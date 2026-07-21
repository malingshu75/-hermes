# -*- coding: utf-8 -*-
"""AI - 情报系统: 财联社快讯+淘股吧情绪+龙虎榜验证"""
import urllib.request, json, re, time

OUT = r'C:\cb_vwap\_intel_report.json'

def cls_telegraph(limit=20):
    """财联社电报: 7×24快讯,抓盘中催化"""
    try:
        url = 'https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8.4.6'
        headers = {'User-Agent':'Mozilla/5.0','Referer':'https://www.cls.cn/'}
        # 财联社电报API
        api = 'https://www.cls.cn/v3/depth/home/assembled/1000'
        req = urllib.request.Request(api, headers=headers)
        data = urllib.request.urlopen(req, timeout=5).read().decode()
        d = json.loads(data)
        items = d.get('data',{}).get('roll_data',[])
        news = []
        for item in items[:limit]:
            title = item.get('title','')
            content = item.get('content','')
            ctime = item.get('ctime',0)
            # 过滤: 只保留A股相关的
            keywords = ['A股','涨停','跌停','板块','政策','业绩','公告','重组','停牌','复牌','减持','增持']
            if any(k in title+content for k in keywords):
                news.append({
                    'time': time.strftime('%H:%M', time.localtime(ctime)),
                    'title': title[:80],
                    'type': 'policy' if '政策' in title else 'company' if '公告' in title else 'market'
                })
        return news
    except:
        return []

def taoguba_sentiment():
    """淘股吧情绪: 连板高度+题材热度"""
    try:
        url = 'https://www.taoguba.com.cn/stockBoard'
        headers = {'User-Agent':'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        data = urllib.request.urlopen(req, timeout=5).read().decode('gbk',errors='ignore')
        # 提取连板统计
        hot = re.findall(r'连板.*?(\d+)', data)
        return {'连板高度': hot[0] if hot else '?', 'source': '淘股吧'}
    except:
        return {'sentiment': '获取失败'}

def dragon_tiger_analysis():
    """龙虎榜: 游资席位+净买入"""
    try:
        # 东方财富龙虎榜 - 使用个股资金流替代
        url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=20&po=1&np=1&fields=f3,f12,f14,f62,f184&fid=f62&fs=m:0+t:6,m:0+t:80'
        headers = {'User-Agent':'Mozilla/5.0','Referer':'https://data.eastmoney.com/'}
        req = urllib.request.Request(url, headers=headers)
        data = urllib.request.urlopen(req, timeout=5).read().decode()
        names = re.findall(r'"f14":"(.*?)"', data)
        flows = re.findall(r'"f62":(.*?),', data)
        top_buy = []
        for n, f in zip(names, flows):
            try:
                flow = float(f)/1e4
                if flow > 1000:
                    top_buy.append({'name': n, 'flow': round(flow,0)})
            except: pass
        return top_buy[:10]
    except:
        return []

def north_bound_sentiment():
    """北向资金情绪"""
    try:
        url = 'https://push2.eastmoney.com/api/qt/kamt.kline/get?fields1=f1,f2,f3,f4&fields2=f51,f52,f53,f54&klt=101&lmt=5'
        headers = {'User-Agent':'Mozilla/5.0','Referer':'https://data.eastmoney.com/'}
        req = urllib.request.Request(url, headers=headers)
        data = urllib.request.urlopen(req, timeout=5).read().decode()
        d = json.loads(data).get('data',{})
        hgt = d.get('hk2sh',{}).get('klines',[])
        sgt = d.get('hk2sz',{}).get('klines',[])
        recent = []
        for i in range(min(5, len(hgt))):
            h = hgt[-(i+1)].split(',')
            s = sgt[-(i+1)].split(',') if i < len(sgt) else ['','0']
            net = float(h[1]) + float(s[1])
            recent.append({'date': h[0][:10], 'net': round(net/1e8,1)})
        return recent
    except:
        return []

def generate_intel():
    """生成综合情报"""
    cls = cls_telegraph()
    taoguba = taoguba_sentiment()
    dragon = dragon_tiger_analysis()
    north = north_bound_sentiment()
    
    # 综合情绪判断
    north_net = sum(n['net'] for n in north[:3])/min(3, len(north)) if north else 0
    north_mood = '持续流入' if north_net > 10 else '小幅流入' if north_net > 0 else '流出'
    
    hot_themes = set()
    for n in cls:
        for kw in ['AI','算力','新能源','光伏','医药','消费','军工','机器人','芯片','低空','红利']:
            if kw in n.get('title',''): hot_themes.add(kw)
    
    result = {
        'time': time.strftime('%H:%M:%S'),
        'cls_news': cls[:10],
        'north_bound': {'recent': north, 'mood': north_mood, 'net3d': round(north_net,1)},
        'dragon_tiger_top_buy': dragon[:5],
        'taoguba': taoguba,
        'hot_themes': list(hot_themes),
        'trading_advice': {
            True: '北向流入+题材活跃=积极做多',
            False: '北向流出=控制仓位'
        }.get(north_net > 0, '观望')
    }
    
    with open(OUT, 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return result

if __name__ == '__main__':
    r = generate_intel()
    print(f'情报生成: {r["time"]}')
    print(f'北向: {r["north_bound"]["mood"]} 近3日净{r["north_bound"]["net3d"]}亿')
    print(f'热点题材: {r["hot_themes"]}')
    print(f'建议: {r["trading_advice"]}')
