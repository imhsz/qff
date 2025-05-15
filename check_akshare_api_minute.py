#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
查找akshare中的分钟数据API
"""

import akshare as ak
import sys

def find_minute_apis():
    """查找与分钟数据相关的API"""
    print(f"AKShare 版本: {ak.__version__}")
    print(f"Python 版本: {sys.version}")
    
    # 查找可能的分钟数据API
    keywords = ['minute', 'min', '分钟', 'hist_min']
    
    all_apis = dir(ak)
    
    print("\n可能的分钟数据API:")
    for keyword in keywords:
        apis = [api for api in all_apis if keyword.lower() in api.lower()]
        for api in sorted(apis):
            print(f" - {api}")
    
    # 特别测试一个分钟数据API
    try:
        print("\n尝试调用 stock_zh_a_hist_min_em API:")
        symbol = "000001"  # 平安银行
        result = ak.stock_zh_a_hist_min_em(symbol=symbol, period='1', adjust='qfq')
        if not result.empty:
            print(f"API调用成功! 获取到 {len(result)} 条记录")
            print(f"数据列: {result.columns.tolist()}")
            print(f"样例数据:\n{result.head()}")
        else:
            print("API调用成功，但返回数据为空")
    except Exception as e:
        print(f"API调用失败: {e}")
        
        # 尝试不带参数调用
        try:
            print("\n尝试不带参数调用:")
            help_text = ak.stock_zh_a_hist_min_em.__doc__
            print(f"API帮助文档: {help_text}")
        except Exception as e2:
            print(f"获取API帮助文档失败: {e2}")
    
    # 尝试查看其他可能的分钟数据API
    for api_name in ["stock_zh_a_minute", "stock_zh_a_hist_min", "stock_zh_a_minute_tx"]:
        try:
            if hasattr(ak, api_name):
                print(f"\n检测到API: {api_name}")
                api_func = getattr(ak, api_name)
                help_text = api_func.__doc__
                print(f"API帮助文档: {help_text}")
            else:
                print(f"\nAPI {api_name} 不存在")
        except Exception as e:
            print(f"检查API {api_name} 失败: {e}")

if __name__ == "__main__":
    find_minute_apis() 