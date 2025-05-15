#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试热点信息、板块信息和特殊信息三个模块的数据获取功能
"""

import sys
import argparse
import datetime
from qff.tools.date import get_real_trade_date

# 打印一些基本信息
print("===== 调试信息 =====")
print(f"Python 版本: {sys.version}")
print(f"当前时间: {datetime.datetime.now()}")
print("===== 调试信息结束 =====\n")

# 导入热点信息模块
from qff.price.hot_info import (
    fetch_limit_up, fetch_limit_down, 
    fetch_block_trade, fetch_margin_detail
)

# 导入板块信息模块
from qff.price.block_info import (
    fetch_concept_list, fetch_concept_stocks, fetch_concept_daily,
    fetch_industry_list, fetch_industry_stocks, fetch_industry_daily
)

# 导入特殊信息模块
from qff.price.special_info import (
    fetch_top_list, fetch_top_inst, fetch_restricted_release,
    fetch_moneyflow_hsgt, fetch_moneyflow_stock, fetch_moneyflow_sector
)

def test_hot_info(date=None):
    """测试热点信息模块"""
    if date is None:
        date = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
    
    print(f"===== 测试热点信息模块 - 日期：{date} =====")
    
    # 测试涨停信息
    print("\n1. 正在获取涨停信息...")
    df = fetch_limit_up(date=date)
    if df is not None and len(df) > 0:
        print(f"成功获取涨停信息，共 {len(df)} 条记录")
        print(df.head(3))
    else:
        print(f"未获取到涨停信息")
    
    # 测试跌停信息
    print("\n2. 正在获取跌停信息...")
    df = fetch_limit_down(date=date)
    if df is not None and len(df) > 0:
        print(f"成功获取跌停信息，共 {len(df)} 条记录")
        print(df.head(3))
    else:
        print(f"未获取到跌停信息")
    
    # 测试大宗交易
    print("\n3. 正在获取大宗交易信息...")
    df = fetch_block_trade(date=date)
    if df is not None and len(df) > 0:
        print(f"成功获取大宗交易信息，共 {len(df)} 条记录")
        print(df.head(3))
    else:
        print(f"未获取到大宗交易信息")
    
    # 测试融资融券
    print("\n4. 正在获取融资融券信息...")
    df = fetch_margin_detail(date=date)
    if df is not None and len(df) > 0:
        print(f"成功获取融资融券信息，共 {len(df)} 条记录")
        print(df.head(3))
    else:
        print(f"未获取到融资融券信息")


def test_block_info():
    """测试板块信息模块"""
    print("\n===== 测试板块信息模块 =====")
    
    # 测试概念板块列表
    print("\n1. 正在获取概念板块列表...")
    df = fetch_concept_list()
    if df is not None and len(df) > 0:
        print(f"成功获取概念板块列表，共 {len(df)} 条记录")
        print(df.head(3))
        
        # 测试概念板块成分股
        first_concept_code = df['code'].iloc[0]
        print(f"\n2. 正在获取概念板块 {first_concept_code} 的成分股...")
        df_stocks = fetch_concept_stocks(concept_code=first_concept_code)
        if df_stocks is not None and len(df_stocks) > 0:
            print(f"成功获取概念板块成分股，共 {len(df_stocks)} 条记录")
            print(df_stocks.head(3))
        else:
            print(f"未获取到概念板块成分股")
        
        # 测试概念板块日线数据
        print(f"\n3. 正在获取概念板块 {first_concept_code} 的日线数据...")
        df_daily = fetch_concept_daily(concept_code=first_concept_code, start_date=None, end_date=None)
        if df_daily is not None and len(df_daily) > 0:
            print(f"成功获取概念板块日线数据，共 {len(df_daily)} 条记录")
            print(df_daily.head(3))
        else:
            print(f"未获取到概念板块日线数据")
    else:
        print(f"未获取到概念板块列表")
    
    # 测试行业板块列表
    print("\n4. 正在获取行业板块列表...")
    df = fetch_industry_list()
    if df is not None and len(df) > 0:
        print(f"成功获取行业板块列表，共 {len(df)} 条记录")
        print(df.head(3))
        
        # 测试行业板块成分股
        first_industry_code = df['code'].iloc[0]
        print(f"\n5. 正在获取行业板块 {first_industry_code} 的成分股...")
        df_stocks = fetch_industry_stocks(industry_code=first_industry_code)
        if df_stocks is not None and len(df_stocks) > 0:
            print(f"成功获取行业板块成分股，共 {len(df_stocks)} 条记录")
            print(df_stocks.head(3))
        else:
            print(f"未获取到行业板块成分股")
        
        # 测试行业板块日线数据
        print(f"\n6. 正在获取行业板块 {first_industry_code} 的日线数据...")
        df_daily = fetch_industry_daily(industry_code=first_industry_code, start_date=None, end_date=None)
        if df_daily is not None and len(df_daily) > 0:
            print(f"成功获取行业板块日线数据，共 {len(df_daily)} 条记录")
            print(df_daily.head(3))
        else:
            print(f"未获取到行业板块日线数据")
    else:
        print(f"未获取到行业板块列表")


def test_special_info(date=None):
    """测试特殊信息模块"""
    if date is None:
        date = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
    
    print(f"\n===== 测试特殊信息模块 - 日期：{date} =====")
    
    # 测试龙虎榜
    print("\n1. 正在获取龙虎榜信息...")
    df = fetch_top_list(date=date)
    if df is not None and len(df) > 0:
        print(f"成功获取龙虎榜信息，共 {len(df)} 条记录")
        print(df.head(3))
    else:
        print(f"未获取到龙虎榜信息")
    
    # 测试龙虎榜机构
    print("\n2. 正在获取龙虎榜机构信息...")
    df = fetch_top_inst(date=date)
    if df is not None and len(df) > 0:
        print(f"成功获取龙虎榜机构信息，共 {len(df)} 条记录")
        print(df.head(3))
    else:
        print(f"未获取到龙虎榜机构信息")
    
    # 测试解禁股
    print("\n3. 正在获取解禁股信息...")
    df = fetch_restricted_release(date=date)
    if df is not None and len(df) > 0:
        print(f"成功获取解禁股信息，共 {len(df)} 条记录")
        print(df.head(3))
    else:
        print(f"未获取到解禁股信息")
    
    # 测试沪深港通资金流向
    print("\n4. 正在获取沪深港通资金流向信息...")
    df = fetch_moneyflow_hsgt(date=date)
    if df is not None and len(df) > 0:
        print(f"成功获取沪深港通资金流向信息，共 {len(df)} 条记录")
        print(df.head(3))
    else:
        print(f"未获取到沪深港通资金流向信息")
    
    # 测试个股资金流向
    print("\n5. 正在获取个股资金流向信息...")
    df = fetch_moneyflow_stock(date=date)
    if df is not None and len(df) > 0:
        print(f"成功获取个股资金流向信息，共 {len(df)} 条记录")
        print(df.head(3))
    else:
        print(f"未获取到个股资金流向信息")
    
    # 测试板块资金流向
    print("\n6. 正在获取板块资金流向信息...")
    df = fetch_moneyflow_sector(date=date)
    if df is not None and len(df) > 0:
        print(f"成功获取板块资金流向信息，共 {len(df)} 条记录")
        print(df.head(3))
    else:
        print(f"未获取到板块资金流向信息")


def main():
    parser = argparse.ArgumentParser(description='测试热点信息、板块信息和特殊信息模块')
    parser.add_argument('--module', '-m', choices=['hot', 'block', 'special', 'all'], 
                        default='all', help='要测试的模块')
    parser.add_argument('--date', '-d', help='指定测试日期，格式为YYYY-MM-DD')
    
    args = parser.parse_args()
    
    print(f"命令行参数: module={args.module}, date={args.date}")
    
    date = args.date
    
    if args.module == 'hot' or args.module == 'all':
        test_hot_info(date)
    
    if args.module == 'block' or args.module == 'all':
        test_block_info()
    
    if args.module == 'special' or args.module == 'all':
        test_special_info(date)


if __name__ == '__main__':
    print("脚本开始执行")
    main()
    print("脚本执行完毕") 