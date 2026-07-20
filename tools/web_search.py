# -*- coding: utf-8 -*-
"""
工具1: web_search — 联网搜索炒股知识
自主检索全网炒股干货、实战经验、量化策略、技术分析教程
"""
import json
import time
from datetime import datetime
from typing import Optional
import urllib.request
import urllib.parse
import re


class WebSearch:
    """
    联网搜索工具 — AI自主学习核心入口
    
    搜索源:
    - 搜索引擎(百度/Bing)基础搜索
    - 特定站点定向搜索(雪球/淘股吧/集思录)
    - 学术论文(知网/arXiv)
    
    搜索策略按阶段自动调整:
    - 小白阶段: 基础K线/均线/可转债入门
    - 进阶阶段: 板块轮动/趋势/网格/风控
    - 高手阶段: 多策略融合/牛熊切换/因子优化
    """

    # 搜索主题分类
    SEARCH_CATEGORIES = {
        "技术分析": ["K线形态", "均线系统", "MACD用法", "RSI指标", "布林带", "成交量分析", "筹码分布"],
        "交易策略": ["网格交易", "趋势跟踪", "突破交易", "反转策略", "日内T+0", "波段操作", "套利策略"],
        "风险管理": ["仓位管理", "止损方法", "回撤控制", "资金管理", "凯利公式", "风险平价"],
        "可转债": ["可转债基础", "双低策略", "强赎条款", "下修博弈", "折价套利", "转债网格"],
        "量化方法": ["因子选股", "回测框架", "机器学习选股", "深度学习量化", "统计套利"],
        "市场规律": ["A股季节性", "板块轮动", "牛熊特征", "情绪指标", "涨跌停规律"],
        "实战经验": ["散户心得", "实盘复盘", "盈亏分析", "交易心理", "策略迭代"],
    }

    def __init__(self):
        self.search_count = 0
        self.search_history = []
        self.session = self._create_session()

    def _create_session(self) -> dict:
        return {
            "started_at": datetime.now().isoformat(),
            "total_searches": 0,
            "categories_covered": set(),
        }

    def search(self, keyword: str, category: str = "交易策略", 
               max_results: int = 10) -> dict:
        """
        执行一次联网搜索
        
        Args:
            keyword: 搜索关键词
            category: 知识分类
            max_results: 最大结果数
            
        Returns:
            {results: [{title, url, snippet, source, relevance}], 
             total_found, search_time, category}
        """
        self.search_count += 1
        self.session["total_searches"] += 1
        self.session["categories_covered"].add(category)
        
        start_time = time.time()
        
        # 构建搜索URL (使用Bing作为搜索引擎, 限制中文内容)
        encoded_keyword = urllib.parse.quote(f"{keyword} 股票 量化 策略")
        search_url = f"https://www.bing.com/search?q={encoded_keyword}&count={max_results}&setlang=zh-cn"
        
        results = []
        try:
            req = urllib.request.Request(
                search_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                results = self._parse_bing_results(html, max_results)
        except Exception as e:
            # 搜索引擎不可用时，标记但继续
            results = [{
                "title": f"搜索失败: {keyword}",
                "url": "",
                "snippet": f"网络搜索暂时不可用: {str(e)[:100]}。将使用本地知识库和已有策略数据。",
                "source": "error",
                "relevance": 0,
            }]
        
        elapsed = round(time.time() - start_time, 2)
        
        search_record = {
            "keyword": keyword,
            "category": category,
            "results_count": len(results),
            "search_time": elapsed,
            "timestamp": datetime.now().isoformat(),
        }
        self.search_history.append(search_record)
        
        return {
            "results": results,
            "total_found": len(results),
            "search_time": elapsed,
            "category": category,
            "keyword": keyword,
        }

    def _parse_bing_results(self, html: str, max_results: int) -> list:
        """解析Bing搜索结果"""
        results = []
        # 简单的正则解析搜索结果
        # Bing搜索结果在 <li class="b_algo"> 中
        pattern = r'<li class="b_algo"[^>]*>.*?<h2[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<p[^>]*>(.*?)</p>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        
        for i, (url, title_html, snippet_html) in enumerate(matches[:max_results]):
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet_html).strip()
            
            # 判断来源
            source = "web"
            if "xueqiu.com" in url:
                source = "雪球"
            elif "taoguba.com" in url:
                source = "淘股吧"
            elif "jisilu" in url:
                source = "集思录"
            elif "zhihu.com" in url:
                source = "知乎"
            elif "eastmoney.com" in url:
                source = "东方财富"
            
            results.append({
                "title": title[:100],
                "url": url,
                "snippet": snippet[:300],
                "source": source,
                "relevance": 10 - i,  # 排序靠前 = 更相关
            })
        
        return results

    def search_daily_batch(self, focus_topics: list, per_topic: int = 2) -> list:
        """
        每日批量学习 — 按关注主题搜索
        
        Args:
            focus_topics: 当前阶段关注的搜索主题列表
            per_topic: 每个主题搜索次数
            
        Returns:
            [{topic, results}]
        """
        all_results = []
        for topic in focus_topics[:5]:  # 每日最多5个主题
            # 找到主题所属分类
            category = "交易策略"
            for cat, topics in self.SEARCH_CATEGORIES.items():
                if any(t in topic for t in topics):
                    category = cat
                    break
            
            result = self.search(topic, category=category, max_results=per_topic * 2)
            all_results.append({"topic": topic, "category": category, "result": result})
        
        return all_results

    def get_search_topics(self, stage: str) -> list:
        """根据学习阶段返回推荐搜索主题"""
        from config import STAGES
        if stage in STAGES:
            return STAGES[stage]["search_focus"]
        return STAGES["beginner"]["search_focus"]


# 便捷函数
def search(keyword: str, category: str = "交易策略") -> dict:
    """快速搜索"""
    return WebSearch().search(keyword, category)
