#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查akshare数据获取的最低要求
测试股票列表、日线数据和最新行情等核心功能
"""

import akshare as ak
import pandas as pd
import time
import os
from datetime import datetime, timedelta

def check_api_requirements():
    """检查akshare数据获取的最低要求"""
    success_count = 0
    total_tests = 5
    results = {}
    
    print(f"开始测试，当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"AKShare 版本: {ak.__version__}")
    
    # 测试1：获取股票列表
    try:
        print("\n测试1: 获取A股股票列表")
        start_time = time.time()
        stock_list = ak.stock_info_a_code_name()
        end_time = time.time()
        
        if not stock_list.empty and len(stock_list) > 3000:  # 应该有超过3000只股票
            print(f"✓ 成功获取 {len(stock_list)} 只A股股票")
            print(f"  样例数据:\n{stock_list.head()}")
            print(f"  耗时: {end_time - start_time:.2f}秒")
            success_count += 1
            results["股票列表"] = "成功"
        else:
            print(f"✗ 获取股票列表失败或数据不完整，仅获取到 {len(stock_list)} 只股票")
            results["股票列表"] = "失败"
    except Exception as e:
        print(f"✗ 获取股票列表出错: {e}")
        results["股票列表"] = f"错误: {str(e)}"
    
    # 测试2：获取单只股票的历史日线数据
    try:
        print("\n测试2: 获取平安银行(000001)历史日线数据")
        start_time = time.time()
        # 获取最近30天的数据
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        stock_data = ak.stock_zh_a_hist(symbol="000001", period="daily", 
                                         start_date=start_date, end_date=end_date, 
                                         adjust="")
        end_time = time.time()
        
        if not stock_data.empty:
            print(f"✓ 成功获取平安银行历史数据 {len(stock_data)} 条记录")
            print(f"  数据范围: {stock_data['日期'].min()} 至 {stock_data['日期'].max()}")
            print(f"  样例数据:\n{stock_data.head()}")
            print(f"  耗时: {end_time - start_time:.2f}秒")
            success_count += 1
            results["日线数据"] = "成功"
        else:
            print("✗ 获取历史日线数据失败或数据为空")
            results["日线数据"] = "失败"
    except Exception as e:
        print(f"✗ 获取历史日线数据出错: {e}")
        results["日线数据"] = f"错误: {str(e)}"
    
    # 测试3：获取实时行情数据
    try:
        print("\n测试3: 获取实时行情数据")
        start_time = time.time()
        realtime_data = ak.stock_zh_a_spot_em()
        end_time = time.time()
        
        if not realtime_data.empty and len(realtime_data) > 3000:
            print(f"✓ 成功获取 {len(realtime_data)} 只股票的实时行情")
            print(f"  样例数据:\n{realtime_data.head()}")
            print(f"  耗时: {end_time - start_time:.2f}秒")
            success_count += 1
            results["实时行情"] = "成功"
        else:
            print(f"✗ 获取实时行情失败或数据不完整，仅获取到 {len(realtime_data)} 条记录")
            results["实时行情"] = "失败"
    except Exception as e:
        print(f"✗ 获取实时行情出错: {e}")
        results["实时行情"] = f"错误: {str(e)}"
    
    # 测试4：获取指数数据
    try:
        print("\n测试4: 获取上证指数数据")
        start_time = time.time()
        index_data = ak.stock_zh_index_daily(symbol="sh000001")
        end_time = time.time()
        
        if not index_data.empty:
            print(f"✓ 成功获取上证指数数据 {len(index_data)} 条记录")
            print(f"  数据范围: {index_data.index.min()} 至 {index_data.index.max()}")
            print(f"  样例数据:\n{index_data.head()}")
            print(f"  耗时: {end_time - start_time:.2f}秒")
            success_count += 1
            results["指数数据"] = "成功"
        else:
            print("✗ 获取指数数据失败或数据为空")
            results["指数数据"] = "失败"
    except Exception as e:
        print(f"✗ 获取指数数据出错: {e}")
        results["指数数据"] = f"错误: {str(e)}"
    
    # 测试5：获取板块成分股
    try:
        print("\n测试5: 获取板块成分股")
        start_time = time.time()
        concept_stocks = ak.stock_board_concept_cons_em(symbol="人工智能")
        end_time = time.time()
        
        if not concept_stocks.empty:
            print(f"✓ 成功获取人工智能板块成分股 {len(concept_stocks)} 只")
            print(f"  样例数据:\n{concept_stocks.head()}")
            print(f"  耗时: {end_time - start_time:.2f}秒")
            success_count += 1
            results["板块成分股"] = "成功"
        else:
            print("✗ 获取板块成分股失败或数据为空")
            results["板块成分股"] = "失败"
    except Exception as e:
        print(f"✗ 获取板块成分股出错: {e}")
        results["板块成分股"] = f"错误: {str(e)}"
    
    # 汇总结果
    print("\n======= 测试结果汇总 =======")
    print(f"总测试项: {total_tests}, 成功: {success_count}, 失败: {total_tests - success_count}")
    print(f"成功率: {success_count/total_tests*100:.1f}%")
    
    for test_name, result in results.items():
        status = "✓" if "成功" in result else "✗"
        print(f"{status} {test_name}: {result}")
    
    if success_count == total_tests:
        print("\n所有测试通过，akshare数据获取功能正常！")
    else:
        print(f"\n注意：有{total_tests - success_count}项测试未通过，请检查网络连接或API可用性。")

if __name__ == "__main__":
    check_api_requirements() 