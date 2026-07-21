# -*- coding: utf-8 -*-
"""AI - 交易决策强制过滤器: 不符合条件就拒绝"""
import json, os

RULES_FILE = r'C:\cb_vwap\_trade_rules.json'

# 从回测中提炼的铁律
RULES = {
    "entry": [
        {"name": "禁止追涨", "check": lambda s: s.get('chg',0) < 5, "reason": "涨幅>5%不追,回测胜率<40%"},
        {"name": "禁止放量突破", "check": lambda s: s.get('vol_ratio',99) < 2.0, "reason": "量比>2x的突破次日胜率42.6%"},
        {"name": "禁止连涨追高", "check": lambda s: s.get('up_streak',0) < 3, "reason": "连涨3天追高次日胜率37.2%"},
        {"name": "禁止巨振", "check": lambda s: s.get('amp',0) < 15, "reason": "振幅>15%次日胜率33.7%"},
        {"name": "优先缩量回调", "check": lambda s: s.get('vol_ratio',1) <= 1.2 or s.get('down_days',0) >= 2, "reason": "缩量+连跌=最佳买点61.5%胜率"},
        {"name": "要求资金流入", "check": lambda s: s.get('main_flow',0) > -1000, "reason": "主力净流出>1000万不买"},
    ],
    "exit": [
        {"name": "止损铁律", "check": lambda p: p.get('pnl_pct',0) > -3, "reason": "浮亏>3%无条件止损"},
        {"name": "止盈分批", "check": lambda p: p.get('pnl_pct',0) < 8, "reason": "浮盈>8%至少卖一半"},
    ],
    "risk": [
        {"name": "单票上限", "max_pct": 5, "reason": "单票不超过总资产5%"},
        {"name": "日亏熔断", "max_loss": 2, "reason": "单日亏损>2%停止开仓"},
        {"name": "集中度", "max_positions": 8, "reason": "最多同时持有8只"},
    ]
}

def check_entry(stock_info):
    """入市前强制检查"""
    violations = []
    for rule in RULES["entry"]:
        if not rule["check"](stock_info):
            violations.append({"rule": rule["name"], "reason": rule["reason"]})
    return {
        "approved": len(violations) == 0,
        "violations": violations,
        "verdict": "✅ 通过全部检查" if not violations else f"❌ {len(violations)}项违规,拒绝交易"
    }

def check_exit(pos_info):
    """退出检查"""
    violations = []
    for rule in RULES["exit"]:
        if not rule["check"](pos_info):
            violations.append({"rule": rule["name"], "reason": rule["reason"], "action": "立即执行"})
    return violations

def save_rules():
    with open(RULES_FILE, 'w') as f:
        json.dump(RULES, f, ensure_ascii=False, indent=2)

def load_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE) as f:
            return json.load(f)
    return RULES

# 快速测试
if __name__ == '__main__':
    # 测试: 追涨被拒绝
    bad_trade = {"chg": 7.5, "vol_ratio": 2.5, "up_streak": 3, "amp": 16, "down_days": 0}
    r = check_entry(bad_trade)
    print(f'追涨7.5%的票: {r["verdict"]}')
    for v in r['violations']:
        print(f'  ❌ {v["rule"]}: {v["reason"]}')
    
    # 测试: 好交易通过
    good_trade = {"chg": 2.0, "vol_ratio": 0.8, "up_streak": 0, "amp": 6, "down_days": 3}
    r2 = check_entry(good_trade)
    print(f'\\n缩量回调的票: {r2["verdict"]}')
