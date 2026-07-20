# -*- coding: utf-8 -*-
"""
工具6: trial_trade_sim — 模拟实盘试错
回测通过后轻仓模拟实盘，二次验证策略稳定性
"""
import json
import os
import time
from datetime import datetime
from typing import Optional


class SimTrader:
    """
    模拟交易器
    
    模式:
    - paper: 纯模拟，不调用GM SDK
    - gm_paper: 通过GM SDK模拟盘(如果有)
    - light_live: 极小仓位实盘试错(100股级别)
    
    记录:
    - 模拟交易盈亏
    - 滑点
    - 持仓周期
    - 实战暴露的缺陷
    """

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data"
        )
        self.sim_file = os.path.join(self.data_dir, "sim_trades.json")
        self._ensure_file()
        self._load()

    def _ensure_file(self):
        os.makedirs(self.data_dir, exist_ok=True)
        if not os.path.exists(self.sim_file):
            self._save({"trades": [], "active_positions": [], "stats": self._empty_stats()})

    def _load(self):
        with open(self.sim_file, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def _save(self, data=None):
        if data:
            self.data = data
        with open(self.sim_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _empty_stats(self):
        return {
            "total_trades": 0,
            "win_trades": 0,
            "total_pnl": 0.0,
            "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "avg_hold_days": 0.0,
            "avg_slippage_pct": 0.0,
        }

    def open_position(self, code: str, strategy_name: str, 
                       direction: str = "long", size: int = 100,
                       entry_price: float = 0, slippage_pct: float = 0.1) -> dict:
        """
        开仓(模拟)
        
        Args:
            code: 标的代码
            strategy_name: 使用的策略名称
            direction: long/short
            size: 数量(股/张)
            entry_price: 入场价(0=用现价)
            slippage_pct: 预估滑点%
        """
        # 获取现价
        if entry_price <= 0:
            entry_price = self._get_current_price(code)
        
        actual_price = entry_price * (1 + slippage_pct / 100) if direction == "long" else entry_price * (1 - slippage_pct / 100)
        
        trade = {
            "id": f"sim_{int(time.time())}_{len(self.data['trades'])}",
            "code": code,
            "strategy": strategy_name,
            "direction": direction,
            "size": size,
            "entry_price": round(actual_price, 4),
            "entry_time": datetime.now().isoformat(),
            "exit_price": None,
            "exit_time": None,
            "pnl": None,
            "pnl_pct": None,
            "status": "open",
            "notes": [],
        }
        
        self.data["trades"].append(trade)
        self.data["active_positions"].append(trade["id"])
        self._save()
        
        return trade

    def close_position(self, trade_id: str, exit_price: float = 0,
                        slippage_pct: float = 0.1) -> dict:
        """平仓(模拟)"""
        for trade in self.data["trades"]:
            if trade["id"] == trade_id and trade["status"] == "open":
                if exit_price <= 0:
                    exit_price = self._get_current_price(trade["code"])
                
                actual_exit = exit_price * (1 - slippage_pct / 100) if trade["direction"] == "long" else exit_price * (1 + slippage_pct / 100)
                
                trade["exit_price"] = round(actual_exit, 4)
                trade["exit_time"] = datetime.now().isoformat()
                trade["status"] = "closed"
                
                # 计算盈亏
                if trade["direction"] == "long":
                    pnl = (actual_exit - trade["entry_price"]) * trade["size"]
                else:
                    pnl = (trade["entry_price"] - actual_exit) * trade["size"]
                
                pnl_pct = (pnl / (trade["entry_price"] * trade["size"])) * 100 if trade["entry_price"] > 0 else 0
                
                trade["pnl"] = round(pnl, 2)
                trade["pnl_pct"] = round(pnl_pct, 2)
                
                if trade_id in self.data["active_positions"]:
                    self.data["active_positions"].remove(trade_id)
                
                # 更新统计
                self._update_stats()
                self._save()
                
                return trade
        
        return {"error": "trade not found or already closed"}

    def run_trial(self, code: str, strategy_name: str, 
                   params: dict, days: int = 60) -> dict:
        """
        运行模拟试错
        
        使用历史数据模拟最近N天的交易，输出试错报告
        """
        # 导入回测引擎
        from tools.backtester import BacktestEngine
        
        bt = BacktestEngine()
        
        # 获取历史数据
        import struct
        market = "sh" if code.startswith(("sh", "6", "51")) else "sz"
        code_num = code.replace("sh", "").replace("sz", "")
        
        from config import TDX_DATA
        tdx_base = TDX_DATA
        filepath = os.path.join(tdx_base, market, "lday", f"{market}{code_num}.day")
        
        try:
            ohlc = []
            with open(filepath, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(0)
                for _ in range(size // 32):
                    raw = f.read(32)
                    if len(raw) < 32:
                        break
                    date, o, h, l, c, amt, vol, _ = struct.unpack("=IiiiiIII", raw)
                    if 19900101 <= date <= 20991231 and c > 0:
                        ohlc.append({"date": date, "open": o/100.0, "high": h/100.0, "low": l/100.0, "close": c/100.0, "amount": amt, "volume": vol})
            
            ohlc = ohlc[-days:] if len(ohlc) > days else ohlc
            
            if not ohlc:
                return {"error": "数据不足"}
            
            # 回测最近N天
            if params.get("type", "grid") == "grid":
                result = bt.backtest_grid(code, params, days, ohlc)
            else:
                result = bt.backtest_custom(code, strategy_name, days)
            
            # 记录模拟交易
            for trade in result.get("trades", []):
                self.data["trades"].append({
                    "id": f"trial_{code}_{len(self.data['trades'])}",
                    "code": code,
                    "strategy": strategy_name,
                    "direction": "long",
                    "size": params.get("unit", 100),
                    "entry_price": trade.get("price", 0),
                    "exit_price": trade.get("exit_price", 0),
                    "pnl": trade.get("pnl", 0),
                    "status": "closed",
                    "is_trial": True,
                })
            
            self._update_stats()
            self._save()
            
            return {
                "code": code,
                "strategy": strategy_name,
                "trial_days": days,
                "backtest_result": result,
                "trial_passed": result.get("verdict") == "pass",
            }
        except Exception as e:
            return {"error": str(e)}

    def get_stats(self) -> dict:
        """获取模拟交易统计"""
        return dict(self.data["stats"])

    def get_open_positions(self) -> list:
        """获取当前持仓"""
        return [t for t in self.data["trades"] if t["status"] == "open"]

    def _update_stats(self):
        trades = [t for t in self.data["trades"] if t["status"] == "closed"]
        if not trades:
            return
        
        total = len(trades)
        wins = len([t for t in trades if t.get("pnl", 0) > 0])
        total_pnl = sum(t.get("pnl", 0) for t in trades)
        
        self.data["stats"] = {
            "total_trades": total,
            "win_trades": wins,
            "win_rate_pct": round(wins / total * 100, 1) if total > 0 else 0,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(total_pnl / total, 2) if total > 0 else 0,
            "active_positions": len(self.data["active_positions"]),
        }

    def _get_current_price(self, code: str) -> float:
        """获取当前价格(从新浪)"""
        import urllib.request
        try:
            market_code = code
            if code.startswith("sh"):
                market_code = code
            elif code.startswith("sz"):
                market_code = code
            elif code.startswith("6"):
                market_code = f"sh{code}"
            else:
                market_code = f"sz{code}"
            
            url = f"http://hq.sinajs.cn/list={market_code}"
            req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
            data = urllib.request.urlopen(req, timeout=5).read().decode("gbk")
            parts = data.split('"')[1].split(",")
            return float(parts[3]) if len(parts) > 3 else 0
        except Exception:
            return 0
