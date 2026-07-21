# -*- coding: utf-8 -*-
"""AI - 仓位管理 + 回撤熔断"""
import json, os

CONFIG = r'C:\cb_vwap\_risk_config.json'

class RiskManager:
    """科学仓位+风控"""
    
    def __init__(self, nav=1000000):
        self.nav = nav
        self.daily_pnl = 0
        self.daily_start_nav = nav
        self.circuit_breaker = False
        self.load()
    
    def load(self):
        if os.path.exists(CONFIG):
            with open(CONFIG) as f:
                d = json.load(f)
                self.daily_start_nav = d.get('start_nav', self.nav)
                self.daily_pnl = d.get('pnl', 0)
    
    def save(self):
        with open(CONFIG, 'w') as f:
            json.dump({'start_nav': self.daily_start_nav, 'pnl': self.daily_pnl}, f)
    
    def update(self, nav, pnl):
        self.nav = nav
        self.daily_pnl = pnl
        self.save()
        
        # 日亏>2%: 停止开仓
        dd_pct = abs(pnl) / self.daily_start_nav * 100 if self.daily_start_nav > 0 else 0
        if dd_pct > 2:
            self.circuit_breaker = True
            return "🚨 日亏>2% 熔断!停止开仓"
        # 日亏>3%: 全部清仓
        if dd_pct > 3:
            return "🆘 日亏>3% 紧急!全部清仓"
        return None
    
    def reset_daily(self):
        self.daily_start_nav = self.nav
        self.daily_pnl = 0
        self.circuit_breaker = False
        self.save()
    
    def calc_position(self, price, volatility_pct):
        """凯利公式仓位计算
        price: 股价, volatility_pct: 日振幅%
        单票上限2%总资产
        """
        if self.circuit_breaker:
            return 0
        
        # 基础仓位: 总资产2%
        base = self.nav * 0.02
        
        # 波动率调整: 高波动→减仓
        if volatility_pct > 15: vol_factor = 0.3
        elif volatility_pct > 10: vol_factor = 0.5
        elif volatility_pct > 6: vol_factor = 0.8
        else: vol_factor = 1.0
        
        position_value = base * vol_factor
        
        # 整百取整
        shares = max(100, int(position_value / price / 100) * 100)
        return shares
    
    def can_open(self):
        return not self.circuit_breaker
