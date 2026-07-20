# -*- coding: utf-8 -*-
"""
AI炒股机器人 — 主入口

用法:
  python main.py                    # learn模式: 学习+回测
  python main.py --mode paper       # 学习+模拟交易
  python main.py --mode live        # 学习+实盘交易(⚠谨慎)
  python main.py --status           # 查看当前状态
  python main.py --report           # 查看成长报告
  python main.py --scan             # 只看全市场扫描
  python main.py --diagnose 603818  # 诊断个股
  python main.py --backtest 603818  # 回测个股网格策略
"""
import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain import AIStockBrain


def cmd_daily(brain, args):
    """每日自主学习循环"""
    mode = args.mode or "learn"
    brain.run_daily(mode=mode)


def cmd_status(brain, args):
    """查看状态"""
    print(json.dumps(brain.status(), ensure_ascii=False, indent=2))


def cmd_report(brain, args):
    """查看报告"""
    print(brain.report())


def cmd_scan(brain, args):
    """全市场扫描"""
    print("正在扫描全市场网格候选...")
    result = brain.scanner.scan_grid_candidates(top_n=20)
    print(f"\n找到 {len(result)} 个候选标的:\n")
    for i, c in enumerate(result[:10]):
        print(f"  {i+1}. {c['code']:12s} | 价格{c['close']:7.2f} | "
              f"振幅{c.get('amplitude_20d', 0):5.1f}% | "
              f"评分{c.get('grid_score', 0):5.0f} | "
              f"日均成交{c.get('avg_amount_20d', 0)/1e6:.0f}万")


def cmd_diagnose(brain, args):
    """诊断个股"""
    code = args.diagnose
    print(f"正在诊断 {code} ...")
    result = brain.indicators.diagnose(code)
    if "error" in result:
        print(f"错误: {result['error']}")
        return
    print(f"\n诊断结果:")
    print(f"  振幅: {result.get('amplitude', 0):.2f}%")
    print(f"  自相关: {result.get('autocorrelation', 0):.3f}")
    print(f"  方向: {result.get('direction', 'unknown')}")
    print(f"  网格评分: {result.get('grid_score', 0):.0f}")
    print(f"  推荐策略: {result.get('recommended_strategy', 'unknown')}")
    if result.get('grid_params'):
        gp = result['grid_params']
        print(f"  网格参数: 间隔{gp.get('interval_pct', 0):.2f}% | "
              f"单位{gp.get('unit', 0)}股 | 层数{gp.get('layers', 0)}")
        print(f"  马丁倍率: {gp.get('martin', [])}")


def cmd_backtest(brain, args):
    """回测个股"""
    code = args.backtest
    print(f"正在诊断+回测 {code} ...")
    diagnosis = brain.indicators.diagnose(code)
    if "error" in diagnosis:
        print(f"诊断失败: {diagnosis['error']}")
        return
    
    params = diagnosis.get("grid_params", {})
    if not params:
        print("无法生成网格参数")
        return
    
    print(f"网格参数: {json.dumps(params, ensure_ascii=False)}")
    result = brain.backtester.backtest_grid(code, params, days=250)
    
    if "error" in result:
        print(f"回测失败: {result['error']}")
        return
    
    print(f"\n回测结果:")
    print(f"  总收益: {result.get('total_return_pct', 0):+.2f}%")
    print(f"  年化收益: {result.get('annual_return_pct', 0):+.2f}%")
    print(f"  胜率: {result.get('win_rate_pct', 0):.1f}%")
    print(f"  最大回撤: {result.get('max_drawdown_pct', 0):.2f}%")
    print(f"  交易笔数: {result.get('total_trades', 0)}")
    print(f"  夏普比率: {result.get('sharpe_ratio', 0):.2f}")
    print(f"  判定: {'✅ 通过' if result.get('verdict') == 'pass' else '❌ 不通过'}")


