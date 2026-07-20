# -*- coding: utf-8 -*-
"""
工具8: auto_self_review_upgrade — 每日收盘自我复盘升级
整合今日学习+回测验证+账户盈亏，淘汰失效策略，融合精华，自我升级
"""
import json
import os
from datetime import datetime, timedelta
from typing import Optional


class SelfReviewer:
    """
    自我复盘升级引擎
    
    每日收盘执行:
    1. 整合今日全网学到的有效知识
    2. 剔除回测/实战证明无效的旧策略
    3. 融合多套优质战法优势
    4. 规划次日学习方向
    5. 生成升级报告
    """

    def __init__(self, knowledge_base=None, evolution=None):
        self.kb = knowledge_base
        self.evo = evolution
        self.review_history = []
        self.review_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "reviews.json"
        )
        self._load_reviews()

    def _load_reviews(self):
        if os.path.exists(self.review_file):
            with open(self.review_file, "r", encoding="utf-8") as f:
                self.review_history = json.load(f)

    def _save_reviews(self):
        with open(self.review_file, "w", encoding="utf-8") as f:
            json.dump(self.review_history, f, ensure_ascii=False, indent=2)

    def daily_review(self, 
                     web_learnings: list = None,
                     backtest_results: list = None,
                     sim_trade_records: list = None,
                     account_data: dict = None) -> dict:
        """
        每日收盘完整复盘
        
        Args:
            web_learnings: 今日联网搜索到的知识列表
            backtest_results: 今日回测结果列表
            sim_trade_records: 模拟/实盘交易记录
            account_data: 账户资金数据
            
        Returns:
            升级报告
        """
        web_learnings = web_learnings or []
        backtest_results = backtest_results or []
        sim_trade_records = sim_trade_records or []
        account_data = account_data or {}
        
        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().isoformat(),
            "sections": {},
            "decisions": [],
            "next_focus": [],
            "upgrade_summary": "",
        }

        # ── 1. 知识吸收 ──
        knowledge_report = self._review_knowledge(web_learnings)
        report["sections"]["knowledge"] = knowledge_report

        # ── 2. 策略验证 ──
        strategy_report = self._review_strategies(backtest_results)
        report["sections"]["strategies"] = strategy_report

        # ── 3. 交易复盘 ──
        trade_report = self._review_trades(sim_trade_records, account_data)
        report["sections"]["trades"] = trade_report

        # ── 4. 淘汰失效策略 ──
        retired = self._retire_failing_strategies(backtest_results, sim_trade_records)
        report["decisions"].extend(retired)

        # ── 5. 融合精华 ──
        upgraded = self._synthesize_upgrades(report)
        report["upgrade_summary"] = upgraded

        # ── 6. 规划明日学习方向 ──
        report["next_focus"] = self._plan_next_learning(report)

        # 保存
        self.review_history.append({
            "date": report["date"],
            "summary": report["upgrade_summary"][:200],
            "decisions": report["decisions"],
        })
        self._save_reviews()
        
        # 记录进化日志
        if self.evo:
            self.evo.log("daily_review", report["upgrade_summary"], 
                         f"{len(report['decisions'])} decisions made")

        return report

    def _review_knowledge(self, learnings: list) -> dict:
        """复盘今日学到的知识"""
        if not learnings:
            return {"status": "no_new_knowledge", "gems": 0, "trash": 0}
        
        gems = [l for l in learnings if l.get("verdict") == "gem"]
        trash = [l for l in learnings if l.get("verdict") == "trash"]
        
        report = {
            "total_learned": len(learnings),
            "gems": len(gems),
            "trash": len(trash),
            "uncertain": len(learnings) - len(gems) - len(trash),
            "top_gems": [],
            "categories_covered": set(),
        }
        
        for gem in gems[:5]:
            report["top_gems"].append({
                "source": gem.get("source", ""),
                "summary": gem.get("summary", "")[:100],
                "score": gem.get("score", 0),
            })
            if "category" in gem:
                report["categories_covered"].add(gem["category"])
        
        report["categories_covered"] = list(report["categories_covered"])
        
        # 存入知识库
        if self.kb:
            for gem in gems:
                self.kb.add(
                    source=gem.get("source", "web"),
                    raw_content=gem.get("summary", ""),
                    category=gem.get("category", "unknown"),
                    quality_score=gem.get("score", 0),
                )
        
        return report

    def _review_strategies(self, backtest_results: list) -> dict:
        """复盘回测结果"""
        if not backtest_results:
            return {"status": "no_backtests"}
        
        passed = [r for r in backtest_results if r.get("verdict") == "pass"]
        failed = [r for r in backtest_results if r.get("verdict") == "fail"]
        
        best = None
        best_return = -999
        worst = None
        worst_dd = 0
        
        for r in backtest_results:
            ret = r.get("total_return_pct", -999)
            dd = r.get("max_drawdown_pct", 0)
            if ret > best_return:
                best_return = ret
                best = r
            if dd > worst_dd:
                worst_dd = dd
                worst = r
        
        return {
            "total_backtests": len(backtest_results),
            "passed": len(passed),
            "failed": len(failed),
            "best_strategy": {
                "code": best.get("code") if best else "",
                "return": best.get("total_return_pct") if best else 0,
                "win_rate": best.get("win_rate_pct") if best else 0,
            } if best else None,
            "worst_drawdown": {
                "code": worst.get("code") if worst else "",
                "max_dd": worst.get("max_drawdown_pct") if worst else 0,
            } if worst else None,
        }

    def _review_trades(self, trade_records: list, account_data: dict) -> dict:
        """复盘交易"""
        if not trade_records:
            return {"status": "no_trades_today"}
        
        closed = [t for t in trade_records if t.get("status") == "closed"]
        wins = [t for t in closed if t.get("pnl", 0) > 0]
        losses = [t for t in closed if t.get("pnl", 0) <= 0]
        
        total_pnl = sum(t.get("pnl", 0) for t in closed)
        
        # 找出亏损最大的交易分析原因
        worst_trade = None
        if losses:
            worst_trade = min(losses, key=lambda t: t.get("pnl", 0))
        
        # 持仓分析
        positions = account_data.get("positions", [])
        pos_analysis = []
        for p in positions:
            pnl_pct = p.get("pnl_pct", 0)
            if pnl_pct < -5:
                pos_analysis.append(f"⚠ {p['symbol']}: {pnl_pct}% (需关注)")
            elif pnl_pct > 5:
                pos_analysis.append(f"✅ {p['symbol']}: +{pnl_pct}%")
        
        return {
            "total_trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0,
            "total_pnl": round(total_pnl, 2),
            "worst_trade": {
                "code": worst_trade.get("code"),
                "pnl": worst_trade.get("pnl"),
            } if worst_trade else None,
            "position_alerts": pos_analysis,
            "account": {
                "nav": account_data.get("nav", 0),
                "position_pct": account_data.get("position_pct", 0),
            },
        }

    def _retire_failing_strategies(self, backtest_results: list, 
                                    trade_records: list) -> list:
        """淘汰失效策略"""
        decisions = []
        
        # 回测连续失败的策略
        for r in backtest_results:
            if r.get("verdict") == "fail":
                decisions.append(f"淘汰: {r.get('code', 'unknown')} {r.get('strategy_name', '')} 回测失败")
                if self.evo:
                    self.evo.retire_strategy(
                        r.get("strategy_name", "unknown"),
                        f"回测失败: return={r.get('total_return_pct')}%"
                    )
        
        # 实盘连续亏损的策略
        for t in trade_records:
            if t.get("pnl", 0) < -500:  # 单笔亏损>500元
                decisions.append(f"警告: {t.get('code', '')} 单笔亏损{t.get('pnl')}元, 需核查")
        
        return decisions

    def _synthesize_upgrades(self, report: dict) -> str:
        """融合精华，生成升级摘要"""
        knowledge = report["sections"].get("knowledge", {})
        strategies = report["sections"].get("strategies", {})
        trades = report["sections"].get("trades", {})
        
        parts = []
        
        # 知识增长
        gems = knowledge.get("gems", 0)
        if gems > 0:
            parts.append(f"今日吸收{gems}条精华知识")
        
        # 策略验证
        passed = strategies.get("passed", 0)
        failed = strategies.get("failed", 0)
        if passed > 0:
            parts.append(f"验证通过{passed}个策略")
        if failed > 0:
            parts.append(f"淘汰{failed}个无效策略")
        
        # 交易表现
        total_pnl = trades.get("total_pnl", 0)
        win_rate = trades.get("win_rate", 0)
        if total_pnl != 0:
            parts.append(f"交易盈亏{total_pnl:+.0f} 胜率{win_rate}%")
        
        # 账户状态
        nav = trades.get("account", {}).get("nav", 0)
        pos = trades.get("account", {}).get("position_pct", 0)
        if nav > 0:
            parts.append(f"资产{nav:,.0f} 仓位{pos}%")
        
        return " | ".join(parts) if parts else "今日无显著变化"

    def _plan_next_learning(self, report: dict) -> list:
        """规划明日学习方向"""
        from config import STAGES
        
        # 根据当前阶段确定基础方向
        stage = "beginner"
        if self.evo:
            stage = self.evo.data.get("stage", "beginner")
        
        focus = list(STAGES[stage]["search_focus"])
        
        # 根据今日发现的问题调整
        strategies = report["sections"].get("strategies", {})
        trades = report["sections"].get("trades", {})
        
        # 如果回撤大 → 学习风控
        worst_dd = strategies.get("worst_drawdown", {})
        if worst_dd and worst_dd.get("max_dd", 0) > 20:
            focus.insert(0, "回撤控制方法")
        
        # 如果胜率低 → 学习入场时机
        if trades.get("win_rate", 100) < 40:
            focus.insert(0, "提高胜率的入场策略")
        
        # 如果仓位高 → 学习仓位管理
        pos_pct = trades.get("account", {}).get("position_pct", 0)
        if pos_pct > 70:
            focus.insert(0, "仓位管理与资金分配")
        
        return focus[:5]


def daily_review(kb=None, evo=None) -> dict:
    """便捷函数: 执行每日复盘"""
    reviewer = SelfReviewer(kb, evo)
    return reviewer.daily_review()
