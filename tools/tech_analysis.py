# -*- coding: utf-8 -*-
"""AI - 技术指标补全: MACD/RSI/布林/支撑阻力/K线形态/PE/PB"""
import urllib.request, struct, os, re
from datetime import datetime


class TechAnalyzer:
    """完整技术分析"""
    
    @staticmethod
    def macd(closes, fast=12, slow=26, signal=9):
        """MACD: 返回(dif, dea, bar)序列"""
        if len(closes) < slow + signal: return [],[],[]
        ema_fast = TechAnalyzer._ema(closes, fast)
        ema_slow = TechAnalyzer._ema(closes, slow)
        dif = [ema_fast[i]-ema_slow[i] for i in range(len(ema_fast))]
        dea = TechAnalyzer._ema(dif, signal)
        bar = [2*(dif[i]-dea[i]) for i in range(min(len(dif),len(dea)))]
        return dif, dea, bar

    @staticmethod
    def rsi(closes, period=14):
        """RSI"""
        if len(closes) < period+1: return []
        gains, losses = [], []
        for i in range(1, len(closes)):
            d = closes[i]-closes[i-1]
            gains.append(max(d,0))
            losses.append(max(-d,0))
        avg_gain = sum(gains[-period:])/period
        avg_loss = sum(losses[-period:])/period
        if avg_loss==0: return [100]
        return [100-(100/(1+avg_gain/avg_loss))]

    @staticmethod
    def bollinger(closes, period=20, std=2):
        """布林带: (upper, middle, lower)"""
        if len(closes) < period: return 0,0,0
        ma = sum(closes[-period:])/period
        variance = sum((c-ma)**2 for c in closes[-period:])/period
        sigma = variance**0.5
        return round(ma+std*sigma,3), round(ma,3), round(ma-std*sigma,3)

    @staticmethod
    def support_resistance(highs, lows, closes, levels=5):
        """支撑阻力位: 基于最近60天高低点+成交量密集区"""
        n = len(closes)
        if n < 20: return [],[]
        
        h60 = sorted(highs[-60:], reverse=True)
        l60 = sorted(lows[-60:])
        
        resistances = []
        supports = []
        
        # 前N个高点是阻力
        for i in range(min(levels, len(h60))):
            if i==0 or h60[i] < h60[i-1]*0.995:
                resistances.append(round(h60[i],2))
        
        # 前N个低点是支撑
        for i in range(min(levels, len(l60))):
            if i==0 or l60[i] > l60[i-1]*1.005:
                supports.append(round(l60[i],2))
        
        # 最近收盘价附近的整数关口
        price = closes[-1]
        for level in range(int(price)-5, int(price)+6):
            if abs(level-price)/price < 0.05 and level%5==0:
                if level > price: resistances.append(float(level))
                else: supports.append(float(level))
        
        return sorted(set(supports), reverse=True), sorted(set(resistances))

    @staticmethod
    def kline_pattern(open_p, high, low, close, prev_open=None, prev_close=None):
        """K线形态识别"""
        body = abs(close-open_p)
        upper = high-max(open_p,close)
        lower = min(open_p,close)-low
        total = max(high-low, 0.001)
        
        patterns = []
        
        # Doji(十字星): 实体<10%总长度
        if body/total < 0.1:
            patterns.append('十字星')
        
        # Hammer(锤子): 下影线>2倍实体, 上影线<实体
        if lower > body*2 and upper < body:
            if close > open_p: patterns.append('锤子线(看涨)')
            else: patterns.append('上吊线(看跌)')
        
        # Shooting star(射击之星): 上影线>2倍实体
        if upper > body*2 and lower < body:
            patterns.append('射击之星(看跌)')
        
        # Engulfing(吞没): 需要前一根K线
        if prev_open and prev_close:
            prev_body = abs(prev_close-prev_open)
            if body > prev_body*1.5:
                if close > open_p and prev_close < prev_open:
                    patterns.append('看涨吞没')
                elif close < open_p and prev_close > prev_open:
                    patterns.append('看跌吞没')
        
        # Marubozu(光头光脚): 实体>90%总长度
        if body/total > 0.9:
            if close > open_p: patterns.append('光头光脚阳线')
            else: patterns.append('光头光脚阴线')
        
        # 连续形态
        gap_up = prev_close and open_p > prev_close*1.01
        gap_down = prev_close and open_p < prev_close*0.99
        if gap_up: patterns.append('跳空高开')
        if gap_down: patterns.append('跳空低开')
        
        return patterns

    @staticmethod
    def volume_profile(closes, volumes, price_step=0.02):
        """成交量分布: 在哪些价位成交最多"""
        if not closes or not volumes: return {}
        profile = {}
        for c, v in zip(closes[-60:], volumes[-60:]):
            key = round(c/price_step)*price_step
            profile[key] = profile.get(key,0)+v
        # 返回top价位
        sorted_p = sorted(profile.items(), key=lambda x:-x[1])
        return {round(k,2):v for k,v in sorted_p[:5]}

    @staticmethod
    def get_fundamentals(code):
        """基本面数据: PE/PB/换手率/总市值"""
        num = code.replace('sh','').replace('sz','').replace('SHSE.','').replace('SZSE.','')
        if code.startswith('sh') or num.startswith('6'): sina=f'sh{num}'
        else: sina=f'sz{num}'
        
        try:
            url = f'http://hq.sinajs.cn/list={sina}'
            req = urllib.request.Request(url, headers={'Referer':'https://finance.sina.com.cn'})
            data = urllib.request.urlopen(req, timeout=3).read().decode('gbk')
            parts = data.split('"')[1].split(',')
            
            return {
                'name': parts[0],
                'price': float(parts[3]) if parts[3] else 0,
                'open': float(parts[1]) if parts[1] else 0,
                'high': float(parts[4]) if parts[4] else 0,
                'low': float(parts[5]) if parts[5] else 0,
                'pre_close': float(parts[2]) if parts[2] else 0,
                'volume': float(parts[8]) if parts[8] else 0,
                'amount': float(parts[9]) if parts[9] else 0,
                # 新浪不直接给PE/PB,需要另外的API
            }
        except: return None

    @staticmethod
    def get_pe_pb(code):
        """东方财富PE/PB数据"""
        num = code.replace('sh','').replace('sz','').replace('SHSE.','').replace('SZSE.','')
        if num.startswith('6'): market='1'
        else: market='0'
        secid = f'{market}.{num}'
        
        try:
            url = f'https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f9,f20,f21,f23,f24,f43,f45,f46,f115,f116,f117,f162,f167'
            req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0','Referer':'https://quote.eastmoney.com/'})
            data = urllib.request.urlopen(req, timeout=3).read().decode()
            import json
            d = json.loads(data).get('data',{})
            return {
                'pe': d.get('f9',0),           # PE(TTM)
                'pb': d.get('f23',0),          # PB
                'total_mv': d.get('f20',0)/1e8, # 总市值(亿)
                'circulating_mv': d.get('f21',0)/1e8, # 流通市值(亿)
                'turnover_rate': d.get('f168',0), # 换手率%
            }
        except: return None

    # ── 内部工具 ──

    @staticmethod
    def _ema(data, period):
        result = [data[0]]
        m = 2/(period+1)
        for v in data[1:]:
            result.append((v-result[-1])*m+result[-1])
        return result


