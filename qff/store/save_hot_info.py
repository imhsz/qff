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
保存涨停信息、封单强度等短线数据
"""

import time
import pandas as pd
from qff.price.hot_info import fetch_limit_up, fetch_limit_down, fetch_block_trade, fetch_margin_detail
from qff.tools.date import now_time, get_real_trade_date
from qff.tools.utils import util_to_json_from_pandas
from qff.tools.mongo import DATABASE

__all__ = ['save_limit_up', 'save_limit_down', 'save_block_trade', 'save_margin_detail']


def save_limit_up(date=None):
    """
    保存涨停信息数据到数据库
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: None
    """
    if date is None:
        date = get_real_trade_date(now_time()[:10])
    
    print(f'==== NOW SAVE LIMIT_UP DATA {date} ====')
    
    # 获取涨停信息数据
    df = fetch_limit_up(date=date)
    
    if df is not None and len(df) > 0:
        # 创建集合并设置索引
        coll = DATABASE.get_collection('limit_up')
        coll.create_index([('date', 1), ('code', 1)], unique=True)
        
        # 删除同一日期的旧数据
        coll.delete_many({'date': date})
        
        # 插入新数据
        coll.insert_many(util_to_json_from_pandas(df))
        
        print(f'SUCCESS SAVE LIMIT_UP DATA, Total: {len(df)} records.')
    else:
        print('No LIMIT_UP data found.')


def save_limit_down(date=None):
    """
    保存跌停信息数据到数据库
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: None
    """
    if date is None:
        date = get_real_trade_date(now_time()[:10])
    
    print(f'==== NOW SAVE LIMIT_DOWN DATA {date} ====')
    
    # 获取跌停信息数据
    df = fetch_limit_down(date=date)
    
    if df is not None and len(df) > 0:
        # 创建集合并设置索引
        coll = DATABASE.get_collection('limit_down')
        coll.create_index([('date', 1), ('code', 1)], unique=True)
        
        # 删除同一日期的旧数据
        coll.delete_many({'date': date})
        
        # 插入新数据
        coll.insert_many(util_to_json_from_pandas(df))
        
        print(f'SUCCESS SAVE LIMIT_DOWN DATA, Total: {len(df)} records.')
    else:
        print('No LIMIT_DOWN data found.')


def save_block_trade(date=None):
    """
    保存大宗交易数据到数据库
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: None
    """
    if date is None:
        date = get_real_trade_date(now_time()[:10])
    
    print(f'==== NOW SAVE BLOCK_TRADE DATA {date} ====')
    
    # 获取大宗交易数据
    df = fetch_block_trade(date=date)
    
    if df is not None and len(df) > 0:
        # 创建集合并设置索引
        coll = DATABASE.get_collection('block_trade')
        coll.create_index([('date', 1), ('code', 1), ('buyer', 1), ('seller', 1)], unique=True)
        
        # 删除同一日期的旧数据
        coll.delete_many({'date': date})
        
        # 插入新数据
        coll.insert_many(util_to_json_from_pandas(df))
        
        print(f'SUCCESS SAVE BLOCK_TRADE DATA, Total: {len(df)} records.')
    else:
        print('No BLOCK_TRADE data found.')


def save_margin_detail(date=None):
    """
    保存融资融券明细数据到数据库
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: None
    """
    if date is None:
        date = get_real_trade_date(now_time()[:10])
    
    print(f'==== NOW SAVE MARGIN_DETAIL DATA {date} ====')
    
    # 获取融资融券明细数据
    df = fetch_margin_detail(date=date)
    
    if df is not None and len(df) > 0:
        # 创建集合并设置索引
        coll = DATABASE.get_collection('margin_detail')
        coll.create_index([('date', 1), ('code', 1)], unique=True)
        
        # 删除同一日期的旧数据
        coll.delete_many({'date': date})
        
        # 插入新数据
        coll.insert_many(util_to_json_from_pandas(df))
        
        print(f'SUCCESS SAVE MARGIN_DETAIL DATA, Total: {len(df)} records.')
    else:
        print('No MARGIN_DETAIL data found.') 