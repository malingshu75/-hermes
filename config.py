# -*- coding: utf-8 -*-
"""
AI炒股机器人 - 配置
从零自学成长的量化交易AI系统
"""
import os
import json

# ── 路径 ──
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
KNOWLEDGE_FILE = os.path.join(DATA_DIR, "knowledge.json")
EVOLUTION_FILE = os.path.join(DATA_DIR, "evolution.json")
TRADE_LOG = os.path.join(DATA_DIR, "trade_log.json")

# ── 外部系统路径 ──
AI_TRADING_DIR = r"D:\AI炒股"           # 现有策略代码
GM_TEAM_DIR = r"E:\掘金量化多Agent团队"  # GM SDK配置
TDX_DATA_WIN = r"C:\工作区\tdx\vipdoc"     # 通达信数据(Windows路径)
TDX_DATA_WSL = "/mnt/c/工作区/tdx/vipdoc"     # 通达信数据(WSL路径)
TDX_DATA = TDX_DATA_WSL if os.path.exists("/mnt/c/工作区/tdx/vipdoc") else TDX_DATA_WIN
CONFIG_PY = os.path.join(GM_TEAM_DIR, "config.py")  # GM凭据

# ── GM 账户 ──
ACCOUNTS = {
    "AI新账户": "2a472909-7763-11f1-95b1-00163e022aa6",
    "旧账户": "bc821533-5a82-11f1-bc2f-00163e022aa6",
}

# ── 学习配置 ──
LEARNING = {
    "search_queries_per_day": 5,       # 每日搜索主题数
    "min_backtest_days": 250,          # 最少回测天数
    "min_backtest_trades": 50,         # 最少回测交易笔数
    "paper_trade_days": 20,            # 模拟交易验证天数
    "paper_trade_size": 10000,         # 模拟资金规模
    "daily_review_for": 30,            # 每日复盘保留天数
    "max_knowledge_entries": 500,      # 知识库最大条目数
    "evolution_generations": 10,       # 进化代数
}

# ── 合规底线 ──
COMPLIANCE = {
    "min_daily_volume": 30_000_000,   # 日均成交额下限(3000万)
    "exclude_st": True,               # 排除ST
    "exclude_new_stocks": 60,         # 排除上市不足60天新股
    "max_single_position_pct": 0.08,  # 单票最大仓位8%
    "max_total_position_pct": 0.70,   # 总仓位上限70%
    "daily_loss_circuit_breaker": 0.05, # 日亏5%熔断
}

# ── 阶段定义 ──
STAGES = {
    "beginner": {
        "name": "小白初学",
        "conditions": {"total_trades": (0, 100), "win_rate": (0, 0.45)},
        "search_focus": ["K线基础", "均线系统", "MACD指标", "可转债入门", "散户基础经验", "成交量分析"],
        "trade_mode": "paper_only",
    },
    "intermediate": {
        "name": "进阶交易者",
        "conditions": {"total_trades": (100, 500), "win_rate": (0.40, 0.55)},
        "search_focus": ["板块轮动", "趋势战法", "网格交易", "资金流分析", "回撤控制", "量化因子", "季节性规律"],
        "trade_mode": "light_live",
    },
    "advanced": {
        "name": "顶级高手",
        "conditions": {"total_trades": (500, 99999), "win_rate": (0.45, 1.0)},
        "search_focus": ["多策略融合", "牛熊切换", "长期复利", "极端行情应对", "因子优化", "头部私募策略"],
        "trade_mode": "full_live",
    },
}

os.makedirs(DATA_DIR, exist_ok=True)
