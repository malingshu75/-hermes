# -*- coding: utf-8 -*-
"""
AI炒股机器人 - 核心大脑 (brain.py)

自主学习闭环:
  联网学习 → 信息过滤 → 回测验证 → 模拟试错 → 实盘交易 → 复盘升级
  每日循环，从不停止成长
"""
import os
import sys
import json
import time
import random
from datetime import datetime
from typing import Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import *
from knowledge_base import KnowledgeBase
from evolution import Evolution
from tools.web_search import WebSearch
from tools.info_filter import InfoFilter
from tools.scanner import MarketScanner
from tools.indicators import IndicatorEngine
from tools.backtester import BacktestEngine
from tools.sim_trader import SimTrader
from tools.account import AccountQuery
from tools.reviewer import SelfReviewer
from tools.order_gen import OrderGenerator


class AIStockBrain:
    """
    AI炒股机器人大脑
    
    全自主运行，无需人工干预。
    每天自动执行学习→验证→交易→进化循环。
    """

    def __init__(self):
        self.kb = KnowledgeBase()
        self.evo = Evolution()
        self.web_search = WebSearch()
        self.info_filter = InfoFilter()
        self.scanner = MarketScanner()
        self.indicators = IndicatorEngine()
        self.backtester = BacktestEngine()
        self.sim_trader = SimTrader()
        self.account = AccountQuery()
        self.reviewer = SelfReviewer(self.kb, self.evo)
        self.order_gen = OrderGenerator()
        
        self.stage = self.evo.data.get("stage", "beginner")
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.log = []

    # ══════════════════════════════════════════════════════════
    #  每日主循环
    # ══════════════════════════════════════════════════════════

    def run_daily(self, mode: str = "learn") -> dict:
        """
        每日主循环
        
        Args:
            mode: "learn"(仅学习) | "paper"(学习+模拟) | "live"(学习+实盘)
        """
        print(f"\n{'='*60}")
        print(f"  AI炒股机器人 — {STAGES[self.stage]['name']}")
        print(f"  {self.today} | 模式: {mode}")
        print(f"{'='*60}\n")

        result = {
            "date": self.today,
            "mode": mode,
            "stage": self.stage,
            "phases": {},
        }

        # ── 阶段1: 联网学习 ──
        print("[阶段1/6] 联网学习...")
        learnings = self._phase_learn()
        result["phases"]["learn"] = learnings
        self._print_phase(learnings)
        
        # ── 阶段2: 信息过滤 ──
        print("[阶段2/6] 信息过滤...")
        filtered = self._phase_filter(learnings)
        result["phases"]["filter"] = filtered
        self._print_phase(filtered)
        
        # ── 阶段3: 全市场扫描 ──
        print("[阶段3/6] 全市场扫描...")
        scan_result = self._phase_scan()
        result["phases"]["scan"] = scan_result
        self._print_phase(scan_result)
        
        # ── 阶段4: 策略验证(回测) ──
        print("[阶段4/6] 回测验证...")
        backtest_results = self._phase_backtest(filtered, scan_result)
        result["phases"]["backtest"] = backtest_results
        self._print_phase(backtest_results)
        
        # ── 阶段5: 交易执行 ──
        print("[阶段5/6] 交易执行...")
        trade_results = self._phase_trade(mode, backtest_results, scan_result)
        result["phases"]["trade"] = trade_results
        self._print_phase(trade_results)
        
        # ── 阶段6: 复盘升级 ──
        print("[阶段6/6] 复盘升级...")
        review = self._phase_review(learnings, backtest_results, trade_results)
        result["phases"]["review"] = review
        self._print_phase(review)
        
        # 保存结果
        self._save_daily_result(result)
        
        print(f"\n{'='*60}")
        print(f"  今日成长完成 | {review.get('upgrade_summary', '')}")
        print(f"{'='*60}\n")
        
        return result

    # ══════════════════════════════════════════════════════════
    #  阶段1: 联网学习
    # ══════════════════════════════════════════════════════════

    def _phase_learn(self) -> dict:
        """联网搜索学习"""
        topics = self.web_search.get_search_topics(self.stage)
        # 每日搜索5个主题
        selected_topics = topics[:5]
        
        all_results = []
        for topic in selected_topics:
            result = self.web_search.search(
                keyword=topic,
                category=self._guess_category(topic),
                max_results=6,
            )
            all_results.append({
                "topic": topic,
                "results_count": result.get("total_found", 0),
                "results": result.get("results", []),
            })
            time.sleep(1)  # 礼貌间隔
        
        self.evo.data["total_searches"] += len(selected_topics)
        
        return {
            "topics_searched": len(selected_topics),
            "total_results": sum(r["results_count"] for r in all_results),
            "details": all_results,
        }

    # ══════════════════════════════════════════════════════════
    #  阶段2: 信息过滤
    # ══════════════════════════════════════════════════════════

    def _phase_filter(self, learnings: dict) -> dict:
        """过滤学习结果"""
        all_items = []
        for topic_result in learnings.get("details", []):
            for item in topic_result.get("results", []):
                all_items.append(item)
        
        if not all_items:
            return {"total": 0, "gems": 0, "trash": 0}
        
        filter_results = self.info_filter.filter_batch(all_items)
        gems = self.info_filter.get_gems(filter_results)
        trash = self.info_filter.get_trash(filter_results)
        
        # 精华存入知识库
        for gem in gems:
            self.kb.add(
                source=gem.get("source", "web"),
                raw_content=gem.get("summary", ""),
                category=gem.get("category", "unknown"),
                quality_score=gem.get("score", 0),
            )
            self.evo.log("knowledge_gem", 
                         f"发现精华: {gem.get('source', '')} {gem.get('summary', '')[:80]}",
                         f"评分: {gem.get('score', 0)}")
        
        # 糟粕标记
        for t in trash:
            self.evo.log("knowledge_trash",
                         f"丢弃糟粕: {t.get('source', '')} {t.get('summary', '')[:80]}",
                         f"原因: {', '.join(t.get('trash_reasons', []))}")
        
        return {
            "total": len(filter_results),
            "gems": len(gems),
            "trash": len(trash),
            "uncertain": len(filter_results) - len(gems) - len(trash),
            "top_gems": [
                {"source": g.get("source"), "score": g.get("score"), 
                 "summary": g.get("summary", "")[:80]}
                for g in gems[:5]
            ],
        }

    # ══════════════════════════════════════════════════════════
    #  阶段3: 全市场扫描
    # ══════════════════════════════════════════════════════════

    def _phase_scan(self) -> dict:
        """扫描全市场候选标的"""
        # 扫描网格候选
        candidates = self.scanner.scan_grid_candidates(
            min_amplitude=4.0,
            max_price=50,
            top_n=30,
        )
        
        # 诊断前5个最优候选
        diagnosed = []
        for c in candidates[:5]:
            diagnosis = self.indicators.diagnose(c["code"])
            if "error" not in diagnosis:
                diagnosed.append({
                    "code": c["code"],
                    "amplitude": diagnosis.get("amplitude", 0),
                    "grid_score": diagnosis.get("grid_score", 0),
                    "recommended": diagnosis.get("recommended_strategy", ""),
                    "grid_params": diagnosis.get("grid_params"),
                })
        
        return {
            "candidates_found": len(candidates),
            "top_5_codes": [c["code"] for c in candidates[:5]],
            "diagnosed": diagnosed,
        }

    # ══════════════════════════════════════════════════════════
    #  阶段4: 回测验证
    # ══════════════════════════════════════════════════════════

    def _phase_backtest(self, filtered: dict, scan_result: dict) -> dict:
        """回测验证策略"""
        backtest_list = []
        
        # 对扫描出的候选做网格回测（100/100验证：网格A股唯一有效策略）
        for d in scan_result.get("diagnosed", []):
            code = d.get("code")
            params = d.get("grid_params")
            # 即使诊断推荐trend，也强制生成网格参数回测（网格是唯一验证通过的策略）
            if code:
                if params is None:
                    amp = d.get("amplitude", 4.0)
                    params = {
                        "interval_pct": round(max(0.75, amp / 6), 2),
                        "unit": 100,
                        "layers": 5,
                        "martin": [1, 1, 2, 3, 5],
                    }
                result = self.backtester.backtest_grid(code, params, days=250)
                result["code"] = code
                backtest_list.append(result)
                self.evo.data["total_backtests"] += 1
                
                if result.get("verdict") == "pass":
                    self.evo.log("backtest_pass",
                                f"{code} 网格回测通过",
                                f"收益{result.get('total_return_pct')}% 胜率{result.get('win_rate_pct')}%")
                    self.evo.add_strategy(f"grid_{code}", params)
                else:
                    self.evo.log("backtest_fail",
                                f"{code} 网格回测失败",
                                f"收益{result.get('total_return_pct')}%")
        
        passed = [r for r in backtest_list if r.get("verdict") == "pass"]
        
        return {
            "total": len(backtest_list),
            "passed": len(passed),
            "failed": len(backtest_list) - len(passed),
            "results": backtest_list,
        }

    # ══════════════════════════════════════════════════════════
    #  阶段5: 交易执行
    # ══════════════════════════════════════════════════════════

    def _phase_trade(self, mode: str, backtest: dict, scan: dict) -> dict:
        """执行交易"""
        if mode == "learn":
            return {"action": "none", "reason": "learn模式,不交易"}
        
        # 检查熔断
        risk = self.account.get_risk()
        if risk.get("circuit_breaker"):
            return {"action": "blocked", "reason": "熔断触发,停止交易",
                    "risk": risk}
        
        trades = []
        
        # 获取回测通过的策略
        passed_results = [r for r in backtest.get("results", [])
                         if r.get("verdict") == "pass"]
        
        if mode == "paper":
            # 模拟交易
            for r in passed_results[:3]:
                trial = self.sim_trader.run_trial(
                    code=r["code"],
                    strategy_name=f"grid_{r['code']}",
                    params=r.get("params", {}),
                )
                trades.append(trial)
            return {"action": "paper_trade", "trades": trades}
        
        elif mode == "live":
            # 真实交易(小仓位试错)
            account_data = self.account.query()
            available = account_data.get("available", 0)
            
            if available < 10000:
                return {"action": "blocked", "reason": f"可用资金不足: {available}"}
            
            # 对回测通过的第一只做极小仓位试错
            if passed_results:
                best = passed_results[0]
                params = best.get("params", {})
                unit = min(params.get("unit", 100), 200)  # 最多200股
                
                if mode == "live":
                    order = self.order_gen.buy(
                        code=best["code"],
                        volume=unit,
                        order_type=2,
                        strategy_name="ai_robot_trial"
                    )
                    trades.append(order)
            
            return {"action": "live_trade", "trades": trades}
        
        return {"action": "none"}

    # ══════════════════════════════════════════════════════════
    #  阶段6: 复盘升级
    # ══════════════════════════════════════════════════════════

    def _phase_review(self, learnings: dict, backtest: dict, 
                       trade_results: dict) -> dict:
        """每日复盘升级"""
        # 收集精华知识
        gems = []
        for topic in learnings.get("details", []):
            for item in topic.get("results", []):
                filter_result = self.info_filter.filter(item.get("snippet", ""))
                if filter_result["verdict"] == "gem":
                    gems.append({
                        "source": item.get("source", ""),
                        "summary": item.get("snippet", "")[:200],
                        "score": filter_result["score"],
                        "verdict": "gem",
                    })
        
        # 收集回测结果
        backtest_data = []
        for r in backtest.get("results", []):
            backtest_data.append({
                "code": r.get("code"),
                "strategy": r.get("strategy_name", "grid"),
                "return": r.get("total_return_pct", 0),
                "verdict": r.get("verdict", "fail"),
            })
        
        # 收集交易记录
        trades = []
        for t in trade_results.get("trades", []):
            if isinstance(t, dict):
                trades.append({
                    "code": t.get("code", ""),
                    "action": t.get("action", ""),
                    "pnl": t.get("pnl", 0),
                })
        
        # 获取账户数据
        account_data = self.account.query()
        
        # 执行复盘
        review = self.reviewer.daily_review(
            web_learnings=gems,
            backtest_results=backtest_data,
            sim_trade_records=trades,
            account_data=account_data,
        )
        
        # 检查阶段升级
        total_trades = self.evo.data.get("total_trades", 0)
        win_rate = self._calc_win_rate()
        new_stage = self.evo.check_stage_upgrade(total_trades, win_rate)
        if new_stage != self.stage:
            self.stage = new_stage
            review["stage_upgraded"] = True
            review["new_stage"] = STAGES[new_stage]["name"]
        
        return review

    # ══════════════════════════════════════════════════════════
    #  辅助方法
    # ══════════════════════════════════════════════════════════

    def status(self) -> dict:
        """获取当前状态"""
        return {
            "stage": self.stage,
            "stage_name": STAGES[self.stage]["name"],
            "evolution": self.evo.status(),
            "knowledge": self.kb.stats(),
            "today": self.today,
        }

    def report(self) -> str:
        """生成状态报告"""
        status = self.status()
        evo = status["evolution"]
        kb = status["knowledge"]
        
        lines = [
            f"AI炒股机器人 — {status['stage_name']}",
            f"日期: {status['today']}",
            f"─" * 40,
            f"进化: 第{evo['generation']}代 | 搜索{evo['total_searches']}次 | 回测{evo['total_backtests']}次 | 交易{evo['total_trades']}笔",
            f"知识库: {kb['total']}条 | 验证通过{kb['validated']}条 | 部署{kb['deployed']}条",
            f"活跃策略: {evo['active_strategies']}个 | 已退役: {evo['retired_strategies']}个",
            f"累计盈亏: {evo['total_pnl']:+,.0f}",
            f"里程碑: {evo['milestones']}个",
        ]
        
        # 最近里程碑
        for m in self.evo.data.get("milestones", [])[-3:]:
            lines.append(f"  🏆 {m['title']}: {m['description']}")
        
        return "\n".join(lines)

    def _calc_win_rate(self) -> float:
        """计算胜率"""
        total = self.evo.data.get("total_trades", 0)
        if total == 0:
            return 0
        # 简化: 从进化日志计算
        trade_logs = [l for l in self.evo.data.get("logs", []) 
                      if l.get("action") == "trade"]
        if not trade_logs:
            return 0.5
        wins = len([l for l in trade_logs if "win" in l.get("result", "").lower()])
        return wins / len(trade_logs) if trade_logs else 0.5

    def _guess_category(self, topic: str) -> str:
        """根据主题猜测分类"""
        topic_lower = topic.lower()
        cats = WebSearch.SEARCH_CATEGORIES
        for cat, keywords in cats.items():
            for kw in keywords:
                if kw in topic or kw in topic_lower:
                    return cat
        return "交易策略"

    def _save_daily_result(self, result: dict):
        """保存每日结果"""
        result_file = os.path.join(DATA_DIR, "daily_results.json")
        history = []
        if os.path.exists(result_file):
            with open(result_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        
        # 只保存摘要(完整结果太大)
        summary = {
            "date": result["date"],
            "mode": result["mode"],
            "stage": result["stage"],
            "learn_topics": result["phases"].get("learn", {}).get("topics_searched", 0),
            "gems_found": result["phases"].get("filter", {}).get("gems", 0),
            "candidates_scanned": result["phases"].get("scan", {}).get("candidates_found", 0),
            "backtest_passed": result["phases"].get("backtest", {}).get("passed", 0),
            "trade_action": result["phases"].get("trade", {}).get("action", "none"),
            "upgrade": result["phases"].get("review", {}).get("upgrade_summary", ""),
        }
        history.append(summary)
        
        # 只保留最近90天
        if len(history) > 90:
            history = history[-90:]
        
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def _print_phase(self, phase_result: dict):
        """打印阶段结果摘要"""
        if not phase_result:
            return
        # 简洁打印
        keys = list(phase_result.keys())
        summary_keys = [k for k in keys if k in 
                       ("topics_searched", "total_results", "gems", "trash",
                        "candidates_found", "total", "passed", "failed",
                        "action", "upgrade_summary")]
        if summary_keys:
            items = []
            for k in summary_keys:
                v = phase_result.get(k)
                if v is not None:
                    items.append(f"{k}={v}")
            print(f"  -> {' | '.join(items[:4])}")


# ══════════════════════════════════════════════════════════
#  主入口
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI炒股机器人")
    parser.add_argument("--mode", choices=["learn", "paper", "live"], 
                        default="learn",
                        help="运行模式: learn=仅学习, paper=学习+模拟, live=学习+实盘")
    parser.add_argument("--status", action="store_true",
                        help="显示当前状态")
    parser.add_argument("--report", action="store_true",
                        help="生成状态报告")
    
    args = parser.parse_args()
    
    brain = AIStockBrain()
    
    if args.status:
        print(json.dumps(brain.status(), ensure_ascii=False, indent=2))
    elif args.report:
        print(brain.report())
    else:
        brain.run_daily(mode=args.mode)
