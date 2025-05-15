#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试涨停信息、板块数据和龙虎榜等数据的获取和保存功能
"""

import akshare as ak
import pandas as pd
import datetime
import time
import os
import sys
import subprocess

def run_qff_command(command):
    """
    运行qff命令并捕获输出
    """
    print(f"\n执行命令: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True)
        print(result.stdout)
        if result.stderr:
            print(f"错误: {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        print(f"输出: {e.stdout}")
        print(f"错误: {e.stderr}")
        return False

def test_akshare_api_direct():
    """直接调用AKShare API测试可用性"""
    print("\n===== 直接测试AKShare API可用性 =====")
    
    # 1. 测试涨停数据
    print("\n1. 测试涨停数据...")
    try:
        # 使用特定日期避免最新日期可能没有数据
        df = ak.stock_zt_pool_em(date="20230701")
        if df is not None and len(df) > 0:
            print(f"✓ 成功获取涨停数据，共 {len(df)} 条记录")
            print(df.head(3))
        else:
            print("✗ 涨停数据API返回空数据")
    except Exception as e:
        print(f"✗ 涨停数据API调用失败: {e}")
    
    # 2. 测试概念板块列表
    print("\n2. 测试概念板块列表...")
    concept_code = None
    try:
        df = ak.stock_board_concept_name_em()
        if df is not None and len(df) > 0:
            print(f"✓ 成功获取概念板块列表，共 {len(df)} 条记录")
            print(df.head(3))
            # 获取一个概念板块代码用于后续测试
            if '代码' in df.columns:
                concept_code = df.iloc[0]['代码']
            elif '板块代码' in df.columns:
                concept_code = df.iloc[0]['板块代码']
            else:
                for col in df.columns:
                    if 'code' in col.lower() or '代码' in col:
                        concept_code = df.iloc[0][col]
                        break
        else:
            print("✗ 概念板块列表API返回空数据")
    except Exception as e:
        print(f"✗ 概念板块列表API调用失败: {e}")
    
    # 3. 测试概念板块成分股
    if concept_code:
        print(f"\n3. 测试概念板块成分股 - 使用板块代码: {concept_code}...")
        try:
            df = ak.stock_board_concept_cons_em(symbol=concept_code)
            if df is not None and len(df) > 0:
                print(f"✓ 成功获取概念板块成分股，共 {len(df)} 条记录")
                print(df.head(3))
            else:
                print("✗ 概念板块成分股API返回空数据")
        except Exception as e:
            print(f"✗ 概念板块成分股API调用失败: {e}")
    else:
        print("\n3. 跳过概念板块成分股测试，因为无法获取概念板块代码")
    
    # 4. 测试概念板块日线数据
    if concept_code:
        print(f"\n4. 测试概念板块日线数据 - 使用板块代码: {concept_code}...")
        try:
            df = ak.stock_board_concept_hist_em(symbol=concept_code)
            if df is not None and len(df) > 0:
                print(f"✓ 成功获取概念板块日线数据，共 {len(df)} 条记录")
                print(df.head(3))
            else:
                print("✗ 概念板块日线数据API返回空数据")
        except Exception as e:
            print(f"✗ 概念板块日线数据API调用失败: {e}")
    else:
        print("\n4. 跳过概念板块日线数据测试，因为无法获取概念板块代码")
    
    # 5. 测试行业板块列表
    print("\n5. 测试行业板块列表...")
    industry_code = None
    try:
        df = ak.stock_board_industry_name_em()
        if df is not None and len(df) > 0:
            print(f"✓ 成功获取行业板块列表，共 {len(df)} 条记录")
            print(df.head(3))
            # 获取一个行业板块代码用于后续测试
            if '代码' in df.columns:
                industry_code = df.iloc[0]['代码']
            elif '板块代码' in df.columns:
                industry_code = df.iloc[0]['板块代码']
            else:
                for col in df.columns:
                    if 'code' in col.lower() or '代码' in col:
                        industry_code = df.iloc[0][col]
                        break
        else:
            print("✗ 行业板块列表API返回空数据")
    except Exception as e:
        print(f"✗ 行业板块列表API调用失败: {e}")
    
    # 6. 测试行业板块成分股
    if industry_code:
        print(f"\n6. 测试行业板块成分股 - 使用板块代码: {industry_code}...")
        try:
            df = ak.stock_board_industry_cons_em(symbol=industry_code)
            if df is not None and len(df) > 0:
                print(f"✓ 成功获取行业板块成分股，共 {len(df)} 条记录")
                print(df.head(3))
            else:
                print("✗ 行业板块成分股API返回空数据")
        except Exception as e:
            print(f"✗ 行业板块成分股API调用失败: {e}")
    else:
        print("\n6. 跳过行业板块成分股测试，因为无法获取行业板块代码")
    
    # 7. 测试行业板块日线数据
    if industry_code:
        print(f"\n7. 测试行业板块日线数据 - 使用板块代码: {industry_code}...")
        try:
            df = ak.stock_board_industry_hist_em(symbol=industry_code)
            if df is not None and len(df) > 0:
                print(f"✓ 成功获取行业板块日线数据，共 {len(df)} 条记录")
                print(df.head(3))
            else:
                print("✗ 行业板块日线数据API返回空数据")
        except Exception as e:
            print(f"✗ 行业板块日线数据API调用失败: {e}")
    else:
        print("\n7. 跳过行业板块日线数据测试，因为无法获取行业板块代码")
    
    # 8. 测试龙虎榜数据
    print("\n8. 测试龙虎榜数据...")
    try:
        # 使用正确的API名称
        try:
            df = ak.stock_lhb_detail_em(date="20230701")
            print("使用 stock_lhb_detail_em API")
        except Exception as e1:
            print(f"使用 stock_lhb_detail_em API失败: {e1}")
            try:
                df = ak.stock_em_lhb_detail(date="20230701")
                print("使用 stock_em_lhb_detail API")
            except Exception as e2:
                print(f"使用 stock_em_lhb_detail API失败: {e2}")
                # 尝试其他可能的龙虎榜相关API
                df = ak.stock_lhb_stock_detail_em(date="20230701") 
                print("使用 stock_lhb_stock_detail_em API")
                
        if df is not None and len(df) > 0:
            print(f"✓ 成功获取龙虎榜数据，共 {len(df)} 条记录")
            print(df.head(3))
        else:
            print("✗ 龙虎榜数据API返回空数据")
    except Exception as e:
        print(f"✗ 龙虎榜数据API调用失败: {e}")
    
    # 9. 测试资金流向
    print("\n9. 测试资金流向数据...")
    try:
        # 使用不同的可能API名称
        try:
            df = ak.stock_individual_fund_flow_rank(indicator="今日")
        except:
            try:
                df = ak.stock_fund_flow_individual(indicator="今日")
            except:
                df = ak.stock_fund_flow_individual_em()
                
        if df is not None and len(df) > 0:
            print(f"✓ 成功获取资金流向数据，共 {len(df)} 条记录")
            print(df.head(3))
        else:
            print("✗ 资金流向数据API返回空数据")
    except Exception as e:
        print(f"✗ 资金流向数据API调用失败: {e}")

def test_qff_save_commands():
    """测试qff save命令"""
    print("\n===== 测试qff save命令 =====")
    
    commands = [
        # 涨停信息
        "qff save limit_up",
        # 跌停信息
        "qff save limit_down",
        # 概念板块
        "qff save concept_list",
        "qff save concept_stocks",
        "qff save concept_daily",
        # 行业板块
        "qff save industry_list",
        "qff save industry_stocks",
        "qff save industry_daily",
        # 龙虎榜
        "qff save top_list",
        "qff save top_inst",
        # 资金流向
        "qff save moneyflow_stock",
        "qff save moneyflow_sector",
    ]
    
    results = {}
    for command in commands:
        results[command] = run_qff_command(command)
    
    # 测试一键保存命令
    group_commands = [
        # 一键保存所有新数据
        "qff save hot_info",
        "qff save block_info",
        "qff save special_info"
    ]
    
    for command in group_commands:
        results[command] = run_qff_command(command)
    
    # 打印总结报告
    print("\n===== qff save命令测试结果汇总 =====")
    success_count = sum(1 for r in results.values() if r)
    total_count = len(results)
    print(f"总命令数: {total_count}, 成功: {success_count}, 失败: {total_count - success_count}")
    print(f"成功率: {success_count / total_count * 100:.1f}%")
    
    for command, success in results.items():
        status = "✓" if success else "✗"
        print(f"{status} {command}")
    
    return results

def check_database_storage():
    """检查数据是否正确持久化到数据库"""
    print("\n===== 检查数据库存储 =====")
    
    # 使用qff dbinfo命令检查数据库
    run_qff_command("qff dbinfo")
    
    # 列出关键数据表并检查
    collections = [
        "limit_up",             # 涨停信息
        "limit_down",           # 跌停信息
        "concept_list",         # 概念板块列表
        "concept_stocks",       # 概念板块成分股
        "concept_daily",        # 概念板块日线数据
        "industry_list",        # 行业板块列表
        "industry_stocks",      # 行业板块成分股
        "industry_daily",       # 行业板块日线数据
        "top_list",             # 龙虎榜
        "top_inst",             # 龙虎榜机构
        "moneyflow_stock",      # 个股资金流向
        "moneyflow_sector"      # 板块资金流向
    ]
    
    for collection in collections:
        print(f"\n检查集合 {collection}...")
        run_qff_command(f"qff find {collection} --limit 3")

def main():
    """主函数"""
    print("\n====== 开始测试新功能数据获取与保存 ======")
    print(f"当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 第一步：直接测试AKShare API
    test_akshare_api_direct()
    
    # 跳过询问，直接继续测试
    print("\n继续测试qff save命令和数据库存储...")
    
    # 第二步：测试qff save命令
    save_results = test_qff_save_commands()
    
    # 第三步：检查数据库存储
    if sum(1 for r in save_results.values() if r) > 0:
        check_database_storage()
    else:
        print("\n由于qff save命令测试全部失败，跳过数据库存储检查")
    
    print("\n====== 测试完成 ======")

if __name__ == "__main__":
    main() 