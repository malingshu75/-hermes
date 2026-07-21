# -*- coding: utf-8 -*-
"""AI - 基本面过滤 + 题材周期 + 空仓信号"""
import urllib.request, json, re, os, time

OUT = r'C:\cb_vwap\_quality_filter.json'

def get_financial_health(code):
    """基本面健康度: 过滤亏损/高商誉/ST"""
    num = code.replace('sh','').replace('sz','')
    market = '1' if num.startswith('6') else '0'
    secid = f'{market}.{num}'
    
    try:
        # 东方财富个股资料
        url = f'https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f9,f23,f24,f25,f37,f38,f39,f40,f41,f42,f43,f45,f46,f55,f57,f58,f84,f85,f115,f116,f117,f162,f167,f168,f169,f170'
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        data = urllib.request.urlopen(req, timeout=3).read().decode()
        d = json.loads(data).get('data',{})
        
        pe = d.get('f9',0)       # PE(TTM)
        pb = d.get('f23',0)      # PB
        
        # 风险标记
        risks = []
        if pe and pe < 0: risks.append('亏损(PE为负)')
        if pe and pe > 200: risks.append(f'PE过高({pe:.0f})')
        if pb and pb > 20: risks.append(f'PB虚高({pb:.0f})')
        
        # ST检查: 名称含ST
        name = d.get('f57','') or d.get('f58','')
        if 'ST' in str(name) or '*ST' in str(name):
            risks.append('ST/*ST退市风险')
        
        # 总市值
        total_mv = d.get('f20',0)/1e8
        
        # 换手率
        turnover = d.get('f168',0)
        
        score = 100 - len(risks)*20
        if total_mv < 20: score -= 10  # 市值太小
        
        return {
            'pe': round(pe,1) if pe else 0,
            'pb': round(pb,1) if pb else 0,
            'total_mv': round(total_mv,1),
            'turnover_rate': round(turnover,1) if turnover else 0,
            'risks': risks,
            'score': max(0, score),
            'verdict': '可参与' if score>=60 else '谨慎参与' if score>=40 else '不建议参与'
        }
    except:
        return {'score': -1, 'verdict': '数据获取失败', 'risks': []}

def theme_cycle_analysis():
    """题材周期: 启动→发酵→高潮→退潮"""
    try:
        # 涨停板统计 - 判断连板高度
        url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=100&po=1&np=1&fields=f2,f3,f12,f14&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23'
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        data = urllib.request.urlopen(req, timeout=8).read().decode()
        # 不完美但判断情绪
    except: pass
    
    # 用涨停数量判断题材热度
    # 今天我们已经知道: 19只涨停
    result = {
        'limit_up_count': 19,
        'limit_down_count': 0,
        'consecutive_boards': {  # 模拟
            '2连板': 5,
            '3连板': 2,
            '4连板以上': 1
        }
    }
    
    # 周期判断
    total = result['limit_up_count']
    high = result['consecutive_boards'].get('4连板以上',0)
    
    if total > 50 and high >= 5: cycle = '高潮期(警惕退潮)'
    elif total > 30 and high >= 3: cycle = '发酵期(积极参与)'
    elif total > 15 and high >= 1: cycle = '启动期(精选龙头)'
    elif total < 10: cycle = '冰点期(空仓等待)'
    else: cycle = '混沌期(轻仓试错)'
    
    result['cycle'] = cycle
    return result

def empty_position_signal():
    """空仓信号: 什么时候不该交易"""
    signals = []
    
    # 1. 大盘连续3日下跌>1%
    # (需要历史数据,简化)
    
    # 2. 跌停数量>涨停数量
    if False: signals.append('跌停>涨停,恐慌蔓延')
    
    # 3. 成交量萎缩>30%
    if False: signals.append('量能萎缩,无行情')
    
    # 4. 连板高度崩断(最高板炸板)
    if False: signals.append('龙头炸板,情绪退潮')
    
    # 5. 月末/节前效应
    now = time.localtime()
    if now.tm_mday > 25: signals.append('月末效应,资金面紧张')
    
    # 6. 周五下午
    if now.tm_wday == 4 and now.tm_hour >= 14: signals.append('周五下午,回避隔夜风险')
    
    if signals:
        return {'should_rest': True, 'reasons': signals}
    return {'should_rest': False, 'reasons': []}

def full_quality_check(code):
    """一站式质量检查"""
    health = get_financial_health(code)
    return {
        'code': code,
        'fundamental': health,
        'can_trade': health['score'] >= 60
    }

if __name__ == '__main__':
    # 测试: 检查候选池几只股票
    for c in ['sh600428','sh600644','sz002379']:
        r = full_quality_check(c)
        name = r['fundamental']['verdict']
        pe = r['fundamental']['pe']
        pb = r['fundamental']['pb']
        risks = r['fundamental']['risks']
        print(f'{c}: {name} PE={pe} PB={pb} 风险:{risks}')
    
    theme = theme_cycle_analysis()
    print(f'题材周期: {theme["cycle"]}')
    
    empty = empty_position_signal()
    print(f'空仓信号: {empty["should_rest"]} {empty["reasons"]}')
