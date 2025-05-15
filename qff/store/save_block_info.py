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

"""
保存概念板块和行业板块数据及成分股
"""

import os
import datetime
import time
import pandas as pd
from bson.objectid import ObjectId
from qff.price.block_info import (fetch_concept_list, fetch_concept_stocks, fetch_concept_daily,
                                fetch_industry_list, fetch_industry_stocks, fetch_industry_daily)
from qff.tools.date import now_time, get_real_trade_date
from qff.tools.utils import util_to_json_from_pandas
from qff.tools.mongo import DATABASE
from qff.tools.logs import log
from qff.tools.cache import save_data_to_cache, get_cached_data

__all__ = ['save_concept_list', 'save_concept_stocks', 'save_concept_daily',
           'save_industry_list', 'save_industry_stocks', 'save_industry_daily']


def save_concept_list():
    """
    保存概念板块列表到数据库
    
    :return: None
    """
    print('==== NOW SAVE CONCEPT LIST DATA ====')
    
    # 获取概念板块列表
    df = fetch_concept_list()
    
    if df is not None and len(df) > 0:
        # 将数据保存到缓存，以便在API失败时使用
        save_data_to_cache(df, 'concept_list')
        
        # 创建集合并设置索引
        coll = DATABASE.get_collection('concept_list')
        coll.create_index([('date', 1), ('code', 1)], unique=True)
        
        # 删除同一日期的旧数据
        date = df['date'].iloc[0]
        coll.delete_many({'date': date})
        
        # 插入新数据
        coll.insert_many(util_to_json_from_pandas(df))
        
        print(f'SUCCESS SAVE CONCEPT LIST DATA, Total: {len(df)} records.')
        
        # 返回概念板块代码列表，用于后续获取成分股和日线数据
        return df['code'].tolist()
    else:
        # 尝试从缓存中获取数据
        print('尝试从缓存中获取概念板块列表...')
        cached_df = get_cached_data('concept_list')
        if cached_df is not None and len(cached_df) > 0:
            print(f'从缓存中获取概念板块列表成功，数据包含 {len(cached_df)} 条记录')
            return cached_df['code'].tolist()
        else:
            print('No CONCEPT LIST data found.')
            return []


def save_concept_stocks(concept_code=None):
    """
    保存概念板块成分股到数据库
    
    :param concept_code: 概念板块代码，如果为None则获取所有概念板块
    :return: None
    """
    # 获取所有概念板块代码
    if concept_code is None:
        concept_codes = save_concept_list()
    else:
        concept_codes = [concept_code]
    
    if not concept_codes:
        print('No CONCEPT CODE found.')
        return
    
    # 创建集合并设置索引
    coll = DATABASE.get_collection('concept_stocks')
    coll.create_index([('date', 1), ('block_code', 1), ('code', 1)], unique=True)
    
    date = get_real_trade_date(now_time()[:10])
    coll.delete_many({'date': date})
    
    # 依次获取并保存每个概念板块的成分股
    total_records = 0
    start_time = time.time()
    
    for i, code in enumerate(concept_codes):
        print(f'Fetching concept stocks {i+1}/{len(concept_codes)}: {code}')
        
        # 获取概念板块成分股
        df = fetch_concept_stocks(concept_code=code)
        
        if df is not None and len(df) > 0:
            # 插入新数据
            coll.insert_many(util_to_json_from_pandas(df))
            total_records += len(df)
        
        # 避免请求过快
        if i < len(concept_codes) - 1:
            time.sleep(0.5)
    
    print(f'SUCCESS SAVE CONCEPT STOCKS DATA, Total: {total_records} records in {(time.time() - start_time):.2f}s.')


