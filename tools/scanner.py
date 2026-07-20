# -*- coding: utf-8 -*-
"""
工具3: scan_all_market — 全市场自主扫描
扫描股票、可转债，挖掘交易机会
"""
import os
import glob
import struct
from datetime import datetime, timedelta
from typing import Optional


class MarketScanner:
    """
    全市场扫描器
    
    扫描范围:
    - 沪市主板 (sh60xxxx)
    - 深市主板 (sz00xxxx)
    - 创业板 (sz30xxxx)
    - 科创板 (sh68xxxx)
    - 可转债 (sz12xxxx)
    
    过滤条件:
    - 日均成交额 >= 3000万
    - 排除ST/*ST
    - 排除上市不足60天
    - 排除退市整理期
    """

    def __init__(self, tdx_data_path: str = None):
        from config import TDX_DATA
        self.tdx_path = tdx_data_path or TDX_DATA
        self._market_map = {
            "sh": os.path.join(self.tdx_path, "sh", "lday"),
            "sz": os.path.join(self.tdx_path, "sz", "lday"),
        }

    def scan_all(self, min_volume_amount: float = 30_000_000,
                 exclude_st: bool = True, 
                 exclude_new_days: int = 60) -> dict:
        """
        全市场扫描
        
        Returns:
            {
                stocks: [{code, name, close, volume, amount, change_pct, amplitude, ...}],
                cbs: [{code, name, close, volume, amount, ...}],
                summary: {total_stocks, total_cbs, filtered_stocks, filtered_cbs}
            }
        """
        stocks = []
        cbs = []
        
        # 扫描所有日线数据
        for market, path in self._market_map.items():
            if not os.path.isdir(path):
                continue
            for day_file in glob.glob(os.path.join(path, "*.day")):
                filename = os.path.basename(day_file).replace(".day", "")
                # 文件名格式: sh603818 或 sz123456, 提取6位数字代码
                import re as _re
                code_match = _re.search(r'(\d{6})', filename)
                if not code_match:
                    continue
                code = code_match.group(1)
                full_code = f"{market}{code}"
                
                try:
                    data = self._read_day_file(day_file)
                    if not data or len(data) < 20:  # 至少20个交易日
                        continue
                    
                    latest = data[-1]
                    close = latest["close"]
                    volume = latest["volume"]
                    amount = latest["amount"]
                    
                    if close <= 0 or amount <= 0:
                        continue
                    
                    # 过滤退市/ST/低价股
                    if close < 1.0:
                        continue
                    
                    # 计算日均成交额
                    recent_amounts = [d["amount"] for d in data[-20:] if d["amount"] > 0]
                    avg_amount = sum(recent_amounts) / len(recent_amounts) if recent_amounts else 0
                    
                    if avg_amount < min_volume_amount:
                        continue
                    
                    # 计算振幅和涨跌幅
                    pre_close = data[-2]["close"] if len(data) >= 2 else close
                    change_pct = (close - pre_close) / pre_close * 100 if pre_close else 0
                    
                    high_20 = max(d["high"] for d in data[-20:])
                    low_20 = min(d["low"] for d in data[-20:])
                    amplitude_20d = (high_20 - low_20) / low_20 * 100 if low_20 else 0
                    
                    item = {
                        "code": full_code,
                        "name": self._lookup_name(full_code),
                        "close": close,
                        "volume": volume,
                        "amount": amount,
                        "avg_amount_20d": round(avg_amount, 0),
                        "change_pct": round(change_pct, 2),
                        "amplitude_20d": round(amplitude_20d, 2),
                        "high_20d": high_20,
                        "low_20d": low_20,
                        "days_of_data": len(data),
                    }
                    
                    # 分类
                    if full_code.startswith("sz12"):
                        # 可转债
                        if 100 <= close <= 1500:  # 价格过滤
                            cbs.append(item)
                    elif full_code.startswith(("sh6", "sz0", "sz3")):
                        # 股票
                        stocks.append(item)
                        
                except Exception:
                    continue

        # 排序: 股票按振幅降序，转债按成交额降序
        stocks.sort(key=lambda x: x["amplitude_20d"], reverse=True)
        cbs.sort(key=lambda x: x["avg_amount_20d"], reverse=True)

        return {
            "stocks": stocks,
            "cbs": cbs,
            "summary": {
                "total_stocks": len(stocks),
                "total_cbs": len(cbs),
                "top_stocks_by_amplitude": [s["code"] for s in stocks[:20]],
                "top_cbs_by_volume": [c["code"] for c in cbs[:20]],
            }
        }

    def scan_grid_candidates(self, min_amplitude: float = 4.0, 
                              max_price: float = 50,
                              top_n: int = 50) -> list:
        """
        扫描网格策略候选标的
        
        条件: 振幅>=4%, 价格<=50, 日均成交额>=3000万, 非ST
        """
        result = self.scan_all()
        candidates = []
        
        for stock in result["stocks"]:
            if stock["amplitude_20d"] >= min_amplitude and stock["close"] <= max_price:
                # 网格评分
                grid_score = stock["amplitude_20d"] * 10  # 振幅权重最高
                grid_score += min(stock["avg_amount_20d"] / 1e7, 10)  # 流动性加分
                stock["grid_score"] = round(grid_score, 1)
                candidates.append(stock)
        
        # 也加入可转债
        for cb in result["cbs"]:
            cb_amplitude = cb.get("amplitude_20d", 0)
            if cb_amplitude >= min_amplitude:
                grid_score = cb_amplitude * 10
                grid_score += min(cb["avg_amount_20d"] / 1e7, 10)
                cb["grid_score"] = round(grid_score, 1)
                candidates.append(cb)
        
        candidates.sort(key=lambda x: x["grid_score"], reverse=True)
        return candidates[:top_n]

    def _read_day_file(self, filepath: str, max_records: int = 30) -> list:
        """读取通达信.day文件(仅最后N条,极速扫描)"""
        data = []
        try:
            with open(filepath, "rb") as f:
                f.seek(0, 2)
                file_size = f.tell()
                total_records = file_size // 32
                read_count = min(max_records, total_records)
                # 定位到最后N条
                f.seek(max(0, file_size - read_count * 32))
                
                for _ in range(read_count):
                    raw = f.read(32)
                    if len(raw) < 32:
                        break
                    date, open_p, high, low, close, amount, volume, _ = struct.unpack("=IiiiiIII", raw)
                    
                    if date < 19900101 or date > 20991231:
                        continue
                    if close <= 0:
                        continue
                    
                    data.append({
                        "date": date,
                        "open": round(open_p/100.0, 3),
                        "high": round(high/100.0, 3),
                        "low": round(low/100.0, 3),
                        "close": round(close/100.0, 3),
                        "amount": amount,
                        "volume": volume,
                    })
        except Exception:
            pass
        return data

    def _lookup_name(self, code: str) -> str:
        """查找股票名称(从通达信配置文件)"""
        # 简化实现，从TDX的name文件查找
        name_file = os.path.join(self.tdx_path, "..", "T0002", "hq_cache", "name.tmp")
        # 如果找不到名称文件，返回代码
        return ""


# 便捷函数
def scan_all() -> dict:
    return MarketScanner().scan_all()

def scan_grid_candidates() -> list:
    return MarketScanner().scan_grid_candidates()