# 便捷函数
def full_analysis(code, ohlc_data, volumes=None):
    """一站式分析: 返回完整技术评估"""
    ta = TechAnalyzer()
    closes = [b['close'] for b in ohlc_data]
    highs = [b['high'] for b in ohlc_data]
    lows = [b['low'] for b in ohlc_data]
    opens = [b['open'] for b in ohlc_data]
    
    # MACD
    dif, dea, bar = ta.macd(closes)
    macd_signal = '金叉看涨' if dif and dea and dif[-1]>dea[-1] and dif[-2]<=dea[-2] else \
                  '死叉看跌' if dif and dea and dif[-1]<dea[-1] and dif[-2]>=dea[-2] else \
                  '多头' if dif and dea and dif[-1]>dea[-1] else '空头'
    
    # RSI
    rsi_val = ta.rsi(closes)
    rsi_status = '超买' if rsi_val and rsi_val[-1]>70 else '超卖' if rsi_val and rsi_val[-1]<30 else '中性'
    
    # 布林带
    bb_upper, bb_mid, bb_lower = ta.bollinger(closes)
    bb_pos = (closes[-1]-bb_lower)/(bb_upper-bb_lower)*100 if bb_upper!=bb_lower else 50
    
    # 支撑阻力
    supports, resistances = ta.support_resistance(highs, lows, closes)
    
    # K线形态
    prev_o = opens[-2] if len(opens)>=2 else None
    prev_c = closes[-2] if len(closes)>=2 else None
    patterns = ta.kline_pattern(opens[-1], highs[-1], lows[-1], closes[-1], prev_o, prev_c)
    
    # 量价关系
    vol_increase = volumes and len(volumes)>=6 and sum(volumes[-3:])>sum(volumes[-6:-3])*1.3
    
    return {
        'macd': {'signal': macd_signal, 'dif': round(dif[-1],4) if dif else 0, 'dea': round(dea[-1],4) if dea else 0},
        'rsi': {'value': round(rsi_val[-1],1) if rsi_val else 0, 'status': rsi_status},
        'bollinger': {'upper': bb_upper, 'mid': bb_mid, 'lower': bb_lower, 'position_pct': round(bb_pos,1)},
        'support_resistance': {'supports': supports[:3], 'resistances': resistances[:3]},
        'kline_patterns': patterns,
        'volume': {'increasing': vol_increase},
        'composite_signal': _composite(macd_signal, rsi_status, bb_pos, patterns)
    }

def _composite(macd, rsi, bb_pos, patterns):
    """综合评分: -10到+10"""
    score = 0
    if '金叉' in macd: score += 3
    elif '多头' in macd: score += 1
    elif '死叉' in macd: score -= 3
    
    if '超卖' in rsi: score += 2
    elif '超买' in rsi: score -= 2
    
    if bb_pos < 20: score += 2  # 布林下轨
    elif bb_pos > 80: score -= 2  # 布林上轨
    
    for p in patterns:
        if '看涨' in p: score += 1
        elif '看跌' in p: score -= 1
    
    if score >= 4: return '强烈看多'
    elif score >= 2: return '看多'
    elif score >= -1: return '中性'
    elif score >= -3: return '看空'
    else: return '强烈看空'
