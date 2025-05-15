# coding :utf-8
#
# The MIT License (MIT)
#
# Copyright (c) 2016-2019 XuHaiJiang/QFF
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import json
import time
import os

from qff.frame.backtestEngine import BacktestEngine
from qff.frame.live_trade_engine import LiveTradeEngine
from qff.tools.config import get_config
from qff.store.update_all import update_all
from qff.store.init_all import init_tdx_dir, init_db, init_stock_list, init_index_list, init_etf_list, init_block_list

# 导入标准数据存储模块
from qff.store.save_info import save_stock_list, init_index_list, init_etf_list
from qff.store.save_price import save_security_day, save_security_min
from qff.store.save_report import save_report
from qff.store.save_valuation import save_valuation_data
from qff.store.save_mtss import save_mtss_data
from qff.store.save_block import save_security_block

# 导入新的保存模块
from qff.store.save_hot_info import save_limit_up, save_limit_down, save_block_trade, save_margin_detail
from qff.store.save_block_info import (save_concept_list, save_concept_stocks, save_concept_daily,
                                     save_industry_list, save_industry_stocks, save_industry_daily)
from qff.store.save_special_info import (save_top_list, save_top_inst, save_restricted_release,
                                        save_moneyflow_hsgt, save_moneyflow_stock, save_moneyflow_sector)


