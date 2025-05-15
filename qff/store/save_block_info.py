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

import time
import pandas as pd
from qff.price.block_info import (fetch_concept_list, fetch_concept_stocks, fetch_concept_daily,
                                fetch_industry_list, fetch_industry_stocks, fetch_industry_daily)
from qff.tools.date import now_time, get_real_trade_date
from qff.tools.utils import util_to_json_from_pandas
from qff.tools.mongo import DATABASE

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
    start_time = time.time()
    
    for i, code in enumerate(concept_codes):
        print(f'Fetching concept daily {i+1}/{len(concept_codes)}: {code}')
        
        # 获取概念板块日线数据
        df = fetch_concept_daily(concept_code=code, start_date=start_date, end_date=end_date)
        
        if df is not None and len(df) > 0:
            # 如果有日期范围，先删除对应日期的数据
            if start_date and end_date:
                coll.delete_many({'block_code': code, 'date': {'$gte': start_date, '$lte': end_date}})
            elif end_date:
                coll.delete_many({'block_code': code, 'date': {'$lte': end_date}})
            
            # 插入新数据
            coll.insert_many(util_to_json_from_pandas(df))
            total_records += len(df)
        
        # 避免请求过快
        if i < len(concept_codes) - 1:
            time.sleep(0.5)
    
    print(f'SUCCESS SAVE CONCEPT DAILY DATA, Total: {total_records} records in {(time.time() - start_time):.2f}s.')


def save_industry_list():
    """
    保存行业板块列表到数据库
    
    :return: None
    """
    print('==== NOW SAVE INDUSTRY LIST DATA ====')
    
    # 获取行业板块列表
    df = fetch_industry_list()
    
    if df is not None and len(df) > 0:
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
    start_time = time.time()
    
    for i, code in enumerate(industry_codes):
        print(f'Fetching industry daily {i+1}/{len(industry_codes)}: {code}')
        
        # 获取行业板块日线数据
        df = fetch_industry_daily(industry_code=code, start_date=start_date, end_date=end_date)
        
        if df is not None and len(df) > 0:
            # 如果有日期范围，先删除对应日期的数据
            if start_date and end_date:
                coll.delete_many({'block_code': code, 'date': {'$gte': start_date, '$lte': end_date}})
            elif end_date:
                coll.delete_many({'block_code': code, 'date': {'$lte': end_date}})
            
            # 插入新数据
            coll.insert_many(util_to_json_from_pandas(df))
            total_records += len(df)
        
        # 避免请求过快
        if i < len(industry_codes) - 1:
            time.sleep(0.5)
    
    print(f'SUCCESS SAVE INDUSTRY DAILY DATA, Total: {total_records} records in {(time.time() - start_time):.2f}s.') 