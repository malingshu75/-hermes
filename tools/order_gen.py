# -*- coding: utf-8 -*-
"""
工具9: generate_order — 交易指令生成器
下单规则（强制校验）:
  股票(300/000/60): 支持市价(1)/限价(2)双模式
  可转债(123/127/113): 仅限价委托，价格必须落在[现价*0.8, 现价*1.2]
  前置: 下单前必须获取实时现价，禁止填充price=0
"""
import json, os, sys, time, urllib.request
from datetime import datetime


class OrderGenerator:
    def __init__(self, account_id: str = None):
        self.account_id = account_id or "2a472909-7763-11f1-95b1-00163e022aa6"
        self.recent_orders = set()
        self.order_history = []
        self._gm_available = False  # WSL始终False，走JSON桥接

    # ── 标的类型判断 ──

    @staticmethod
    def _is_cb(code: str) -> bool:
        """可转债: 123xxx/127xxx/113xxx/128xxx/118xxx/110xxx"""
        num = code.replace("SHSE.", "").replace("SZSE.", "").replace("sh", "").replace("sz", "")
        return num[:3] in ("123", "127", "113", "128", "118", "110", "111")

    @staticmethod
    def _is_stock(code: str) -> bool:
        """股票: 300xxx/000xxx/002xxx/60xxxx/68xxxx"""
        num = code.replace("SHSE.", "").replace("SZSE.", "").replace("sh", "").replace("sz", "")
        return num[:2] in ("60", "68", "00", "30")

    @staticmethod
    def _get_current_price(code: str) -> float:
        """获取实时现价(新浪)"""
        num = code.replace("SHSE.", "").replace("SZSE.", "").replace("sh", "").replace("sz", "")
        if num.startswith("6"):
            sina_code = f"sh{num}"
        else:
            sina_code = f"sz{num}"
        try:
            url = f"http://hq.sinajs.cn/list={sina_code}"
            req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
            data = urllib.request.urlopen(req, timeout=5).read().decode("gbk")
            parts = data.split('"')[1].split(",")
            return float(parts[3]) if parts[3] else 0.0
        except Exception:
            return 0.0

    # ── 买入/卖出 (带品类校验) ──

    def buy(self, code: str, volume: int, price: float = 0,
             order_type: int = 2, strategy_name: str = "ai_robot") -> dict:
        return self._place_order(code, volume, price, order_type, side=1, strategy_name=strategy_name)

    def sell(self, code: str, volume: int, price: float = 0,
              order_type: int = 2, strategy_name: str = "ai_robot") -> dict:
        return self._place_order(code, volume, price, order_type, side=2, strategy_name=strategy_name)

    def _place_order(self, code: str, volume: int, price: float,
                      order_type: int, side: int, strategy_name: str) -> dict:
        """通用下单 — 品类校验 + 价格校验"""

        # 去重
        dedup_key = f"{code}_{side}_{volume}_{int(time.time() // 60)}"
        if dedup_key in self.recent_orders:
            return {"status": "rejected", "reason": "重复订单(60s内)"}

        formatted = self._format_code(code)

        # ── 品类校验 ──
        is_cb = self._is_cb(code)
        is_stock = self._is_stock(code)

        # 获取实时现价(价格前置校验)
        current_price = self._get_current_price(code)

        # 可转债: 强制限价, 禁止市价, 禁止price=0
        if is_cb:
            if order_type == 1:
                return {"status": "rejected", "reason": "可转债只允许限价委托,禁止市价单"}
            if current_price <= 0:
                return {"status": "rejected", "reason": "无法获取可转债实时现价,拒绝price=0下单"}
            if price <= 0:
                return {"status": "rejected", "reason": "可转债禁止price=0,必须指定有效限价"}

            # 价格区间校验: [现价*0.8, 现价*1.2] (±20%涨跌幅)
            price_floor = round(current_price * 0.8, 3)
            price_ceiling = round(current_price * 1.2, 3)
            if price < price_floor or price > price_ceiling:
                return {
                    "status": "rejected",
                    "reason": f"可转债委托价{price}超出涨跌幅限制[{price_floor}, {price_ceiling}]",
                }

        # 股票: price=0时自动获取现价
        if is_stock and price <= 0 and current_price > 0:
            price = round(current_price, 3)
            order_type = 2  # 默认限价

        # ── 生成订单 ──
        order = {
            "order_id": f"json_{int(time.time())}_{len(self.order_history)}",
            "symbol": formatted,
            "side": "buy" if side == 1 else "sell",
            "volume": volume,
            "price": round(price, 4),
            "order_type": "limit" if (order_type == 2 or is_cb) else "market",
            "current_price": round(current_price, 2),
            "status": "generated",
            "time": datetime.now().isoformat(),
            "strategy": strategy_name,
            "account_id": self.account_id,
        }
        self.recent_orders.add(dedup_key)
        self.order_history.append(order)
        return order

    # ── 网格买卖 ──

    def buy_grid(self, code: str, grid_params: dict, current_price: float) -> dict:
        interval = grid_params.get("interval_pct", 2.0) / 100
        unit = grid_params.get("unit", 100)
        martin = grid_params.get("martin", [1, 1, 2, 3, 5])
        layer = grid_params.get("layer", 0)
        multiplier = martin[min(layer, len(martin) - 1)]
        volume = unit * multiplier
        limit_price = current_price * (1 - interval) * 1.005
        return self.buy(code, volume, round(limit_price, 4), order_type=2,
                       strategy_name=f"grid_L{layer+1}")

    def sell_grid(self, code: str, grid_params: dict, current_price: float, avg_cost: float) -> dict:
        interval = grid_params.get("interval_pct", 2.0) / 100
        unit = grid_params.get("unit", 100)
        limit_price = avg_cost * (1 + interval) * 0.99
        return self.sell(code, unit, round(limit_price, 4), order_type=2, strategy_name="grid_sell")

    # ── 辅助 ──

    def close_position(self, code: str, volume: int = 0) -> dict:
        """清仓: 股票T+1检查available_now, 可转债T+0直接卖"""
        from tools.account import AccountQuery
        aq = AccountQuery(self.account_id)
        positions = aq.get_positions()
        
        target = None
        for p in positions:
            if code in p.get("symbol", ""):
                target = p
                break
        
        if not target:
            return {"status": "error", "reason": f"找不到{code}的持仓"}
        
        total_vol = target.get("volume", 0)
        avail = target.get("available_now", total_vol)
        
        if total_vol <= 0:
            return {"status": "error", "reason": "持仓为0"}
        
        # T+1检查: 股票当日买入不可卖
        if self._is_stock(code) and avail <= 0:
            return {"status": "rejected", 
                    "reason": f"T+1规则: {code} 今日买入{total_vol}股,available_now=0,不可卖出"}
        
        sell_vol = min(volume, avail) if volume > 0 else avail
        if sell_vol <= 0:
            return {"status": "rejected", "reason": "无可卖数量"}
            
        price = self._get_current_price(code)
        return self.sell(code, sell_vol, round(price * 0.99, 3), order_type=2, strategy_name="close_all")

    def get_history(self, limit: int = 20) -> list:
        return self.order_history[-limit:]

    def _format_code(self, code: str) -> str:
        if "." in code:
            return code
        if code.startswith("6"):
            return f"SHSE.{code}"
        elif code.startswith(("0", "3", "1")):
            return f"SZSE.{code}"
        elif code.startswith("sh"):
            return f"SHSE.{code[2:]}"
        elif code.startswith("sz"):
            return f"SZSE.{code[2:]}"
        return f"SZSE.{code}"
