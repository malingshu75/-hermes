# -*- coding: utf-8 -*-
"""
工具5: backtest_strategy — 历史回测引擎
将网上学到的策略代入多年历史行情验证
"""
import os
import sys
import json
from datetime import datetime
from typing import Optional

# GM SDK仅Windows端需要——WSL端禁用导入避免卡死
GM_AVAILABLE = False


class BacktestEngine:
    """
    回测引擎
    
    支持:
    - 网格策略回测
    - 趋势策略回测
    - 自定义策略回测
    
    输出:
    - 年化收益
    - 月度盈亏
    - 胜率
    - 最大回撤
    - 失效行情场景
    """

    def __init__(self):
        self.backtest_count = 0

    def backtest_grid(self, code: str, params: dict, 
                       days: int = 250, ohlc_data: list = None) -> dict:
        """
        网格策略回测
        
        Args:
            code: 股票/转债代码
            params: {interval_pct, unit, layers, martin, base_price}
            days: 回测天数
            ohlc_data: 可选, 预加载的OHLC数据
            
        Returns:
            {total_return, annual_return, win_rate, max_drawdown, 
             trades, monthly_returns, sharpe, best_month, worst_month}
        """
        # 加载数据
        if ohlc_data is None:
            ohlc_data = self._load_ohlc(code, days)
        
        if not ohlc_data or len(ohlc_data) < 50:
            return {"error": "数据不足", "code": code}

        # 解析参数
        interval_pct = params.get("interval_pct", 2.0) / 100
        unit = params.get("unit", 100)
        martin = params.get("martin", [1, 1, 2, 3, 5])
        base_price = params.get("base_price", ohlc_data[0]["close"])
        
        # 初始化
        cash = 100000  # 10万回测资金
        position = 0
        total_shares = 0
        avg_cost = base_price
        
        trades = []
        equity_curve = [cash]
        layer = 0  # 当前马丁层
        
        open_price = base_price  # 当日开盘锚定价格
        
        for i, bar in enumerate(ohlc_data):
            high = bar["high"]
            low = bar["low"]
            close = bar["close"]
            date = bar["date"]
            
            # 新的一天: 重置日内锚定
            if i > 0 and date != ohlc_data[i-1]["date"]:
                open_price = close
            
            # 网格买入层
            buy_shares = unit * martin[min(layer, len(martin)-1)]
            buy_price = open_price * (1 - interval_pct)
            
            # 网格卖出层
            sell_shares = unit
            sell_price = avg_cost * (1 + interval_pct) if avg_cost > 0 else open_price * (1 + interval_pct)
            
            # 检查买入触发
            if low <= buy_price and cash >= buy_shares * buy_price:
                actual_price = buy_price
                cost = buy_shares * actual_price
                cash -= cost
                total_shares += buy_shares
                avg_cost = (avg_cost * (total_shares - buy_shares) + cost) / total_shares if total_shares > 0 else actual_price
                position += 1
                layer += 1
                trades.append({
                    "date": date, "action": "buy", "price": round(actual_price, 3),
                    "shares": buy_shares, "layer": layer
                })
            
            # 检查卖出触发
            if high >= sell_price and total_shares >= sell_shares:
                actual_price = sell_price
                revenue = sell_shares * actual_price
                cash += revenue
                total_shares -= sell_shares
                
                # 计算盈亏
                cost_basis = sell_shares * avg_cost
                pnl = revenue - cost_basis
                
                position = max(0, position - 1)
                layer = max(0, layer - 1)
                if total_shares == 0:
                    avg_cost = 0
                
                trades.append({
                    "date": date, "action": "sell", "price": round(actual_price, 3),
                    "shares": sell_shares, "pnl": round(pnl, 2)
                })
            
            # 记录权益曲线
            equity = cash + total_shares * close
            equity_curve.append(equity)

        # 结算
        final_price = ohlc_data[-1]["close"]
        final_equity = cash + total_shares * final_price
        total_return = (final_equity / 100000 - 1) * 100
        
        # 年化
        trading_days = len(ohlc_data)
        annual_return = ((final_equity / 100000) ** (250 / trading_days) - 1) * 100 if trading_days > 0 else 0
        
        # 胜率
        sell_trades = [t for t in trades if t["action"] == "sell"]
        win_trades = [t for t in sell_trades if t.get("pnl", 0) > 0]
        win_rate = len(win_trades) / len(sell_trades) * 100 if sell_trades else 0
        
        # 最大回撤
        max_dd = self._calc_max_drawdown(equity_curve)
        
        # 月度收益
        monthly = self._calc_monthly_returns(equity_curve, ohlc_data)
        
        # 夏普比率
        sharpe = self._calc_sharpe(equity_curve)
        
        self.backtest_count += 1
        
        return {
            "code": code,
            "strategy": "grid",
            "params": params,
            "total_return_pct": round(total_return, 2),
            "annual_return_pct": round(annual_return, 2),
            "win_rate_pct": round(win_rate, 1),
            "max_drawdown_pct": round(max_dd, 2),
            "total_trades": len(trades),
            "sell_trades": len(sell_trades),
            "final_equity": round(final_equity, 2),
            "sharpe_ratio": round(sharpe, 2),
            "monthly_returns": monthly,
            "verdict": "pass" if total_return > 0 and win_rate > 40 and max_dd < 30 else "fail",
        }

    def backtest_custom(self, code: str, strategy_logic: str,
                         days: int = 250) -> dict:
        """
        自定义策略回测 (占位接口)
        实际策略逻辑由大脑生成Python代码后执行
        """
        return {
            "code": code,
            "strategy": "custom",
            "logic": strategy_logic[:100],
            "status": "not_implemented",
            "note": "自定义策略需通过brain.py生成代码后执行",
        }

    def compare_strategies(self, code: str, strategies: list,
                            days: int = 250) -> list:
        """
        多策略并行回测比较
        
        strategies: [{name, type, params}]
        """
        ohlc = self._load_ohlc(code, days)
        if not ohlc:
            return [{"error": "数据加载失败"}]
        
        results = []
        for s in strategies:
            s_type = s.get("type", "grid")
            if s_type == "grid":
                result = self.backtest_grid(code, s.get("params", {}), days, ohlc)
                result["strategy_name"] = s.get("name", "unnamed")
            else:
                result = self.backtest_custom(code, s.get("logic", ""), days)
                result["strategy_name"] = s.get("name", "unnamed")
            results.append(result)
        
        return results

    # ── 内部方法 ──

    def _load_ohlc(self, code: str, days: int) -> list:
        """加载OHLC数据"""
        import struct
        # 清理代码格式
        market = "sh" if code.startswith(("sh", "6", "51")) else "sz"
        code_num = code.replace("sh", "").replace("sz", "")
        
        from config import TDX_DATA
        tdx_base = TDX_DATA
        filepath = os.path.join(tdx_base, market, "lday", f"{market}{code_num}.day")
        
        if not os.path.exists(filepath):
            filepath = os.path.join(tdx_base, market, f"{market}{code_num}.day")
            if not os.path.exists(filepath):
                # 尝试WSL路径
                tdx_base_wsl = "/mnt/c/工作区/tdx/vipdoc"
                filepath = os.path.join(tdx_base_wsl, market, "lday", f"{market}{code_num}.day")
                if not os.path.exists(filepath):
                    return []

        data = []
        try:
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
                        data.append({"date": date, "open": o/100.0, "high": h/100.0, "low": l/100.0, "close": c/100.0, "amount": amt, "volume": vol})
        except Exception:
            return []
        
        return data[-days:] if len(data) > days else data

    def _calc_max_drawdown(self, equity: list) -> float:
        peak = equity[0]
        max_dd = 0
        for val in equity:
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100
            max_dd = max(max_dd, dd)
        return max_dd

    def _calc_monthly_returns(self, equity: list, ohlc: list) -> dict:
        """计算月度收益"""
        monthly = {}
        if not ohlc:
            return {}
        
        # 按月份分组
        for i, bar in enumerate(ohlc):
            date_str = str(bar["date"])
            month_key = date_str[:6]  # YYYYMM
            if month_key not in monthly:
                monthly[month_key] = {"start_equity": equity[i], "end_equity": equity[min(i+1, len(equity)-1)]}
            monthly[month_key]["end_equity"] = equity[min(i+1, len(equity)-1)]
        
        result = {}
        for month, data in monthly.items():
            ret = (data["end_equity"] / data["start_equity"] - 1) * 100
            result[month] = round(ret, 2)
        
        return result

    def _calc_sharpe(self, equity: list) -> float:
        if len(equity) < 2:
            return 0
        returns = [(equity[i] - equity[i-1]) / equity[i-1] for i in range(1, len(equity))]
        if not returns:
            return 0
        mean_ret = sum(returns) / len(returns)
        std_ret = (sum((r - mean_ret) ** 2 for r in returns) / len(returns)) ** 0.5
        if std_ret == 0:
            return 0
        return mean_ret / std_ret * (250 ** 0.5)  # 年化
