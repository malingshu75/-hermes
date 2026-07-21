# -*- coding: utf-8 -*-
"""AI - 统一持仓管理: 可卖→设止盈止损 不可卖→跳过"""
import sys, os, time, json
sys.path.insert(0, r'E:\掘金量化多Agent团队')
from gm.api import *

TOKEN = '927520d80ef8212c5eb366c18fff611bd2090ef2'
ACCT = '2a472909-7763-11f1-95b1-00163e022aa6'
OUT = r'C:\cb_vwap\_ai_cb_result.json'

def init(ctx):
    result = {"time": time.strftime('%H:%M:%S'), "can_sell": [], "locked": []}
    
    # 撤全部旧挂单
    try:
        for o in (get_orders() or []):
            if o.get('order_status',0) in (1,2):
                order_cancel(o.get('cl_ord_id',''), account=ACCT)
    except: pass
    time.sleep(1)
    
    pos = get_position(account_id=ACCT)
    for p in pos:
        sym = p.get('symbol','')
        vol = p.get('volume',0)
        avail = p.get('available_now', 0) if p.get('available_now', 0) is not None else vol
        cost = p.get('vwap',0)
        px = p.get('price',0)
        pnl = (px-cost)/cost*100 if cost>0 else 0
        
        if vol <= 0: continue
        s = sym.replace('SZSE.','').replace('SHSE.','')
        
        # 可转债T+0: 始终可卖; 股票: 检查available_now
        is_cb = any(s.startswith(p) for p in ['123','127','113','128','118','110'])
        can_trade = True if is_cb else (avail > 0)
        
        if not can_trade:
            result["locked"].append(f"{s} x{vol} PnL{pnl:+.1f}% T+1锁定")
            continue
        
        # 可卖: 设动态止盈止损
        if pnl >= 2: tp, sl = round(px*1.001,3), round(cost*1.005,3)
        elif pnl >= 0: tp, sl = round(cost*1.02,3), round(cost*0.99,3)
        else: tp, sl = round(cost*1.02,3), round(cost*0.985,3)
        
        order_volume(sym, avail, side=OrderSide_Sell, order_type=OrderType_Limit,
                    position_effect=PositionEffect_Close, price=tp, account=ACCT)
        order_volume(sym, avail, side=OrderSide_Sell, order_type=OrderType_Limit,
                    position_effect=PositionEffect_Close, price=sl, account=ACCT)
        result["can_sell"].append(f"{s} x{avail} PnL{pnl:+.1f}% TP{tp} SL{sl}")
    
    with open(OUT,'w') as f: json.dump(result,f,ensure_ascii=False,indent=2)
    stop()

if __name__=='__main__':
    run(strategy_id='_mgmt_', filename=os.path.basename(__file__), mode=MODE_LIVE, token=TOKEN)