def save_concept_daily(concept_code=None, start_date=None, end_date=None):
    """
    保存概念板块日线数据到数据库
    
    :param concept_code: 概念板块代码，如果为None则获取所有概念板块
    :param start_date: 开始日期，格式为'YYYY-MM-DD'，默认为前60个交易日
    :param end_date: 结束日期，格式为'YYYY-MM-DD'，默认为当前日期
    :return: None
    """
    # 获取所有概念板块代码
    if concept_code is None:
        concept_codes = save_concept_list()
    else:
        concept_codes = [concept_code]
    
    if not concept_codes:
        print('No CONCEPT CODE found.')
        return
    
    # 创建集合并设置索引
    coll = DATABASE.get_collection('concept_daily')
    coll.create_index([('date', 1), ('block_code', 1)], unique=True)
    
    # 依次获取并保存每个概念板块的日线数据
    total_records = 0
    success_blocks = 0
    failed_blocks = 0
    start_time = time.time()
    
    for i, code in enumerate(concept_codes):
        print(f'Fetching concept daily {i+1}/{len(concept_codes)}: {code}')
        
        try:
            # 获取概念板块名称
            concept_name = None
            try:
                concept_df = fetch_concept_list()
                if concept_df is not None:
                    concept_row = concept_df[concept_df['code'] == code]
                    if not concept_row.empty:
                        concept_name = concept_row.iloc[0]['name']
                        log.info(f"找到概念板块 {code} 对应的名称: {concept_name}")
            except Exception as e:
                log.warning(f"查找概念板块 {code} 名称时出错: {str(e)}")
            
            # 获取概念板块日线数据
            df = fetch_concept_daily(concept_code=code, start_date=start_date, end_date=end_date)
            
            if df is not None and len(df) > 0:
                try:
                    # 无论是否有日期范围，都先删除对应的数据以避免重复键错误
                    if start_date and end_date:
                        coll.delete_many({'block_code': code, 'date': {'$gte': start_date, '$lte': end_date}})
                    elif start_date:
                        coll.delete_many({'block_code': code, 'date': {'$gte': start_date}})
                    elif end_date:
                        coll.delete_many({'block_code': code, 'date': {'$lte': end_date}})
                    else:
                        # 如果没有指定日期范围，删除这个板块的所有数据
                        # 或者可以获取数据中的日期范围再删除
                        date_min = df['date'].min()
                        date_max = df['date'].max()
                        coll.delete_many({'block_code': code, 'date': {'$gte': date_min, '$lte': date_max}})
                    
                    # 插入新数据
                    records = util_to_json_from_pandas(df)
                    
                    # 使用bulk操作，允许单条记录失败
                    bulk = coll.initialize_unordered_bulk_op()
                    for record in records:
                        bulk.insert(record)
                    
                    try:
                        bulk.execute()
                    except Exception as bulk_err:
                        # 如果有部分记录插入失败，仅记录错误但不中断程序
                        log.warning(f"部分概念板块 {code} 日线数据插入失败: {str(bulk_err)}")
                    
                    total_records += len(df)
                    success_blocks += 1
                except Exception as e:
                    print(f"保存概念板块 {code} 日线数据异常: {str(e)}")
                    failed_blocks += 1
            else:
                print(f"未获取到概念板块 {code} 的日线数据")
                failed_blocks += 1
        except Exception as e:
            print(f"获取或保存概念板块 {code} 日线数据异常: {str(e)}")
            failed_blocks += 1
        
        # 避免请求过快
        if i < len(concept_codes) - 1:
            time.sleep(0.5)
    
    print(f'SUCCESS SAVE CONCEPT DAILY DATA, Total: {total_records} records in {(time.time() - start_time):.2f}s.')
    print(f'成功板块: {success_blocks}, 失败板块: {failed_blocks}')


def save_industry_list():
    """
    保存行业板块列表到数据库
    
    :return: None
    """
    print('==== NOW SAVE INDUSTRY LIST DATA ====')
    
    # 获取行业板块列表
    df = fetch_industry_list()
    
    if df is not None and len(df) > 0:
        # 将数据保存到缓存，以便在API失败时使用
        save_data_to_cache(df, 'industry_list')
        
        # 创建集合并设置索引
        coll = DATABASE.get_collection('industry_list')
        coll.create_index([('date', 1), ('code', 1)], unique=True)
        
        # 删除同一日期的旧数据
        date = df['date'].iloc[0]
        coll.delete_many({'date': date})
        
        # 插入新数据
        coll.insert_many(util_to_json_from_pandas(df))
        
        print(f'SUCCESS SAVE INDUSTRY LIST DATA, Total: {len(df)} records.')
        
        # 返回行业板块代码列表，用于后续获取成分股和日线数据
        return df['code'].tolist()
    else:
        # 尝试从缓存中获取数据
        print('尝试从缓存中获取行业板块列表...')
        cached_df = get_cached_data('industry_list')
        if cached_df is not None and len(cached_df) > 0:
            print(f'从缓存中获取行业板块列表成功，数据包含 {len(cached_df)} 条记录')
            return cached_df['code'].tolist()
        else:
            print('No INDUSTRY LIST data found.')
            return []


