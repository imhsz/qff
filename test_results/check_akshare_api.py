#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查本地安装的akshare包中的API
"""

import akshare as ak
import sys
import pandas as pd

def print_api_info():
    print(f"AKShare 版本: {ak.__version__}")
    print(f"Python 版本: {sys.version}")
    
    # 涨停板相关API
    print("\n涨停板相关API:")
    zt_apis = [api for api in dir(ak) if 'zt' in api.lower() or 'limit_up' in api.lower()]
    for api in sorted(zt_apis):
        print(f" - {api}")
    
    # 跌停板相关API
    print("\n跌停板相关API:")
    dt_apis = [api for api in dir(ak) if 'dt' in api.lower() or 'limit_down' in api.lower()]
    for api in sorted(dt_apis):
        print(f" - {api}")
    
    # 大宗交易相关API
    print("\n大宗交易相关API:")
    block_apis = [api for api in dir(ak) if 'dzjy' in api.lower() or 'block_trade' in api.lower()]
    for api in sorted(block_apis):
        print(f" - {api}")
    
    # 融资融券相关API
    print("\n融资融券相关API:")
    margin_apis = [api for api in dir(ak) if 'margin' in api.lower() or 'rzrq' in api.lower()]
    for api in sorted(margin_apis):
        print(f" - {api}")
    
    # 概念板块相关API
    print("\n概念板块相关API:")
    concept_apis = [api for api in dir(ak) if 'concept' in api.lower() or 'bk' in api.lower()]
    for api in sorted(concept_apis):  # 显示所有API
        print(f" - {api}")
    
    # 行业板块相关API
    print("\n行业板块相关API:")
    industry_apis = [api for api in dir(ak) if 'industry' in api.lower() or 'hy' in api.lower()]
    for api in sorted(industry_apis):  # 显示所有API
        print(f" - {api}")
    
    # 龙虎榜相关API
    print("\n龙虎榜相关API:")
    lhb_apis = [api for api in dir(ak) if 'lhb' in api.lower()]
    for api in sorted(lhb_apis):
        print(f" - {api}")
    
    # 资金流向相关API
    print("\n资金流向相关API:")
    flow_apis = [api for api in dir(ak) if 'fund_flow' in api.lower() or 'money' in api.lower() or 'hsgt' in api.lower()]
    for api in sorted(flow_apis):  # 显示所有API
        print(f" - {api}")
    
    # 新增：股票基本信息相关API
    print("\n股票基本信息相关API:")
    stock_info_apis = [api for api in dir(ak) if 'stock_info' in api.lower() or 'stock_list' in api.lower()]
    for api in sorted(stock_info_apis):
        print(f" - {api}")
    
    # 新增：股票日线行情相关API
    print("\n股票日线行情相关API:")
    stock_daily_apis = [api for api in dir(ak) if 'stock_zh_a_daily' in api.lower() or 'stock_zh_a_hist' in api.lower()]
    for api in sorted(stock_daily_apis):
        print(f" - {api}")
    
    # 新增：指数相关API
    print("\n指数相关API:")
    index_apis = [api for api in dir(ak) if 'index' in api.lower() or 'zs' in api.lower()]
    for api in sorted(index_apis)[:20]:  # 显示前20个
        print(f" - {api}")
    
    # 新增：基金相关API
    print("\n基金相关API:")
    fund_apis = [api for api in dir(ak) if 'fund' in api.lower()]
    for api in sorted(fund_apis)[:20]:  # 显示前20个
        print(f" - {api}")

def test_api_example():
    """测试几个常用API的实际调用"""
    print("\n\n===== API 示例调用测试 =====")
    
    try:
        print("\n股票列表API测试:")
        stock_info = ak.stock_info_a_code_name()
        print(f"获取到 {len(stock_info)} 只股票")
        print(stock_info.head())
    except Exception as e:
        print(f"股票列表API测试失败: {e}")
    
    try:
        print("\n涨停板数据API测试:")
        zt_data = ak.stock_zt_pool_em(date="20230701")
        print(f"获取到 {len(zt_data)} 条涨停记录")
        print(zt_data.head())
    except Exception as e:
        print(f"涨停板数据API测试失败: {e}")
    
    try:
        print("\n股票日线数据API测试:")
        stock_data = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20230601", end_date="20230630", adjust="")
        print(f"获取到 {len(stock_data)} 条日线记录")
        print(stock_data.head())
    except Exception as e:
        print(f"股票日线数据API测试失败: {e}")

if __name__ == "__main__":
    print_api_info()
    test_api_example() 