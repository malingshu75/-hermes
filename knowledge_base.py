# -*- coding: utf-8 -*-
"""
知识库管理 — 存储经过验证的精华交易知识
结构: {id, source, raw_content, category, quality_score, backtest_result, status, created_at, updated_at}
"""
import json
import os
import time
from datetime import datetime
from typing import Optional
from config import KNOWLEDGE_FILE


class KnowledgeBase:
    def __init__(self):
        self._ensure_file()
        self._load()

    def _ensure_file(self):
        if not os.path.exists(KNOWLEDGE_FILE):
            self._save({"entries": [], "stats": {"total": 0, "validated": 0, "trashed": 0, "deployed": 0}})

    def _load(self):
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def _save(self, data=None):
        if data:
            self.data = data
        with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add(self, source: str, raw_content: str, category: str, quality_score: float = 0.0) -> str:
        """添加新知识条目,返回entry_id"""
        entry = {
            "id": f"kb_{int(time.time())}_{len(self.data['entries'])}",
            "source": source,
            "raw_content": raw_content[:5000],
            "summary": raw_content[:200],
            "category": category,
            "tags": self._extract_tags(raw_content, category),
            "quality_score": quality_score,
            "status": "raw",  # raw -> validated -> deployed | trashed
            "backtest_result": None,
            "paper_trade_result": None,
            "live_trade_result": None,
            "lessons_learned": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self.data["entries"].append(entry)
        self.data["stats"]["total"] += 1
        self._save()
        return entry["id"]

    def validate(self, entry_id: str, backtest_result: dict):
        """回测验证通过,标记为validated"""
        for e in self.data["entries"]:
            if e["id"] == entry_id:
                e["status"] = "validated"
                e["backtest_result"] = backtest_result
                e["updated_at"] = datetime.now().isoformat()
                self.data["stats"]["validated"] += 1
                self._save()
                return
        raise ValueError(f"entry {entry_id} not found")

    def trash(self, entry_id: str, reason: str):
        """标记为糟粕丢弃"""
        for e in self.data["entries"]:
            if e["id"] == entry_id:
                e["status"] = "trashed"
                e["lessons_learned"].append(f"trashed: {reason}")
                e["updated_at"] = datetime.now().isoformat()
                self.data["stats"]["trashed"] += 1
                self._save()
                return
        raise ValueError(f"entry {entry_id} not found")

    def deploy(self, entry_id: str):
        """部署到实盘"""
        for e in self.data["entries"]:
            if e["id"] == entry_id:
                e["status"] = "deployed"
                e["updated_at"] = datetime.now().isoformat()
                self.data["stats"]["deployed"] += 1
                self._save()
                return
        raise ValueError(f"entry {entry_id} not found")

    def get_validated(self) -> list:
        """获取所有验证通过的知识"""
        return [e for e in self.data["entries"] if e["status"] == "validated"]

    def get_deployed(self) -> list:
        """获取所有已部署的知识"""
        return [e for e in self.data["entries"] if e["status"] == "deployed"]

    def get_by_category(self, category: str) -> list:
        return [e for e in self.data["entries"] if e["category"] == category]

    def get_raw(self) -> list:
        """获取待处理的原始知识"""
        return [e for e in self.data["entries"] if e["status"] == "raw"]

    def search(self, keyword: str) -> list:
        keyword_lower = keyword.lower()
        results = []
        for e in self.data["entries"]:
            if keyword_lower in json.dumps(e, ensure_ascii=False).lower():
                results.append(e)
        return results

    def stats(self) -> dict:
        return dict(self.data["stats"])

    def summary(self) -> str:
        s = self.data["stats"]
        validated = self.get_validated()
        deployed = self.get_deployed()
        lines = [
            f"知识库: {s['total']}条 | 验证通过{s['validated']}条 | 已部署{s['deployed']}条 | 丢弃{s['trashed']}条",
        ]
        if validated:
            lines.append(f"  验证通过: {', '.join(e['category'] for e in validated)}")
        if deployed:
            lines.append(f"  已部署: {', '.join(e['category'] for e in deployed)}")
        return "\n".join(lines)

    def _extract_tags(self, content: str, category: str) -> list:
        """从内容中提取标签"""
        tags = [category]
        keywords = {
            "网格": ["网格", "grid"],
            "趋势": ["趋势", "trend", "均线"],
            "反转": ["反转", "reverse", "超跌"],
            "量价": ["量价", "volume", "放量", "缩量"],
            "可转债": ["转债", "可转债", "CB"],
            "风控": ["风控", "止损", "回撤", "仓位"],
            "选股": ["选股", "筛选", "因子"],
            "择时": ["择时", "入场", "出场", "时机"],
        }
        content_lower = content.lower()
        for tag, kws in keywords.items():
            if any(kw in content_lower for kw in kws):
                tags.append(tag)
        return tags
