# -*- coding: utf-8 -*-
"""实时行情融合 — 解决TDX日线盘后更新滞后问题"""
import urllib.request
from datetime import datetime


def get_realtime_bar(code: str) -> dict:
    """
    从新浪获取今日实时K线
    
    Args:
        code: 如 'sh603137', 'sz000555'
    Returns:
        {date, open, high, low, close, amount, volume} 或 None
    """
    # 格式化新浪代码
    num = code.replace('sh','').replace('sz','').replace('SHSE.','').replace('SZSE.','')
    if code.startswith('sh') or num.startswith('6'):
        sina = f'sh{num}'
    else:
        sina = f'sz{num}'
    
    try:
        url = f'http://hq.sinajs.cn/list={sina}'
        req = urllib.request.Request(url, headers={'Referer': 'https://finance.sina.com.cn'})
        data = urllib.request.urlopen(req, timeout=5).read().decode('gbk')
        parts = data.split('"')[1].split(',')
        
        name = parts[0]
        open_p = float(parts[1]) if parts[1] else 0
        pre_close = float(parts[2]) if parts[2] else 0
        price = float(parts[3]) if parts[3] else 0
        high = float(parts[4]) if parts[4] else 0
        low = float(parts[5]) if parts[5] else 0
        volume = float(parts[8]) if parts[8] else 0   # 成交量(股)
        amount = float(parts[9]) if parts[9] else 0    # 成交额(元)
        
        if price <= 0 or open_p <= 0:
            return None
        
        today = int(datetime.now().strftime('%Y%m%d'))
        
        return {
            "date": today,
            "open": open_p,
            "high": max(high, price, open_p),  # 新浪数据有时high=0
            "low": min(low, price, open_p) if low > 0 else min(price, open_p),
            "close": price,
            "amount": amount,
            "volume": int(volume),
            "name": name,
            "pre_close": pre_close,
        }
    except Exception:
        return None


def merge_today(historical: list, code: str) -> list:
    """
    将今日实时K线追加到历史数据末尾(如果TDX还没有今天的数据)
    
    Args:
        historical: TDX历史OHLC列表 [{date, open, high, low, close, amount, volume}]
        code: 如 'sh603137'
    Returns:
        合并后的列表
    """
    if not historical:
        return historical
    
    today = int(datetime.now().strftime('%Y%m%d'))
    last_date = historical[-1].get('date', 0)
    
    # 如果历史数据已有今天的数据, 不重复合并
    if last_date >= today:
        return historical
    
    # 获取今日实时数据
    realtime = get_realtime_bar(code)
    if not realtime:
        return historical
    
    # 只合并今天的
    if realtime['date'] == today:
        return historical + [realtime]
    
    return historical


def is_market_open() -> bool:
    """判断是否在交易时段"""
    now = datetime.now()
    if now.weekday() >= 5:  # 周末
        return False
    # 9:30-11:30, 13:00-15:00
    t = now.hour * 60 + now.minute
    return (570 <= t < 690) or (780 <= t < 900)
