# -*- coding: utf-8 -*-
"""
工具7: account_status_query — 随时读取账户状态
总资产、仓位、盈亏、回撤、资金曲线
"""
import json
import os
import sys
import time
from datetime import datetime


class AccountQuery:
    """
    账户查询器
    
    通过GM SDK查询真实账户状态
    支持:
    - 总资产(NAV)
    - 可用资金
    - 持仓明细
    - 当日/累计盈亏
    - 仓位比例
    - 回撤监控
    """

    def __init__(self, account_id: str = None, token: str = None):
        self.account_id = account_id or "2a472909-7763-11f1-95b1-00163e022aa6"
        self.token = token or "927520d80ef8212c5eb366c18fff611bd2090ef2"
        self._gm_available = False
        self._try_import_gm()

    def _try_import_gm(self):
        """WSL环境不直接导入GM SDK(会卡死)，始终使用桥接"""
        # GM SDK仅Windows Python可用，WSL端通过PowerShell桥接查询
        self._gm_available = False

    def query(self) -> dict:
        """
        查询账户完整状态
        
        Returns:
            {
                account_id, nav, available, market_value,
                pnl_today, pnl_total, position_pct,
                positions: [{code, volume, cost, price, pnl, pnl_pct}],
                risk: {circuit_breaker, daily_loss, drawdown}
            }
        """
        if not self._gm_available:
            return self._query_via_bridge()

        result = {
            "account_id": self.account_id,
            "query_time": datetime.now().isoformat(),
            "query_method": "gm_sdk",
        }

        try:
            # 获取资金
            cash = self._gm_get_cash(account_id=self.account_id)
            if isinstance(cash, dict):
                nav = cash.get("nav", 0)
                available = cash.get("available", 0)
                pnl_total = cash.get("pnl", 0)
            else:
                nav = cash.nav
                available = cash.available
                pnl_total = cash.pnl

            result["nav"] = round(nav, 2)
            result["available"] = round(available, 2)
            result["market_value"] = round(nav - available, 2)
            result["position_pct"] = round((nav - available) / nav * 100, 1) if nav > 0 else 0
            result["cash_pct"] = round(available / nav * 100, 1) if nav > 0 else 0
            result["pnl_total"] = round(pnl_total, 2)
            result["pnl_ratio"] = round(pnl_total / (nav - pnl_total) * 100, 2) if nav != pnl_total else 0

            # 获取持仓
            positions = self._gm_get_position(account_id=self.account_id)
            result["positions"] = []
            active_pos = [p for p in positions if p.get("volume", 0) > 0]
            
            for p in active_pos:
                symbol = p.get("symbol", "")
                volume = p.get("volume", 0)
                vwap = p.get("vwap", 0)
                price = p.get("price", 0)
                market_val = p.get("market_value", 0)
                fpnl = p.get("fpnl", 0)
                
                pnl_pct = (fpnl / (vwap * volume)) * 100 if vwap > 0 and volume > 0 else 0
                
                result["positions"].append({
                    "symbol": symbol,
                    "volume": volume,
                    "cost": round(vwap, 4),
                    "price": round(price, 2),
                    "market_value": round(market_val, 2),
                    "pnl": round(fpnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "weight_pct": round(market_val / nav * 100, 1) if nav > 0 else 0,
                })

            # 挂单
            try:
                orders = self._gm_get_orders(account_id=self.account_id)
                result["pending_orders"] = len(orders) if orders else 0
            except Exception:
                result["pending_orders"] = 0

            # 风控
            result["risk"] = self._assess_risk(result)

        except Exception as e:
            result["error"] = str(e)
            result["query_method"] = "failed"
            # 降级到桥接方式
            fallback = self._query_via_bridge()
            if not fallback.get("error"):
                result.update(fallback)

        return result

    def _query_via_bridge(self) -> dict:
        """通过文件桥接查询 (WSL→Windows)"""
        bridge_file = r"C:\cb_vwap\_ai_robot_account.json"
        wsl_bridge = "/mnt/c/cb_vwap/_ai_robot_account.json"
        
        # 运行桥接脚本
        try:
            script = r"C:\cb_vwap\_ai_account_query.py"
            os.system(f'powershell.exe -NoProfile -Command "Start-Process -FilePath \'C:/Users/Administrator/AppData/Local/Programs/Python/Python310/python.exe\' -ArgumentList \'C:/cb_vwap/_ai_account_query.py\' -NoNewWindow -Wait" 2>&1')
            time.sleep(5)
        except Exception:
            pass
        
        # 读取结果
        bridge_path = wsl_bridge if os.path.exists(wsl_bridge) else bridge_file
        try:
            with open(bridge_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 提取AI账户数据
            for name, acct in data.get("accounts", {}).items():
                if self.account_id in acct.get("acct_id", ""):
                    return {
                        "account_id": self.account_id,
                        "query_time": datetime.now().isoformat(),
                        "query_method": "bridge",
                        "nav": acct.get("nav", 0),
                        "available": acct.get("available", 0),
                        "market_value": acct.get("market_value", 0),
                        "position_pct": round(acct.get("market_value", 0) / acct.get("nav", 1) * 100, 1),
                        "pnl_total": acct.get("pnl", 0),
                        "positions": acct.get("positions", []),
                        "risk": {"circuit_breaker": data.get("circuit_breaker", False)},
                    }
        except Exception as e:
            return {"error": str(e), "query_method": "failed"}
        
        return {"error": "无法连接账户", "query_method": "failed"}

    def get_positions(self) -> list:
        """获取当前持仓"""
        result = self.query()
        return result.get("positions", [])

    def get_nav(self) -> float:
        """获取总资产"""
        result = self.query()
        return result.get("nav", 0)

    def get_available(self) -> float:
        """获取可用资金"""
        result = self.query()
        return result.get("available", 0)

    def get_risk(self) -> dict:
        """获取风控状态"""
        result = self.query()
        return result.get("risk", {})

    def _assess_risk(self, result: dict) -> dict:
        """评估风险"""
        nav = result.get("nav", 0)
        pos_pct = result.get("position_pct", 0)
        pnl_total = result.get("pnl_total", 0)
        
        from config import COMPLIANCE
        
        risk = {
            "circuit_breaker": False,
            "warnings": [],
            "daily_loss_pct": 0,
            "drawdown_pct": 0,
        }
        
        # 仓位检查
        if pos_pct > COMPLIANCE["max_total_position_pct"] * 100:
            risk["warnings"].append(f"仓位超标: {pos_pct}% > {COMPLIANCE['max_total_position_pct']*100}%")
        
        # 单票仓位检查
        for pos in result.get("positions", []):
            weight = pos.get("weight_pct", 0)
            if weight > COMPLIANCE["max_single_position_pct"] * 100:
                risk["warnings"].append(f"单票{pos['symbol']}仓位超标: {weight}%")
        
        # 熔断检查 (日亏>5%)
        if abs(pnl_total) / nav > COMPLIANCE["daily_loss_circuit_breaker"]:
            risk["circuit_breaker"] = True
            risk["warnings"].append("触发日亏熔断!")
        
        return risk


# 便捷函数
def query_account(account_id: str = None) -> dict:
    return AccountQuery(account_id).query()
