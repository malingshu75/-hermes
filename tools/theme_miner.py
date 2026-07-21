# -*- coding: utf-8 -*-
"""AI - 题材挖掘: 识别热点/主流/资金方向/市场分歧"""
import urllib.request, json, re, time

OUT = r'C:\cb_vwap\_theme_report.json'

def get_hot_concepts(top_n=20):
    """当前最热概念板块: 涨幅+资金流入"""
    concepts = []
    try:
        url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&fields=f2,f3,f12,f14,f62,f104,f105&fid=f3&fs=m:90+t3'
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0','Referer':'https://quote.eastmoney.com/'})
        data = urllib.request.urlopen(req, timeout=8).read().decode()
        names = re.findall(r'"f14":"(.*?)"', data)
        chgs = re.findall(r'"f3":(.*?),', data)
        flows = re.findall(r'"f62":(.*?),', data) if 'f62' in data else []
        
        for i, (n, c) in enumerate(zip(names, chgs)):
            try:
                chg = float(c)
                flow = float(flows[i])/1e8 if i < len(flows) else 0
                if chg > 0.5 or flow > 0:
                    concepts.append({
                        'name': n, 'chg': round(chg,2),
                        'flow': round(flow,2),
                        'score': round(chg*2 + flow*3, 1)
                    })
            except: pass
    except: pass
    
    concepts.sort(key=lambda x: -x['score'])
    return concepts[:top_n]

def get_hot_sectors(top_n=15):
    """行业板块热度"""
    sectors = []
    try:
        url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=30&po=1&np=1&fields=f2,f3,f12,f14,f62,f184&fid=f3&fs=m:90+t2'
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0','Referer':'https://quote.eastmoney.com/'})
        data = urllib.request.urlopen(req, timeout=8).read().decode()
        names = re.findall(r'"f14":"(.*?)"', data)
        chgs = re.findall(r'"f3":(.*?),', data)
        
        for n, c in zip(names, chgs):
            try:
                chg = float(c)
                if abs(chg) > 0.3:
                    sectors.append({'name': n, 'chg': round(chg,2)})
            except: pass
    except: pass
    
    sectors.sort(key=lambda x: -x['chg'])
    return sectors[:top_n]

def detect_divergence():
    """市场分歧检测: 价涨量缩/价跌量增/板块分化"""
    signals = []
    
    # 1. 强势板块vs弱势板块数量对比
    # 2. 涨停vs跌停比例
    # 3. 北向资金方向
    
    # 简化版: 用已知数据判断
    return signals

def analyze_theme_cycle():
    """题材周期: 启动→发酵→高潮→退潮"""
    concepts = get_hot_concepts(30)
    sectors = get_hot_sectors(15)
    
    if not concepts:
        return {"error": "API未返回数据"}
    
    # 热度评分
    avg_chg = sum(c['chg'] for c in concepts[:10])/min(10, len(concepts))
    top5_chg = sum(c['chg'] for c in concepts[:5])/min(5, len(concepts))
    
    # 周期判断
    if avg_chg > 3: cycle = '高潮期'
    elif avg_chg > 1.5: cycle = '发酵期'
    elif avg_chg > 0.5: cycle = '启动期'
    else: cycle = '冰点期'
    
    # 找主流题材(涨幅最大+持续性最好)
    mainstream = [c for c in concepts if c['chg'] > 2]
    
    # 找分歧: 板块之间涨幅差距
    if concepts:
        gap = concepts[0]['chg'] - concepts[-1]['chg'] if len(concepts)>1 else 0
        divergence = '分歧大' if gap > 5 else '分歧小' if gap < 2 else '正常'
    else:
        divergence = '未知'
    
    result = {
        'time': time.strftime('%H:%M:%S'),
        'cycle': cycle,
        'heat_score': round(avg_chg, 1),
        'divergence': divergence,
        'mainstream': [{'name': c['name'], 'chg': c['chg']} for c in mainstream[:5]],
        'hot_concepts': [{'name': c['name'], 'chg': c['chg'], 'flow': c.get('flow',0)} for c in concepts[:10]],
        'hot_sectors': [{'name': s['name'], 'chg': s['chg']} for s in sectors[:8]],
        'advice': {
            '高潮期': '警惕退潮,减少新开仓,逐步止盈',
            '发酵期': '积极参与主流题材,加仓龙头',
            '启动期': '精选题材龙头,试探性建仓',
            '冰点期': '空仓等待,保存实力'
        }.get(cycle, ''),
        'trading_direction': ', '.join(c['name'] for c in mainstream[:3]) if mainstream else '无明确方向'
    }
    
    with open(OUT, 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return result

if __name__ == '__main__':
    r = analyze_theme_cycle()
    if 'error' not in r:
        print(f'题材周期: {r["cycle"]} 热度:{r["heat_score"]} 分歧:{r["divergence"]}')
        print(f'主流方向: {r["trading_direction"]}')
        print(f'操作建议: {r["advice"]}')
    else:
        print(f'API未就绪: {r["error"]}')
