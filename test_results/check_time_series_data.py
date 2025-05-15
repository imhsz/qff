#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试akshare不同时间尺度的数据获取
包括日线、周线、月线、分钟线等多种时间尺度
"""

import akshare as ak
import pandas as pd
import time
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os

# 设置matplotlib中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

def test_time_series_data():
    """测试不同时间尺度的数据获取"""
    print(f"开始测试不同时间尺度数据，当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"AKShare 版本: {ak.__version__}")
    
    # 创建charts目录用于保存图表
    charts_dir = "charts"
    if not os.path.exists(charts_dir):
        os.makedirs(charts_dir)
    
    # 设置测试的股票代码
    symbol = "000001"  # 平安银行
    symbol_name = "平安银行"
    
    results = {}  # 存储测试结果
    
    # 1. 测试日线数据
    try:
        print("\n测试1: 获取日线数据")
        start_time = time.time()
        
        # 获取最近1年的数据
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        
        daily_data = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                         start_date=start_date, end_date=end_date, 
                                         adjust="qfq")  # 前复权
        end_time = time.time()
        
        if not daily_data.empty and len(daily_data) > 200:  # 交易日一年应该超过200天
            print(f"✓ 成功获取{symbol_name}日线数据 {len(daily_data)} 条记录")
            print(f"  数据范围: {daily_data['日期'].min()} 至 {daily_data['日期'].max()}")
            print(f"  样例数据:\n{daily_data.head()}")
            print(f"  耗时: {end_time - start_time:.2f}秒")
            
            # 绘制K线图
            plt.figure(figsize=(12, 6))
            plt.plot(daily_data['日期'], daily_data['收盘'], label='收盘价')
            plt.title(f"{symbol_name}日线图 - {daily_data['日期'].min()} 至 {daily_data['日期'].max()}")
            plt.xlabel('日期')
            plt.ylabel('价格')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.legend()
            plt.savefig(f"{charts_dir}/{symbol}_daily.png")
            plt.close()
            
            results["日线数据"] = "成功"
        else:
            print(f"✗ 获取日线数据失败或数据不完整，仅获取到 {len(daily_data)} 条记录")
            results["日线数据"] = "失败"
    except Exception as e:
        print(f"✗ 获取日线数据出错: {e}")
        results["日线数据"] = f"错误: {str(e)}"
    
    # 2. 测试周线数据
    try:
        print("\n测试2: 获取周线数据")
        start_time = time.time()
        
        weekly_data = ak.stock_zh_a_hist(symbol=symbol, period="weekly", 
                                           start_date=start_date, end_date=end_date, 
                                           adjust="qfq")
        end_time = time.time()
        
        if not weekly_data.empty and len(weekly_data) > 40:  # 一年应该有超过40周
            print(f"✓ 成功获取{symbol_name}周线数据 {len(weekly_data)} 条记录")
            print(f"  数据范围: {weekly_data['日期'].min()} 至 {weekly_data['日期'].max()}")
            print(f"  样例数据:\n{weekly_data.head()}")
            print(f"  耗时: {end_time - start_time:.2f}秒")
            
            # 绘制K线图
            plt.figure(figsize=(12, 6))
            plt.plot(weekly_data['日期'], weekly_data['收盘'], label='收盘价')
            plt.title(f"{symbol_name}周线图 - {weekly_data['日期'].min()} 至 {weekly_data['日期'].max()}")
            plt.xlabel('日期')
            plt.ylabel('价格')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.legend()
            plt.savefig(f"{charts_dir}/{symbol}_weekly.png")
            plt.close()
            
            results["周线数据"] = "成功"
        else:
            print(f"✗ 获取周线数据失败或数据不完整，仅获取到 {len(weekly_data)} 条记录")
            results["周线数据"] = "失败"
    except Exception as e:
        print(f"✗ 获取周线数据出错: {e}")
        results["周线数据"] = f"错误: {str(e)}"
    
    # 3. 测试月线数据
    try:
        print("\n测试3: 获取月线数据")
        start_time = time.time()
        
        # 获取最近2年的月线数据
        start_date_monthly = (datetime.now() - timedelta(days=365*2)).strftime('%Y%m%d')
        
        monthly_data = ak.stock_zh_a_hist(symbol=symbol, period="monthly", 
                                            start_date=start_date_monthly, end_date=end_date, 
                                            adjust="qfq")
        end_time = time.time()
        
        if not monthly_data.empty and len(monthly_data) > 10:  # 两年应该有超过20个月
            print(f"✓ 成功获取{symbol_name}月线数据 {len(monthly_data)} 条记录")
            print(f"  数据范围: {monthly_data['日期'].min()} 至 {monthly_data['日期'].max()}")
            print(f"  样例数据:\n{monthly_data.head()}")
            print(f"  耗时: {end_time - start_time:.2f}秒")
            
            # 绘制K线图
            plt.figure(figsize=(12, 6))
            plt.plot(monthly_data['日期'], monthly_data['收盘'], label='收盘价')
            plt.title(f"{symbol_name}月线图 - {monthly_data['日期'].min()} 至 {monthly_data['日期'].max()}")
            plt.xlabel('日期')
            plt.ylabel('价格')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.legend()
            plt.savefig(f"{charts_dir}/{symbol}_monthly.png")
            plt.close()
            
            results["月线数据"] = "成功"
        else:
            print(f"✗ 获取月线数据失败或数据不完整，仅获取到 {len(monthly_data)} 条记录")
            results["月线数据"] = "失败"
    except Exception as e:
        print(f"✗ 获取月线数据出错: {e}")
        results["月线数据"] = f"错误: {str(e)}"
    
    # 4. 测试分钟级数据 - 使用东方财富网站数据
    try:
        print("\n测试4: 获取分钟级数据（东方财富）")
        start_time = time.time()
        
        # 使用东方财富分钟数据接口
        min_data = ak.stock_zh_a_hist_min_em(symbol=symbol, period='1', adjust='qfq')
        end_time = time.time()
        
        if not min_data.empty:
            print(f"✓ 成功获取{symbol_name}分钟线数据 {len(min_data)} 条记录")
            print(f"  数据范围: {min_data['时间'].min()} 至 {min_data['时间'].max()}")
            print(f"  样例数据:\n{min_data.head()}")
            print(f"  耗时: {end_time - start_time:.2f}秒")
            
            # 绘制分钟线图
            plt.figure(figsize=(12, 6))
            plt.plot(min_data['时间'], min_data['收盘'], label='收盘价')
            plt.title(f"{symbol_name}分钟线图 - {min_data['时间'].min()} 至 {min_data['时间'].max()}")
            plt.xlabel('时间')
            plt.ylabel('价格')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.legend()
            plt.savefig(f"{charts_dir}/{symbol}_1min_em.png")
            plt.close()
            
            results["分钟线数据(东财)"] = "成功"
        else:
            print(f"✗ 获取分钟线数据失败或数据为空")
            results["分钟线数据(东财)"] = "失败"
    except Exception as e:
        print(f"✗ 获取分钟线数据出错: {e}")
        results["分钟线数据(东财)"] = f"错误: {str(e)}"
    
    # 5. A股分钟级别数据（新浪）
    try:
        print("\n测试5: 获取分钟级数据（新浪）")
        start_time = time.time()
        
        # 使用新浪分钟数据接口
        sina_symbol = f"sh{symbol}" if symbol.startswith('6') else f"sz{symbol}"
        min_data_sina = ak.stock_zh_a_minute(symbol=sina_symbol, period='1', adjust='qfq')
        end_time = time.time()
        
        if not min_data_sina.empty:
            print(f"✓ 成功获取{symbol_name}分钟线数据(新浪) {len(min_data_sina)} 条记录")
            first_data_point = min_data_sina.iloc[0]
            last_data_point = min_data_sina.iloc[-1]
            
            # 使用'day'列作为数据范围说明
            print(f"  数据范围: {first_data_point['day']} 至 {last_data_point['day']}")
            print(f"  样例数据:\n{min_data_sina.head()}")
            print(f"  耗时: {end_time - start_time:.2f}秒")
            
            # 绘制分钟线图
            plt.figure(figsize=(12, 6))
            # 使用range(len)作为x轴坐标
            x_axis = range(len(min_data_sina))
            plt.plot(x_axis, min_data_sina['close'], label='收盘价')
            plt.title(f"{symbol_name}分钟线图(新浪) - 共{len(min_data_sina)}条记录")
            plt.xlabel('时间点')
            plt.ylabel('价格')
            plt.xticks([])  # 隐藏x轴刻度
            plt.tight_layout()
            plt.legend()
            plt.savefig(f"{charts_dir}/{symbol}_1min_sina.png")
            plt.close()
            
            results["分钟线数据(新浪)"] = "成功"
        else:
            print(f"✗ 获取分钟线数据(新浪)失败或数据为空")
            results["分钟线数据(新浪)"] = "失败"
    except Exception as e:
        print(f"✗ 获取分钟线数据(新浪)出错: {e}")
        results["分钟线数据(新浪)"] = f"错误: {str(e)}"
    
    # 6. 测试5分钟K线数据
    try:
        print("\n测试6: 获取5分钟K线数据")
        start_time = time.time()
        
        # 使用东方财富的5分钟数据接口
        min5_data = ak.stock_zh_a_hist_min_em(symbol=symbol, period='5', adjust='qfq')
        end_time = time.time()
        
        if not min5_data.empty:
            print(f"✓ 成功获取{symbol_name} 5分钟K线数据 {len(min5_data)} 条记录")
            print(f"  数据范围: {min5_data['时间'].min()} 至 {min5_data['时间'].max()}")
            print(f"  样例数据:\n{min5_data.head()}")
            print(f"  耗时: {end_time - start_time:.2f}秒")
            
            # 绘制5分钟K线图
            plt.figure(figsize=(12, 6))
            plt.plot(min5_data['时间'], min5_data['收盘'], label='收盘价')
            plt.title(f"{symbol_name} 5分钟K线图 - {min5_data['时间'].min()} 至 {min5_data['时间'].max()}")
            plt.xlabel('时间')
            plt.ylabel('价格')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.legend()
            plt.savefig(f"{charts_dir}/{symbol}_5min_em.png")
            plt.close()
            
            results["5分钟K线数据"] = "成功"
        else:
            print(f"✗ 获取5分钟K线数据失败或数据为空")
            results["5分钟K线数据"] = "失败"
    except Exception as e:
        print(f"✗ 获取5分钟K线数据出错: {e}")
        results["5分钟K线数据"] = f"错误: {str(e)}"
    
    # 汇总结果
    print("\n======= 测试结果汇总 =======")
    total_tests = len(results)
    success_count = sum(1 for result in results.values() if "成功" in result)
    
    print(f"总测试项: {total_tests}, 成功: {success_count}, 失败: {total_tests - success_count}")
    print(f"成功率: {success_count/total_tests*100:.1f}%")
    
    for test_name, result in results.items():
        status = "✓" if "成功" in result else "✗"
        print(f"{status} {test_name}: {result}")
    
    if success_count == total_tests:
        print(f"\n所有时间尺度数据测试通过！图表已保存至 {charts_dir} 目录")
    else:
        print(f"\n注意：有{total_tests - success_count}项测试未通过，请检查网络连接或API可用性。")
        print(f"成功的测试结果图表已保存至 {charts_dir} 目录")

if __name__ == "__main__":
    test_time_series_data() 