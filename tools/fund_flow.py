# -*- coding: utf-8 -*-
"""AI - 资金流向 + 组合风控"""
import urllib.request, json, math

# ═══════════════════════════════════════
#  资金流向
# ═══════════════════════════════════════

def north_bound_flow():
    """北向资金: 沪股通+深股通净流入"""
    try:
        url = 'https://push2.eastmoney.com/api/qt/kamt.kline/get?fields1=f1,f2,f3,f4&fields2=f51,f52,f53,f54'
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.eastmoney.com/'})
        data = urllib.request.urlopen(req, timeout=8).read().decode()
        d = json.loads(data).get('data',{})
        # 取最近一天
        hgt = d.get('hk2sh',{}).get('klines',[])
        sgt = d.get('hk2sz',{}).get('klines',[])
        if hgt and sgt:
            last_hgt = hgt[-1].split(',')
            last_sgt = sgt[-1].split(',')
            net = float(last_hgt[1]) + float(last_sgt[1])
            return {'net_flow': round(net/1e8,2), 'date': last_hgt[0][:10]}
    except: pass
    return None

def sector_fund_flow():
    """行业资金净流入排名"""
    try:
        url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=20&po=1&np=1&fields=f3,f12,f14,f62,f184,f66&fid=f62&fs=m:90+t2'
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.eastmoney.com/'})
        data = urllib.request.urlopen(req, timeout=8).read().decode()
        import re
        names = re.findall(r'"f14":"(.*?)"', data)
        flows = re.findall(r'"f62":(.*?),', data)  # 主力净流入
        chgs = re.findall(r'"f3":(.*?),', data)
        result = {}
        for n,f,c in zip(names, flows, chgs):
            try: result[n] = {'flow': round(float(f)/1e8,2), 'chg': round(float(c),2)}
            except: pass
        return result
    except: pass
    return {}

def stock_fund_flow(code):
    """个股资金流向"""
    num = code.replace('sh','').replace('sz','')
    market = '1' if num.startswith('6') else '0'
    secid = f'{market}.{num}'
    try:
        url = f'https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f62,f184,f66,f69,f70,f78'
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        data = urllib.request.urlopen(req, timeout=3).read().decode()
        d = json.loads(data).get('data',{})
        return {
            'price': d.get('f43',0)/100 if d.get('f43') else 0,
            'main_flow': round(d.get('f62',0)/1e4,2),    # 主力净流入(万)
            'super_large': round(d.get('f66',0)/1e4,2),  # 超大单(万)
            'large': round(d.get('f69',0)/1e4,2),        # 大单(万)
            'medium': round(d.get('f70',0)/1e4,2),       # 中单(万)
            'small': round(d.get('f78',0)/1e4,2),        # 小单(万)
        }
    except: return None

# ═══════════════════════════════════════
#  组合风控
# ═══════════════════════════════════════

def calc_var(daily_returns, confidence=0.95):
    """历史VaR: 在给定置信度下的最大日亏损%"""
    if len(daily_returns) < 10: return 0
    sorted_ret = sorted(daily_returns)
    idx = int(len(sorted_ret) * (1-confidence))
    return abs(sorted_ret[idx]) * 100

def calc_sharpe(daily_returns, risk_free=0.02):
    """夏普比率: (年化收益-无风险)/年化波动"""
    if len(daily_returns) < 10: return 0
    avg_daily = sum(daily_returns)/len(daily_returns)
    std_daily = (sum((r-avg_daily)**2 for r in daily_returns)/len(daily_returns))**0.5
    if std_daily == 0: return 0
    # 年化
    annual_ret = avg_daily * 250
    annual_std = std_daily * (250**0.5)
    return round((annual_ret - risk_free)/annual_std, 2)

def calc_max_drawdown(equity_curve):
    """最大回撤%"""
    if not equity_curve: return 0
    peak = equity_curve[0]
    max_dd = 0
    for v in equity_curve:
        if v > peak: peak = v
        dd = (peak-v)/peak*100
        max_dd = max(max_dd, dd)
    return round(max_dd, 2)

def portfolio_risk(positions, daily_returns_dict):
    """组合风险评估
    positions: [{code, weight, volatility}]
    """
    total_weight = sum(p.get('weight',0) for p in positions)
    concentration = max(p.get('weight',0) for p in positions)/total_weight*100 if total_weight>0 else 0
    
    # 简单组合VaR: 加权平均
    weighted_var = 0
    for p in positions:
        rets = daily_returns_dict.get(p.get('code',''), [])
        if rets:
            var = calc_var(rets)
            weighted_var += var * p.get('weight',0)
    
    risk_score = weighted_var + concentration*0.5
    level = '低风险' if risk_score<2 else '中风险' if risk_score<5 else '高风险' if risk_score<10 else '极高风险'
    
    return {
        'var_95': round(weighted_var, 2),
        'concentration_pct': round(concentration, 1),
        'risk_score': round(risk_score, 1),
        'level': level,
        'advice': {
            '低风险': '可加仓到15%',
            '中风险': '保持仓位5-10%',
            '高风险': '减仓到5%以下',
            '极高风险': '减仓或清仓'
        }.get(level, '')
    }

def position_correlation(returns_a, returns_b):
    """两只股票收益相关性"""
    n = min(len(returns_a), len(returns_b))
    if n < 5: return 0
    avg_a = sum(returns_a[:n])/n
    avg_b = sum(returns_b[:n])/n
    cov = sum((returns_a[i]-avg_a)*(returns_b[i]-avg_b) for i in range(n))/n
    std_a = (sum((r-avg_a)**2 for r in returns_a[:n])/n)**0.5
    std_b = (sum((r-avg_b)**2 for r in returns_b[:n])/n)**0.5
    if std_a*std_b==0: return 0
    return round(cov/(std_a*std_b), 2)