def save_industry_stocks(industry_code=None):
    """
    保存行业板块成分股到数据库
    
    :param industry_code: 行业板块代码，如果为None则获取所有行业板块
    :return: None
    """
    # 获取所有行业板块代码
    if industry_code is None:
        industry_codes = save_industry_list()
    else:
        industry_codes = [industry_code]
    
    if not industry_codes:
        print('No INDUSTRY CODE found.')
        return
    
    # 创建集合并设置索引
    coll = DATABASE.get_collection('industry_stocks')
    coll.create_index([('date', 1), ('block_code', 1), ('code', 1)], unique=True)
    
    date = get_real_trade_date(now_time()[:10])
    coll.delete_many({'date': date})
    
    # 依次获取并保存每个行业板块的成分股
    total_records = 0
    start_time = time.time()
    
    for i, code in enumerate(industry_codes):
        print(f'Fetching industry stocks {i+1}/{len(industry_codes)}: {code}')
        
        # 获取行业板块成分股
        df = fetch_industry_stocks(industry_code=code)
        
        if df is not None and len(df) > 0:
            # 插入新数据
            coll.insert_many(util_to_json_from_pandas(df))
            total_records += len(df)
        
        # 避免请求过快
        if i < len(industry_codes) - 1:
            time.sleep(0.5)
    
    print(f'SUCCESS SAVE INDUSTRY STOCKS DATA, Total: {total_records} records in {(time.time() - start_time):.2f}s.')


def save_industry_daily(industry_code=None, start_date=None, end_date=None):
    """
    保存行业板块日线数据到数据库
    
    :param industry_code: 行业板块代码，如果为None则获取所有行业板块
    :param start_date: 开始日期，格式为'YYYY-MM-DD'，默认为前60个交易日
    :param end_date: 结束日期，格式为'YYYY-MM-DD'，默认为当前日期
    :return: None
    """
    # 获取所有行业板块代码
    if industry_code is None:
        industry_codes = save_industry_list()
    else:
        industry_codes = [industry_code]
    
    if not industry_codes:
        print('No INDUSTRY CODE found.')
        return
    
    # 创建集合并设置索引
    coll = DATABASE.get_collection('industry_daily')
    coll.create_index([('date', 1), ('block_code', 1)], unique=True)
    
    # 依次获取并保存每个行业板块的日线数据
    total_records = 0
    success_blocks = 0
    failed_blocks = 0
    start_time = time.time()
    
    for i, code in enumerate(industry_codes):
        print(f'Fetching industry daily {i+1}/{len(industry_codes)}: {code}')
        
        try:
            # 获取行业板块名称
            industry_name = None
            try:
                industry_df = fetch_industry_list()
                if industry_df is not None:
                    industry_row = industry_df[industry_df['code'] == code]
                    if not industry_row.empty:
                        industry_name = industry_row.iloc[0]['name']
                        log.info(f"找到行业板块 {code} 对应的名称: {industry_name}")
            except Exception as e:
                log.warning(f"查找行业板块 {code} 名称时出错: {str(e)}")
            
            # 获取行业板块日线数据
            df = fetch_industry_daily(industry_code=code, start_date=start_date, end_date=end_date)
            
            if df is not None and len(df) > 0:
                try:
                    # 无论是否有日期范围，都先删除对应的数据以避免重复键错误
                    if start_date and end_date:
                        coll.delete_many({'block_code': code, 'date': {'$gte': start_date, '$lte': end_date}})
                    elif start_date:
                        coll.delete_many({'block_code': code, 'date': {'$gte': start_date}})
                    elif end_date:
                        coll.delete_many({'block_code': code, 'date': {'$lte': end_date}})
                    else:
                        # 如果没有指定日期范围，删除这个板块的所有数据
                        # 或者可以获取数据中的日期范围再删除
                        date_min = df['date'].min()
                        date_max = df['date'].max()
                        coll.delete_many({'block_code': code, 'date': {'$gte': date_min, '$lte': date_max}})
                    
                    # 插入新数据
                    records = util_to_json_from_pandas(df)
                    
                    # 使用bulk操作，允许单条记录失败
                    bulk = coll.initialize_unordered_bulk_op()
                    for record in records:
                        bulk.insert(record)
                    
                    try:
                        bulk.execute()
                    except Exception as bulk_err:
                        # 如果有部分记录插入失败，仅记录错误但不中断程序
                        log.warning(f"部分行业板块 {code} 日线数据插入失败: {str(bulk_err)}")
                    
                    total_records += len(df)
                    success_blocks += 1
                except Exception as e:
                    print(f"保存行业板块 {code} 日线数据异常: {str(e)}")
                    failed_blocks += 1
            else:
                print(f"未获取到行业板块 {code} 的日线数据")
                failed_blocks += 1
        except Exception as e:
            print(f"获取或保存行业板块 {code} 日线数据异常: {str(e)}")
            failed_blocks += 1
        
        # 避免请求过快
        if i < len(industry_codes) - 1:
            time.sleep(0.5)
    
    print(f'SUCCESS SAVE INDUSTRY DAILY DATA, Total: {total_records} records in {(time.time() - start_time):.2f}s.')
    print(f'成功板块: {success_blocks}, 失败板块: {failed_blocks}') 