def cli():
    # 主命令解析
    parser = argparse.ArgumentParser(
        description='quantitative finance framework',
        epilog='Any questions please contact: xuhaijiangsz@gmail.com',
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # 添加模块子命令解析器
    subparsers = parser.add_subparsers(
        title='commands',
        dest='COMMAND',
        help='additional help',
        metavar='')

    # 添加回测 'backtest' 子命令
    parser_bt = subparsers.add_parser('backtest', aliases=['bt'], help='回测策略')
    parser_bt.add_argument('file', help='回测策略文件')
    parser_bt.add_argument('-p', '--plot', action='store_true', help='显示图形分析')
    parser_bt.add_argument('-c', '--conf', action='store_true', help='使用配置回测参数')
    parser_bt.add_argument('-m', '--multi', action='store_true', help='多次回测取平均表现')
    parser_bt.add_argument('-d', '--dump', type=str, help='dump回测日志')

    # 添加 '实盘交易' 子命令
    parser_bt = subparsers.add_parser('livetrade', aliases=['live'], help='实盘交易策略')
    parser_bt.add_argument('file', help='交易策略文件')
    parser_bt.add_argument('-t', '--trans', action='store_true', help='使用模拟交易')

    # 添加 '初始化' 子命令
    parser_init = subparsers.add_parser('init', help='初始化')
    parser_init.add_argument('--tdx_dir', help='设置通达信目录')
    parser_init.add_argument('--db', help='设置数据库名称')
    parser_init.add_argument('--stock_list', action='store_true', help='初始化股票列表')
    parser_init.add_argument('--index_list', action='store_true', help='初始化指数列表')
    parser_init.add_argument('--etf_list', action='store_true', help='初始化ETF列表')
    parser_init.add_argument('--block_list', action='store_true', help='初始化板块列表')
    parser_init.add_argument('--all', action='store_true', help='初始化全部')

    # 添加 '更新数据' 子命令
    parser_save = subparsers.add_parser('save', help='更新数据')
    parser_save.add_argument('--security', choices=['stock', 'index', 'etf'], help='证券类型')
    parser_save.add_argument('--stock_day', action='store_true', help='更新股票日线数据')
    parser_save.add_argument('--stock_min', action='store_true', help='更新股票分钟线数据')
    parser_save.add_argument('--stock_list', action='store_true', help='更新股票列表')
    parser_save.add_argument('--stock_block', action='store_true', help='更新股票板块数据')
    parser_save.add_argument('--index_day', action='store_true', help='更新指数日线数据')
    parser_save.add_argument('--index_min', action='store_true', help='更新指数分钟线数据')
    parser_save.add_argument('--etf_day', action='store_true', help='更新ETF日线数据')
    parser_save.add_argument('--etf_min', action='store_true', help='更新ETF分钟线数据')
    parser_save.add_argument('--report', action='store_true', help='更新财务数据')
    parser_save.add_argument('--valuation', action='store_true', help='更新估值数据')
    parser_save.add_argument('--mtss', action='store_true', help='更新融资融券数据')
    
    # 添加新的命令选项
    parser_save.add_argument('--limit_up', action='store_true', help='更新涨停信息')
    parser_save.add_argument('--limit_down', action='store_true', help='更新跌停信息')
    parser_save.add_argument('--block_trade', action='store_true', help='更新大宗交易数据')
    parser_save.add_argument('--margin_detail', action='store_true', help='更新融资融券明细数据')
    
    parser_save.add_argument('--concept_list', action='store_true', help='更新概念板块列表')
    parser_save.add_argument('--concept_stocks', action='store_true', help='更新概念板块成分股')
    parser_save.add_argument('--concept_daily', action='store_true', help='更新概念板块日线数据')
    parser_save.add_argument('--industry_list', action='store_true', help='更新行业板块列表')
    parser_save.add_argument('--industry_stocks', action='store_true', help='更新行业板块成分股')
    parser_save.add_argument('--industry_daily', action='store_true', help='更新行业板块日线数据')
    
    parser_save.add_argument('--top_list', action='store_true', help='更新龙虎榜数据')
    parser_save.add_argument('--top_inst', action='store_true', help='更新龙虎榜机构数据')
    parser_save.add_argument('--restricted_release', action='store_true', help='更新解禁股数据')
    parser_save.add_argument('--moneyflow_hsgt', action='store_true', help='更新沪深港通资金流向数据')
    parser_save.add_argument('--moneyflow_stock', action='store_true', help='更新个股资金流向数据')
    parser_save.add_argument('--moneyflow_sector', action='store_true', help='更新板块资金流向数据')
    
    parser_save.add_argument('--hot_info', action='store_true', help='更新所有短线数据')
    parser_save.add_argument('--block_info', action='store_true', help='更新所有板块数据')
    parser_save.add_argument('--special_info', action='store_true', help='更新所有特别信息数据')
    
    parser_save.add_argument('--all', action='store_true', help='更新全部数据')
    parser_save.add_argument('--date', help='指定更新的日期')

    # 添加 'run' 子命令
    parser_run = subparsers.add_parser('run', help='运行策略')
    parser_run.add_argument('file', help='策略文件')

    args = parser.parse_args()

    if args.COMMAND == 'backtest' or args.COMMAND == 'bt':
        qff_bt(args)
    elif args.COMMAND == 'livetrade' or args.COMMAND == 'live':
        qff_live_trade(args)
    elif args.COMMAND == 'init':
        qff_init(args)
    elif args.COMMAND == 'save':
        qff_save(args)
    elif args.COMMAND == 'run':
        qff_run(args)
    else:
        print("QFF: Quantitative investment framework")
        print("========================================")
        print("")
        print("Commands:")
        print("  - init - Initialize database and data")
        print("  - save - Save data to database")
        print("  - backtest - Backtest strategy")
        print("  - livetrade - Run strategy in live market")
        print("  - run - Run strategy file")
        print("")
        print("For more information, run 'qff <command> -h'")


def qff_bt(args):
    engine = BacktestEngine()
    results = engine.run_bt_strategy(args.file, args.plot, args.conf, args.multi)
    if args.dump:
        with open(args.dump, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)


def qff_live_trade(args):
    engine = LiveTradeEngine()
    engine.run_trade_strategy(args.file, args.trans)


def qff_init(args):
    if args.tdx_dir:
        init_tdx_dir(args.tdx_dir)
    if args.db:
        init_db(args.db)
    if args.stock_list or args.all:
        init_stock_list()
    if args.index_list or args.all:
        init_index_list()
    if args.etf_list or args.all:
        init_etf_list()
    if args.block_list or args.all:
        init_block_list()


def qff_save(args):
    if args.all:
        update_all(args.date)
        return

    # 更新股票信息
    if args.stock_list:
        try:
            save_stock_list()
        except Exception as e:
            print(f"updating stock list data error: {e}")

    # 更新行情数据
    if args.security == 'stock' or args.stock_day:
        try:
            save_security_day(market='stock')
        except Exception as e:
            print(f"updating stock day data error: {e}")

    if args.security == 'index' or args.index_day:
        try:
            save_security_day(market='index')
        except Exception as e:
            print(f"updating index day data error: {e}")

    if args.security == 'etf' or args.etf_day:
        try:
            save_security_day(market='etf')
        except Exception as e:
            print(f"updating etf day data error: {e}")

    if args.security == 'stock' or args.stock_min:
        try:
            for freq in ["1min", "5min", "15min", "30min", "60min"]:
                save_security_min(market='stock', freq=freq)
        except Exception as e:
            print(f"updating stock min data error: {e}")

    if args.security == 'index' or args.index_min:
        try:
            for freq in ["1min", "5min", "15min", "30min", "60min"]:
                save_security_min(market='index', freq=freq)
        except Exception as e:
            print(f"updating index min data error: {e}")

    if args.security == 'etf' or args.etf_min:
        try:
            for freq in ["1min", "5min", "15min", "30min", "60min"]:
                save_security_min(market='etf', freq=freq)
        except Exception as e:
            print(f"updating etf min data error: {e}")

    # 更新财务数据
    if args.report:
        try:
            save_report()
        except Exception as e:
            print(f"updating report data error: {e}")

    # 更新估值数据
    if args.valuation:
        try:
            save_valuation_data()
        except Exception as e:
            print(f"updating valuation data error: {e}")

    # 更新融资融券数据
    if args.mtss:
        try:
            save_mtss_data()
        except Exception as e:
            print(f"updating mtss data error: {e}")

    # 更新板块信息
    if args.stock_block:
        try:
            save_security_block()
        except Exception as e:
            print(f"updating stock block data error: {e}")

    # 处理短线数据
    if args.limit_up or args.hot_info:
        try:
            save_limit_up()
        except Exception as e:
            print(f"updating limit up data error: {e}")
    
    if args.limit_down or args.hot_info:
        try:
            save_limit_down()
        except Exception as e:
            print(f"updating limit down data error: {e}")
            
    if args.block_trade or args.hot_info:
        try:
            save_block_trade()
        except Exception as e:
            print(f"updating block trade data error: {e}")
            
    if args.margin_detail or args.hot_info:
        try:
            save_margin_detail()
        except Exception as e:
            print(f"updating margin detail data error: {e}")
    
    # 处理板块数据
    if args.concept_list or args.block_info:
        try:
            concept_codes = save_concept_list()
            if args.concept_stocks or args.block_info:
                save_concept_stocks()
            if args.concept_daily or args.block_info:
                save_concept_daily()
        except Exception as e:
            print(f"updating concept data error: {e}")
            
    elif args.concept_stocks:
        try:
            save_concept_stocks()
        except Exception as e:
            print(f"updating concept stocks data error: {e}")
            
    elif args.concept_daily:
        try:
            save_concept_daily()
        except Exception as e:
            print(f"updating concept daily data error: {e}")
            
    if args.industry_list or args.block_info:
        try:
            industry_codes = save_industry_list()
            if args.industry_stocks or args.block_info:
                save_industry_stocks()
            if args.industry_daily or args.block_info:
                save_industry_daily()
        except Exception as e:
            print(f"updating industry data error: {e}")
            
    elif args.industry_stocks:
        try:
            save_industry_stocks()
        except Exception as e:
            print(f"updating industry stocks data error: {e}")
            
    elif args.industry_daily:
        try:
            save_industry_daily()
        except Exception as e:
            print(f"updating industry daily data error: {e}")
    
    # 处理特别信息数据
    if args.top_list or args.special_info:
        try:
            save_top_list()
        except Exception as e:
            print(f"updating top list data error: {e}")
            
    if args.top_inst or args.special_info:
        try:
            save_top_inst()
        except Exception as e:
            print(f"updating top inst data error: {e}")
            
    if args.restricted_release or args.special_info:
        try:
            save_restricted_release()
        except Exception as e:
            print(f"updating restricted release data error: {e}")
            
    if args.moneyflow_hsgt or args.special_info:
        try:
            save_moneyflow_hsgt()
        except Exception as e:
            print(f"updating moneyflow hsgt data error: {e}")
            
    if args.moneyflow_stock or args.special_info:
        try:
            save_moneyflow_stock()
        except Exception as e:
            print(f"updating moneyflow stock data error: {e}")
            
    if args.moneyflow_sector or args.special_info:
        try:
            save_moneyflow_sector()
        except Exception as e:
            print(f"updating moneyflow sector data error: {e}")


def qff_run(args):
    path = os.path.abspath(args.file)
    strategy_folder = os.path.dirname(path)
    strategy_file = os.path.basename(path)
    if os.path.isfile(path) and strategy_file.endswith('.py'):
        if strategy_folder not in os.sys.path:
            os.sys.path.insert(0, strategy_folder)

        import importlib.util
        spec = importlib.util.spec_from_file_location("strategy", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        print(f"Error: {args.file} - is not a valid Python file.")


if __name__ == '__main__':
    cli() 