# -*- coding: utf-8 -*-
"""
进化追踪 — 记录AI自学成长全过程
追踪: 学习日志、策略版本、回测对比、自我升级记录
"""
import json
import os
import time
from datetime import datetime
from config import EVOLUTION_FILE, STAGES


class Evolution:
    def __init__(self):
        self._ensure_file()
        self._load()

    def _ensure_file(self):
        if not os.path.exists(EVOLUTION_FILE):
            init = {
                "stage": "beginner",
                "generation": 0,
                "total_searches": 0,
                "total_backtests": 0,
                "total_trades": 0,
                "total_pnl": 0.0,
                "strategies_active": [],
                "strategies_retired": [],
                "logs": [],
                "milestones": [],
                "current_focus": [],
                "performance": {
                    "daily": [],
                    "weekly": [],
                    "monthly": [],
                },
                "created_at": datetime.now().isoformat(),
            }
            self._save(init)

    def _load(self):
        with open(EVOLUTION_FILE, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def _save(self, data=None):
        if data:
            self.data = data
        with open(EVOLUTION_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def log(self, action: str, detail: str, result: str = ""):
        """记录学习/操作日志"""
        entry = {
            "time": datetime.now().isoformat(),
            "action": action,
            "detail": detail[:500],
            "result": result[:200],
            "stage": self.data["stage"],
            "generation": self.data["generation"],
        }
        self.data["logs"].append(entry)
        if len(self.data["logs"]) > 1000:
            self.data["logs"] = self.data["logs"][-500:]
        self._save()

    def milestone(self, title: str, description: str):
        """记录成长里程碑"""
        self.data["milestones"].append({
            "time": datetime.now().isoformat(),
            "title": title,
            "description": description,
            "stage": self.data["stage"],
            "generation": self.data["generation"],
        })
        self._save()

    def add_strategy(self, name: str, params: dict):
        """添加活跃策略"""
        s = {"name": name, "params": params, "deployed_at": datetime.now().isoformat(), "trades": 0, "pnl": 0.0}
        self.data["strategies_active"].append(s)
        self._save()

    def retire_strategy(self, name: str, reason: str):
        """退役策略"""
        for s in self.data["strategies_active"]:
            if s["name"] == name:
                s["retired_at"] = datetime.now().isoformat()
                s["retire_reason"] = reason
                self.data["strategies_retired"].append(s)
                self.data["strategies_active"].remove(s)
                self._save()
                return

    def record_trade(self, pnl: float):
        """记录交易盈亏"""
        self.data["total_trades"] += 1
        self.data["total_pnl"] += pnl

    def check_stage_upgrade(self, total_trades: int, win_rate: float) -> str:
        """检查是否该升级阶段"""
        for stage_name, info in STAGES.items():
            cond = info["conditions"]
            if cond["total_trades"][0] <= total_trades <= cond["total_trades"][1] and \
               cond["win_rate"][0] <= win_rate <= cond["win_rate"][1]:
                if stage_name != self.data["stage"]:
                    old = self.data["stage"]
                    self.data["stage"] = stage_name
                    self.data["generation"] += 1
                    self.data["current_focus"] = info["search_focus"]
                    self.milestone(f"阶段升级: {STAGES[old]['name']} -> {info['name']}", 
                                   f"交易{total_trades}笔, 胜率{win_rate:.1%}")
                    self._save()
                    return stage_name
        return self.data["stage"]

    def record_daily(self, date: str, pnl: float, trades: int, win_rate: float, drawdown: float):
        """记录每日表现"""
        self.data["performance"]["daily"].append({
            "date": date, "pnl": pnl, "trades": trades, "win_rate": win_rate, "drawdown": drawdown
        })
        if len(self.data["performance"]["daily"]) > 365:
            self.data["performance"]["daily"] = self.data["performance"]["daily"][-365:]
        self._save()

    def status(self) -> dict:
        """当前状态摘要"""
        return {
            "stage": self.data["stage"],
            "stage_name": STAGES[self.data["stage"]]["name"],
            "generation": self.data["generation"],
            "total_searches": self.data["total_searches"],
            "total_backtests": self.data["total_backtests"],
            "total_trades": self.data["total_trades"],
            "total_pnl": self.data["total_pnl"],
            "active_strategies": len(self.data["strategies_active"]),
            "retired_strategies": len(self.data["strategies_retired"]),
            "milestones": len(self.data["milestones"]),
        }
