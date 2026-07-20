# -*- coding: utf-8 -*-
"""
工具2: info_filter — 自主辨别精华/糟粕
对联网搜到的海量资料执行三层极速筛选:
  第1层: 粗筛黑名单 — 暴富/内幕/引流/满仓赌徒 → 直接丢弃
  第2层: 结构快速校验 — 5大核心模块检测,缺3项→低价值
  第3层: 逻辑闭环校验 — 能否说明回撤/失效场景/行情适配 → 高价值精华

精华标准: 可量化、可回测、跨牛熊验证、配套风控、无营销引流
所有糟粕永久剔除,不参与学习与实盘,不占知识库资源
"""
import re
from typing import Optional


class InfoFilter:
    """
    三层极速筛选过滤器

    ── 第1层: 粗筛黑名单(命中即丢弃) ──
    暴富话术 | 内幕消息 | 引流广告 | 满仓赌徒 | 虚假承诺

    ── 第2层: 结构快速校验(5大核心模块) ──
    ① 入场条件 | ② 止损规则 | ③ 止盈规则 | ④ 仓位管理 | ⑤ 历史盈亏数据
    缺失≥3项 → 低价值,仅浅度参考

    ── 第3层: 逻辑闭环校验 ──
    能说明策略回撤/失效场景/适配行情 → 高价值精华
    可量化+可回测+跨牛熊+有风控+无营销 → 顶级精华
    """

    # ═══ 第1层: 粗筛黑名单(命中任意→直接丢弃) ═══
    BLACKLIST = [
        # 暴富话术
        (r"(月|周|日)\s*(赚|盈|收益|获利)\s*\d{2,}\s*[%％万]", "暴富宣称"),
        (r"(翻倍|暴富|财富自由|一夜暴富|躺赚|稳赚|稳赢)", "暴富话术"),
        (r"(保证.*?赚|包赚|必涨|零风险|无风险|百分百|100%)\s*(赚|盈)", "虚假承诺"),
        # 内幕消息
        (r"(内幕|内部消息|一手消息|提前知道|庄家透露)", "内幕消息"),
        (r"(消息票|内幕票|庄票|老鼠仓)", "非法荐股"),
        (r"(独家.*?消息|私密.*?情报)", "伪装内幕"),
        # 引流广告
        (r"(加.*?(微信|QQ|群|v|V)|扫码|关注公众号|私信我)", "引流广告"),
        (r"(免费带单|免费指导|跟单.*?赚|代操盘|代客理财)", "非法代客"),
        (r"(限时.*?免费|名额.*?有限|最后.*?机会)", "营销话术"),
        # 满仓赌徒
        (r"(满仓.*?(干|搞|冲|杀|梭)|满仓搞|all\s*in|一把梭)", "满仓赌博"),
        (r"(闭眼.*?买|无脑.*?买|不看.*?(买|进))", "盲从交易"),
        # 造神/骗局
        (r"(股神|大师|神级|神话|传奇|封神)", "造神营销"),
        (r"(必杀技|绝招|秘诀|秘籍|不传之秘)", "夸张营销"),
        (r"(胜率\s*(90|9[5-9]|100)\s*[%％])", "虚高胜率"),
        # 纯情绪
        (r"^(大涨|暴跌|崩盘|涨停潮|跌停潮)[!！。.]*$", "纯情绪呐喊"),
    ]

    # ═══ 第2层: 5大核心模块检测 ═══
    FIVE_MODULES = {
        "入场条件": [
            r"(买入条件|入场条件|开仓条件|进场.*?条件)",
            r"(当.*?(突破|跌破|站上|跌穿).*?(买入|开仓))",
            r"(金叉|死叉|突破.*?均线|回踩.*?支撑)",
            r"(信号.*?买入|触发.*?买入)",
            r"(buy.*?condition|entry.*?rule|开仓.*?规则)",
        ],
        "止损规则": [
            r"(止损|stop\s*loss|亏损.*?(卖出|离场))",
            r"(亏.*?[≤<]\s*\d{1,2}\s*[%％].*?(卖|出|走))",
            r"(最大.*?(亏损|回撤).*?[≤<]\s*\d)",
            r"(跌破.*?(止损|退出|离场))",
            r"(亏损.*?上限|硬止损)",
        ],
        "止盈规则": [
            r"(止盈|take\s*profit|盈利.*?(卖出|离场))",
            r"(赚.*?[≥>]\s*\d{1,2}\s*[%％].*?(卖|出|走))",
            r"(目标.*?(价|位|收益)|盈利.*?目标)",
            r"(移动止盈|跟踪止盈|动态止盈)",
            r"(分批次.*?止盈|阶梯.*?止盈)",
        ],
        "仓位管理": [
            r"(仓位|头寸|position\s*size|资金管理)",
            r"(单票.*?[≤<]\s*\d{1,2}\s*[%％])",
            r"(总仓位.*?[≤<]\s*\d{1,2}\s*[%％])",
            r"(分散|分仓|分批|资金分配|金字塔)",
            r"(凯利|Kelly|风险预算|仓位.*?上限)",
        ],
        "历史盈亏数据": [
            r"(回测|backtest|历史.*?验证|历史.*?测试)",
            r"(胜率\s*\d{2,3}\s*[%％]|盈亏比\s*\d)",
            r"(年化.*?收益|最大回撤\s*\d{1,2}\s*[%％])",
            r"(夏普|sharpe|calmar|sortino)",
            r"(\d{4}\s*[年-]\s*\d{4}.*?(回测|数据|验证))",
        ],
    }

    # ═══ 第3层: 逻辑闭环加分项 ═══
    LOGIC_BONUS = [
        # 能说明回撤
        (r"(最大回撤|drawdown).*?(\d{1,2}\s*[%％]|控制|管理|应对)", "回撤说明", 8),
        (r"(回撤.*?(原因|分析|场景|行情))", "回撤归因", 6),
        # 能说明失效场景
        (r"(失效|不适.*?(行情|市场|场景|环境)|策略.*?失效)", "失效场景说明", 10),
        (r"(震荡市.*?表现|熊市.*?表现|牛市.*?表现)", "分行情表现", 8),
        (r"(不适合|不适应|不适用).*?(行情|市场|标的)", "限制条件明确", 6),
        # 能说明行情适配
        (r"(适配.*?(行情|市场)|适用.*?(场景|条件|环境))", "适配说明", 8),
        (r"(牛.*?熊.*?切换|风格.*?轮动|行情.*?转换)", "市场周期意识", 6),
        (r"(分.*?(行情|市场|阶段).*?(策略|应对|调整))", "分行情策略", 6),
        # 量化/可回测
        (r"(可量化|可回测|可验证|可复现)", "可验证声明", 4),
        (r"(因子|指标.*?(公式|计算)|参数.*?(优化|调参))", "量化特征", 4),
        (r"(代码|code|python|回测.*?代码|策略.*?代码)", "含代码实现", 5),
        # 风控体系
        (r"(风控|风险控制|风险.*?管理|风险.*?体系)", "完整风控", 5),
        (r"(熔断|circuit\s*breaker|极端.*?(行情|风险).*?应对)", "极端风险应对", 5),
    ]

    def __init__(self):
        self.filter_stats = {
            "total": 0,
            "layer1_trashed": 0,
            "layer2_low_value": 0,
            "layer3_gems": 0,
            "uncertain": 0,
        }

    def filter(self, raw_content: str, source: str = "") -> dict:
        """
        三层极速筛选

        Returns:
            {verdict, score, layer, five_module_check, logic_bonuses, reasons, summary}
        """
        self.filter_stats["total"] += 1
        reasons = []

        # ── 第1层: 粗筛黑名单 ──
        blacklist_hits = []
        for pattern, label in self.BLACKLIST:
            if re.search(pattern, raw_content, re.IGNORECASE):
                blacklist_hits.append(label)

        if blacklist_hits:
            self.filter_stats["layer1_trashed"] += 1
            return {
                "verdict": "trash",
                "score": -100,
                "layer": 1,
                "reasons": [f"黑名单命中: {', '.join(blacklist_hits)}"],
                "five_module_check": {},
                "logic_bonuses": [],
                "source": source,
                "summary": raw_content[:200],
            }

        # ── 第2层: 结构快速校验(5大核心模块) ──
        module_check = {}
        for module_name, patterns in self.FIVE_MODULES.items():
            found = False
            for p in patterns:
                if re.search(p, raw_content, re.IGNORECASE):
                    found = True
                    break
            module_check[module_name] = found

        modules_found = sum(1 for v in module_check.values() if v)
        modules_missing = 5 - modules_found

        if modules_missing >= 3:
            self.filter_stats["layer2_low_value"] += 1
            missing = [k for k, v in module_check.items() if not v]
            return {
                "verdict": "low_value",
                "score": -20,
                "layer": 2,
                "reasons": [f"结构不完整: 缺失{', '.join(missing)} (仅{modules_found}/5模块)"],
                "five_module_check": module_check,
                "logic_bonuses": [],
                "source": source,
                "summary": raw_content[:200],
            }

        # ── 第3层: 逻辑闭环校验 ──
        logic_hits = []
        logic_score = 0
        for pattern, label, weight in self.LOGIC_BONUS:
            if re.search(pattern, raw_content, re.IGNORECASE):
                logic_hits.append(label)
                logic_score += weight

        # 基础分 = 模块完整度
        base_score = modules_found * 6  # 每个模块6分,满分30

        # 额外: 内容长度/代码检测
        if len(raw_content) >= 500:
            base_score += 5
        if len(raw_content) >= 1000:
            base_score += 5
        if re.search(r"(def\s|function\s|import\s|class\s|```)", raw_content):
            base_score += 5
            logic_hits.append("含代码实现")

        # 提到具体年份+月份的数据更可靠
        if re.search(r"20[12]\d\s*[年/-]\s*\d{1,2}\s*[月/-]", raw_content):
            base_score += 3
            logic_hits.append("含具体时间数据")

        total_score = base_score + logic_score

        # 判定精华等级
        if total_score >= 35 and modules_found >= 4:
            verdict = "gem"
            self.filter_stats["layer3_gems"] += 1
        elif total_score >= 25 and modules_found >= 3:
            verdict = "gem"
            self.filter_stats["layer3_gems"] += 1
        elif total_score >= 15:
            verdict = "uncertain"
            self.filter_stats["uncertain"] += 1
        else:
            verdict = "low_value"
            self.filter_stats["layer2_low_value"] += 1

        return {
            "verdict": verdict,
            "score": total_score,
            "layer": 3,
            "reasons": [f"模块{modules_found}/5 | 逻辑闭环{len(logic_hits)}项"],
            "logic_hits": logic_hits,
            "five_module_check": module_check,
            "logic_bonuses": logic_hits,
            "source": source,
            "summary": raw_content[:200],
        }

    def filter_batch(self, items: list) -> list:
        """批量三层过滤"""
        results = []
        for item in items:
            content = item.get("snippet", "") or item.get("content", "")
            source = item.get("source", "") or item.get("title", "")
            result = self.filter(content, source)
            result["original"] = item
            results.append(result)
        return results

    def get_gems(self, results: list) -> list:
        """获取精华内容(第3层通过的)"""
        return [r for r in results if r["verdict"] == "gem"]

    def get_trash(self, results: list) -> list:
        """获取黑名单丢弃的(第1层)"""
        return [r for r in results if r["verdict"] == "trash"]

    def get_low_value(self, results: list) -> list:
        """获取低价值内容(第2层结构不完整的)"""
        return [r for r in results if r["verdict"] == "low_value"]

    def report(self, results: list) -> str:
        """生成三层过滤报告"""
        stats = self.filter_stats
        gems = self.get_gems(results)
        trash = self.get_trash(results)
        low = self.get_low_value(results)

        lines = [
            f"三层过滤: 共{stats['total']}条",
            f"  第1层黑名单丢弃: {stats['layer1_trashed']}条",
            f"  第2层结构不完整: {stats['layer2_low_value']}条",
            f"  第3层精华: {stats['layer3_gems']}条",
            f"  待定: {stats['uncertain']}条",
        ]

        if trash:
            all_reasons = set()
            for t in trash:
                all_reasons.update(t.get("reasons", []))
            lines.append(f"  黑名单类型: {', '.join(list(all_reasons)[:5])}")

        if gems:
            lines.append(f"  精华来源: {', '.join(g.get('source', '?') for g in gems[:5])}")
            for g in gems[:3]:
                mod_check = g.get("five_module_check", {})
                mod_str = "/".join("✓" if v else "✗" for v in mod_check.values())
                lines.append(f"    [{g['source']}] 模块:{mod_str} | 逻辑:{', '.join(g.get('logic_hits', [])[:3])}")

        return "\n".join(lines)
