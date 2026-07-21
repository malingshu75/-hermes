# -*- coding: utf-8 -*-
"""AI - 自主进化引擎: 每日自动运行,不需要人管"""
import json, os, time

DATA = r'C:\cb_vwap\_evolution_state.json'

class EvolutionEngine:
    """自我进化: 从每笔交易中学习,持续优化策略"""
    
    def __init__(self):
        self.state = self.load()
    
    def load(self):
        if os.path.exists(DATA):
            with open(DATA) as f: return json.load(f)
        return {
            "generation": 1,
            "total_trades": 0,
            "wins": 0, "losses": 0,
            "total_pnl": 0, "max_dd_pct": 0,
            "rules": {
                "min_volume_yi": 3,        # 最小成交额(亿)
                "min_amplitude": 5,         # 最小振幅%
                "max_position_pct": 2,      # 单票仓位上限%
                "daily_loss_limit": 2,      # 日亏熔断%
                "avoid_streak_days": 3,     # 避免连续涨停天数
                "prefer_sector_leader": True # 偏好板块龙头
            },
            "success_patterns": [],  # 成功的K线形态
            "failure_patterns": [],  # 失败的K线形态
            "daily_log": []
        }
    
    def save(self):
        with open(DATA, 'w') as f: json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def learn_from_trade(self, code, entry_price, exit_price, volume, 
                         amplitude, trend, sector_chg, kline_pattern, result):
        """从每笔交易学习"""
        pnl = (exit_price - entry_price) * volume
        win = pnl > 0
        
        self.state["total_trades"] += 1
        self.state["total_pnl"] += pnl
        if win: self.state["wins"] += 1
        else: self.state["losses"] += 1
        
        # 记录模式
        pattern = {
            "code": code, "pnl": round(pnl,0), "win": win,
            "amplitude": amplitude, "trend": trend,
            "sector_chg": sector_chg, "kline": kline_pattern
        }
        
        if win:
            self.state["success_patterns"].append(pattern)
            # 成功的特征加分
            if amplitude > 10: 
                self.state["rules"]["min_amplitude"] = min(15, self.state["rules"]["min_amplitude"] + 0.5)
        else:
            self.state["failure_patterns"].append(pattern)
            # 失败的特征调整
            if trend < -5:
                self.state["rules"]["min_amplitude"] = max(3, self.state["rules"]["min_amplitude"] - 0.5)
        
        # 只保留最近100条
        if len(self.state["success_patterns"]) > 100:
            self.state["success_patterns"] = self.state["success_patterns"][-100:]
        if len(self.state["failure_patterns"]) > 100:
            self.state["failure_patterns"] = self.state["failure_patterns"][-100:]
        
        self.evolve_rules()
        self.save()
        
        return self.report()
    
    def evolve_rules(self):
        """自动调参"""
        w = self.state["wins"]
        l = self.state["losses"]
        total = w + l
        if total < 5: return  # 样本太少
        
        win_rate = w / total * 100
        
        # 胜率<40%: 收紧规则
        if win_rate < 40:
            self.state["rules"]["min_volume_yi"] = min(10, self.state["rules"]["min_volume_yi"] + 1)
            self.state["rules"]["avoid_streak_days"] = max(1, self.state["rules"]["avoid_streak_days"] - 1)
        
        # 胜率>60%: 放松规则(扩大机会)
        if win_rate > 60 and total > 20:
            self.state["rules"]["min_volume_yi"] = max(1, self.state["rules"]["min_volume_yi"] - 0.5)
            self.state["rules"]["min_amplitude"] = max(3, self.state["rules"]["min_amplitude"] - 0.5)
    
    def should_trade(self, code, amplitude, trend, volume_yi, streak_days, sector_chg):
        """判断是否应该交易"""
        r = self.state["rules"]
        
        # 硬规则
        if volume_yi < r["min_volume_yi"]: return False, "量太小"
        if amplitude < r["min_amplitude"]: return False, "振幅不够"
        if streak_days >= r["avoid_streak_days"]: return False, f"连涨{streak_days}天"
        
        # 软规则: 检查成功模式相似度
        if self.state["success_patterns"]:
            sim = self._similarity(amplitude, trend, sector_chg)
            if sim < 0.3:
                return False, f"与成功模式相似度低({sim:.1f})"
        
        return True, "通过"
    
    def _similarity(self, amp, trend, sector_chg):
        """计算与成功模式的相似度"""
        patterns = self.state["success_patterns"][-20:]
        if not patterns: return 0.5
        matches = 0
        for p in patterns:
            if abs(p["amplitude"] - amp) < 5: matches += 1
            if abs(p["trend"] - trend) < 5: matches += 1
        return matches / (len(patterns) * 2)
    
    def report(self):
        """自我评估报告"""
        w = self.state["wins"]
        l = self.state["losses"]
        total = w + l
        wr = w/total*100 if total > 0 else 0
        return {
            "generation": self.state["generation"],
            "trades": total, "wins": w, "losses": l,
            "win_rate": round(wr, 1),
            "total_pnl": self.state["total_pnl"],
            "rules": self.state["rules"],
            "grade": "A" if wr>60 and total>20 else "B" if wr>50 else "C" if wr>40 else "D"
        }

# 单例
engine = EvolutionEngine()