def cmd_test(brain, args):
    """快速测试: 跑一个简化流程"""
    print("=== 快速测试 ===\n")
    
    # 1. 搜索
    print("[1/4] 搜索知识...")
    w = brain.web_search
    results = w.search("A股网格交易策略 最佳参数", category="交易策略")
    print(f"  找到{results['total_found']}条结果")
    
    # 2. 过滤
    print("[2/4] 过滤信息...")
    items = results.get("results", [])
    if items:
        f = brain.info_filter
        filtered = f.filter_batch(items)
        gems = f.get_gems(filtered)
        trash = f.get_trash(filtered)
        print(f"  精华{gems and len(gems)}条 | 糟粕{trash and len(trash)}条")
    
    # 3. 扫描+诊断一只股票
    print("[3/4] 扫描一只高振幅股票...")
    candidates = brain.scanner.scan_grid_candidates(top_n=3)
    if candidates:
        best = candidates[0]
        print(f"  最佳候选: {best['code']} 振幅{best.get('amplitude_20d', 0):.1f}%")
        
        print("[4/4] 诊断+回测...")
        diag = brain.indicators.diagnose(best['code'])
        if "error" not in diag:
            params = diag.get("grid_params")
            if params is None:
                # 即使诊断推荐趋势，也强制生成网格参数来回测
                from tools.indicators import IndicatorEngine
                amp = diag.get("amplitude", 4.0)
                price = best.get("close", 10)
                params = {
                    "interval_pct": round(max(0.75, amp / 6), 2),
                    "unit": max(100, int(50000 / max(price, 1) / 100) * 100),
                    "layers": 5,
                    "martin": [1, 1, 2, 3, 5],
                    "base_price": price,
                }
            bt = brain.backtester.backtest_grid(best['code'], params, days=250)
            if "error" not in bt:
                print(f"  回测: 收益{bt.get('total_return_pct', 0):+.1f}% | "
                      f"胜率{bt.get('win_rate_pct', 0):.0f}% | "
                      f"判定={bt.get('verdict', '?')}")
            else:
                print(f"  回测失败: {bt.get('error')}")
    else:
        print("  未找到候选(可能TDX数据路径不对)")
    
    # 状态
    print(f"\n知识库: {brain.kb.stats()}")
    print(f"进化: {brain.evo.status()}")
    print("\n=== 快速测试完成 ===")


def main():
    parser = argparse.ArgumentParser(
        description="AI炒股机器人 — 从零自学成长的量化交易AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                    每日学习循环(learn模式)
  python main.py --mode paper       学习+模拟交易
  python main.py --status           查看当前状态
  python main.py --scan             全市场扫描
  python main.py --diagnose 603818  诊断曲美家居
  python main.py --backtest 123211  回测可转债网格
  python main.py --test             快速测试
        """
    )
    parser.add_argument("--mode", choices=["learn", "paper", "live"],
                       default="learn", help="运行模式")
    parser.add_argument("--status", action="store_true", help="显示状态")
    parser.add_argument("--report", action="store_true", help="显示报告")
    parser.add_argument("--scan", action="store_true", help="全市场扫描")
    parser.add_argument("--diagnose", type=str, metavar="CODE", help="诊断个股")
    parser.add_argument("--backtest", type=str, metavar="CODE", help="回测个股")
    parser.add_argument("--test", action="store_true", help="快速测试")
    
    args = parser.parse_args()
    
    brain = AIStockBrain()
    
    commands = {
        "status": cmd_status,
        "report": cmd_report,
        "scan": cmd_scan,
        "diagnose": cmd_diagnose,
        "backtest": cmd_backtest,
        "test": cmd_test,
    }
    
    # 判断执行哪个命令
    executed = False
    for flag, cmd in commands.items():
        if getattr(args, flag, False):
            cmd(brain, args)
            executed = True
            break
    
    if not executed:
        # 默认: 每日学习
        cmd_daily(brain, args)


if __name__ == "__main__":
    main()
