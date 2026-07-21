# -*- coding: utf-8 -*-
"""AI - 板块轮动+资金流向+情绪周期分析"""
import urllib.request, json, time, re

OUT = r'C:\cb_vwap\_market_breadth.json'

def get_sectors():
    """东方财富行业板块"""
    sectors = {}
    try:
        url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&fields=f2,f3,f4,f12,f14,f104,f105&fid=f3&fs=m:90+t2'
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0','Referer':'https://quote.eastmoney.com/'})
        data = urllib.request.urlopen(req, timeout=8).read().decode()
        names = re.findall(r'"f14":"(.*?)"', data)
        chgs = re.findall(r'"f3":(.*?),', data)
        amounts = re.findall(r'"f105":(.*?),', data)  # 成交额
        for n, c, a in zip(names, chgs, amounts):
            try: sectors[n] = {'chg': round(float(c),2), 'amt': round(float(a)/1e8,1)}
            except: pass
    except: pass
    return sectors

def get_concepts():
    """东方财富概念板块"""
    concepts = {}
    try:
        url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&fields=f2,f3,f12,f14,f104&fid=f3&fs=m:90+t3'
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0','Referer':'https://quote.eastmoney.com/'})
        data = urllib.request.urlopen(req, timeout=8).read().decode()
        names = re.findall(r'"f14":"(.*?)"', data)
        chgs = re.findall(r'"f3":(.*?),', data)
        for n, c in zip(names, chgs):
            try: concepts[n] = round(float(c),2)
            except: pass
    except: pass
    return concepts

def get_indices():
    """大盘指数"""
    codes = 'sh000001,sz399001,sz399006,sh000688,sh000300,sh000905'
    url = f'http://hq.sinajs.cn/list={codes}'
    req = urllib.request.Request(url, headers={'Referer':'https://finance.sina.com.cn'})
    data = urllib.request.urlopen(req, timeout=5).read().decode('gbk')
    idx = {}
    names = ['上证','深证','创业板','科创50','沪深300','中证500']
    for line, name in zip(data.strip().split('\n'), names):
        parts = line.split('"')[1].split(',')
        px=float(parts[3]) if parts[3] else 0
        pre=float(parts[2]) if parts[2] else 0
        chg=(px-pre)/pre*100 if pre else 0
        amt=float(parts[9])/1e8 if parts[9] else 0
        idx[name] = {'px':round(px,2),'chg':round(chg,2),'amt':round(amt,0)}
    return idx

def analyze():
    idx = get_indices()
    sectors = get_sectors()
    concepts = get_concepts()
    
    avg_chg = sum(v['chg'] for v in idx.values())/len(idx) if idx else 0
    
    # 强势板块(涨幅>1%)
    strong_s = {k:v for k,v in sectors.items() if v['chg']>1}
    # 强势概念(涨幅>3%)  
    strong_c = {k:v for k,v in concepts.items() if v>3}
    # 弱势板块(跌幅>1%)
    weak_s = {k:v for k,v in sectors.items() if v['chg']<-1}
    
    # 情绪判断
    if avg_chg>1 and len(strong_s)>10: mood='贪婪'
    elif avg_chg>0.3: mood='乐观'
    elif avg_chg>-0.3: mood='震荡'
    elif avg_chg>-1: mood='恐惧'
    else: mood='绝望'
    
    result = {
        "time": time.strftime('%H:%M:%S'),
        "indices": idx,
        "avg_chg": round(avg_chg,2),
        "mood": mood,
        "strong_sectors": {k:v['chg'] for k,v in sorted(strong_s.items(), key=lambda x:-x[1]['chg'])[:10]},
        "strong_concepts": dict(sorted(strong_c.items(), key=lambda x:-x[1])[:10]),
        "weak_sectors": {k:v['chg'] for k,v in sorted(weak_s.items(), key=lambda x:x[1]['chg'])[:5]},
        "advice": {
            "贪婪": "警惕追高,逐步止盈",
            "乐观": "积极做多,加仓强势板块",
            "震荡": "精选个股,控制仓位",
            "恐惧": "减少开仓,等企稳信号",
            "绝望": "准备抄底,注意反转"
        }.get(mood, "")
    }
    
    with open(OUT, 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result

if __name__ == '__main__':
    r = analyze()
    print(f'{r["time"]} 大盘{r["avg_chg"]:+.2f}% 情绪:{r["mood"]} → {r["advice"]}')
    print(f'强势板块: {list(r["strong_sectors"].keys())[:5]}')
    print(f'强势概念: {list(r["strong_concepts"].keys())[:5]}')
