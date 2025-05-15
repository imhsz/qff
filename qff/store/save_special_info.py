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
保存龙虎榜、解禁股、资金流向等信息
"""

import time
import pandas as pd
from qff.price.special_info import (fetch_top_list, fetch_top_inst, fetch_restricted_release,
                                   fetch_moneyflow_hsgt, fetch_moneyflow_stock, fetch_moneyflow_sector)
from qff.tools.date import now_time, get_real_trade_date
from qff.tools.utils import util_to_json_from_pandas
from qff.tools.mongo import DATABASE

__all__ = ['save_top_list', 'save_top_inst', 'save_restricted_release',
           'save_moneyflow_hsgt', 'save_moneyflow_stock', 'save_moneyflow_sector']


def save_top_list(date=None):
    """
    保存龙虎榜数据到数据库
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: None
    """
    if date is None:
        date = get_real_trade_date(now_time()[:10])
    
    print(f'==== NOW SAVE TOP_LIST DATA {date} ====')
    
    # 获取龙虎榜数据
    df = fetch_top_list(date=date)
    
    if df is not None and len(df) > 0:
        # 创建集合并设置索引
        coll = DATABASE.get_collection('top_list')
        coll.create_index([('date', 1), ('code', 1)], unique=True)
        
        # 删除同一日期的旧数据
        try:
            # 先尝试删除旧数据
            delete_result = coll.delete_many({'date': date})
            print(f"删除旧数据: {delete_result.deleted_count} 条记录")
        except Exception as e:
            print(f"删除旧数据时出错: {e}")
        
        # 使用upsert方式插入新数据，避免重复键错误
        success_count = 0
        error_count = 0
        
        for _, row in df.iterrows():
            data = util_to_json_from_pandas(row.to_frame().T)[0]
            try:
                coll.replace_one(
                    {'date': date, 'code': data['code']},
                    data,
                    upsert=True
                )
                success_count += 1
            except Exception as e:
                print(f"插入数据时出错 code={data['code']}: {e}")
                error_count += 1
        
        print(f'SUCCESS SAVE TOP_LIST DATA, Total: {success_count} records, Errors: {error_count}.')
    else:
        print('No TOP_LIST data found.')


def save_top_inst(date=None):
    """
    保存龙虎榜机构数据到数据库
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: None
    """
    if date is None:
        date = get_real_trade_date(now_time()[:10])
    
    print(f'==== NOW SAVE TOP_INST DATA {date} ====')
    
    # 获取龙虎榜机构数据
    df = fetch_top_inst(date=date)
    
    if df is not None and len(df) > 0:
        # 创建集合并设置索引
        coll = DATABASE.get_collection('top_inst')
        coll.create_index([('date', 1), ('code', 1)], unique=True)
        
        # 删除同一日期的旧数据
        try:
            delete_result = coll.delete_many({'date': date})
            print(f"删除旧数据: {delete_result.deleted_count} 条记录")
        except Exception as e:
            print(f"删除旧数据时出错: {e}")
        
        # 使用upsert方式插入新数据
        success_count = 0
        error_count = 0
        
        for _, row in df.iterrows():
            data = util_to_json_from_pandas(row.to_frame().T)[0]
            try:
                coll.replace_one(
                    {'date': date, 'code': data['code']},
                    data,
                    upsert=True
                )
                success_count += 1
            except Exception as e:
                print(f"插入数据时出错 code={data['code']}: {e}")
                error_count += 1
        
        print(f'SUCCESS SAVE TOP_INST DATA, Total: {success_count} records, Errors: {error_count}.')
    else:
        print('No TOP_INST data found.')


def save_restricted_release(date=None):
    """
    保存解禁股数据到数据库
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: None
    """
    print('==== NOW SAVE RESTRICTED_RELEASE DATA ====')
    
    # 获取解禁股数据
    df = fetch_restricted_release(date=date)
    
    if df is not None and len(df) > 0:
        # 创建集合并设置索引
        coll = DATABASE.get_collection('restricted_release')
        coll.create_index([('release_date', 1), ('code', 1)], unique=True)
        
        # 如果有指定日期，删除对应日期的旧数据
        try:
            if date:
                delete_result = coll.delete_many({'release_date': date})
                print(f'删除日期 {date} 的旧数据: {delete_result.deleted_count} 条记录')
            else:
                # 获取的是未来一段时间的解禁数据，先删除所有记录然后全部重新插入
                delete_result = coll.delete_many({})
                print(f'删除所有旧数据: {delete_result.deleted_count} 条记录')
        except Exception as e:
            print(f"删除旧数据时出错: {e}")
        
        # 使用upsert方式插入新数据
        success_count = 0
        error_count = 0
        
        for _, row in df.iterrows():
            data = util_to_json_from_pandas(row.to_frame().T)[0]
            try:
                coll.replace_one(
                    {'release_date': data['release_date'], 'code': data['code']},
                    data,
                    upsert=True
                )
                success_count += 1
            except Exception as e:
                print(f"插入数据时出错 code={data['code']}: {e}")
                error_count += 1
        
        print(f'SUCCESS SAVE RESTRICTED_RELEASE DATA, Total: {success_count} records, Errors: {error_count}.')
    else:
        print('No RESTRICTED_RELEASE data found.')


def save_moneyflow_hsgt(date=None):
    """
    保存沪深港通资金流向数据到数据库
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: None
    """
    if date is None:
        date = get_real_trade_date(now_time()[:10])
    
    print(f'==== NOW SAVE MONEYFLOW_HSGT DATA {date} ====')
    
    # 获取沪深港通资金流向数据
    df = fetch_moneyflow_hsgt(date=date)
    
    if df is not None and len(df) > 0:
        # 创建集合并设置索引
        coll = DATABASE.get_collection('moneyflow_hsgt')
        coll.create_index([('date', 1)], unique=True)
        
        # 删除同一日期的旧数据
        try:
            delete_result = coll.delete_many({'date': date})
            print(f"删除旧数据: {delete_result.deleted_count} 条记录")
        except Exception as e:
            print(f"删除旧数据时出错: {e}")
        
        # 使用upsert方式插入新数据
        success_count = 0
        error_count = 0
        
        for _, row in df.iterrows():
            data = util_to_json_from_pandas(row.to_frame().T)[0]
            try:
                coll.replace_one(
                    {'date': date},
                    data,
                    upsert=True
                )
                success_count += 1
            except Exception as e:
                print(f"插入数据时出错: {e}")
                error_count += 1
        
        print(f'SUCCESS SAVE MONEYFLOW_HSGT DATA, Total: {success_count} records, Errors: {error_count}.')
    else:
        print('No MONEYFLOW_HSGT data found.')


def save_moneyflow_stock(date=None):
    """
    保存个股资金流向数据到数据库
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: None
    """
    if date is None:
        date = get_real_trade_date(now_time()[:10])
    
    print(f'==== NOW SAVE MONEYFLOW_STOCK DATA {date} ====')
    
    # 获取个股资金流向数据
    df = fetch_moneyflow_stock(date=date)
    
    if df is not None and len(df) > 0:
        # 创建集合并设置索引
        coll = DATABASE.get_collection('moneyflow_stock')
        coll.create_index([('date', 1), ('code', 1)], unique=True)
        
        # 删除同一日期的旧数据
        try:
            delete_result = coll.delete_many({'date': date})
            print(f"删除旧数据: {delete_result.deleted_count} 条记录")
        except Exception as e:
            print(f"删除旧数据时出错: {e}")
        
        # 使用upsert方式插入新数据
        success_count = 0
        error_count = 0
        
        for _, row in df.iterrows():
            data = util_to_json_from_pandas(row.to_frame().T)[0]
            try:
                coll.replace_one(
                    {'date': date, 'code': data['code']},
                    data,
                    upsert=True
                )
                success_count += 1
            except Exception as e:
                print(f"插入数据时出错 code={data['code']}: {e}")
                error_count += 1
        
        print(f'SUCCESS SAVE MONEYFLOW_STOCK DATA, Total: {success_count} records, Errors: {error_count}.')
    else:
        print('No MONEYFLOW_STOCK data found.')


def save_moneyflow_sector(date=None):
    """
    保存板块资金流向数据到数据库
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: None
    """
    if date is None:
        date = get_real_trade_date(now_time()[:10])
    
    print(f'==== NOW SAVE MONEYFLOW_SECTOR DATA {date} ====')
    
    # 获取板块资金流向数据
    df = fetch_moneyflow_sector(date=date)
    
    if df is not None and len(df) > 0:
        # 创建集合并设置索引
        coll = DATABASE.get_collection('moneyflow_sector')
        coll.create_index([('date', 1), ('name', 1)], unique=True)
        
        # 删除同一日期的旧数据
        try:
            delete_result = coll.delete_many({'date': date})
            print(f"删除旧数据: {delete_result.deleted_count} 条记录")
        except Exception as e:
            print(f"删除旧数据时出错: {e}")
        
        # 使用upsert方式插入新数据
        success_count = 0
        error_count = 0
        
        for _, row in df.iterrows():
            data = util_to_json_from_pandas(row.to_frame().T)[0]
            try:
                coll.replace_one(
                    {'date': date, 'name': data['name']},
                    data,
                    upsert=True
                )
                success_count += 1
            except Exception as e:
                print(f"插入数据时出错 name={data['name']}: {e}")
                error_count += 1
        
        print(f'SUCCESS SAVE MONEYFLOW_SECTOR DATA, Total: {success_count} records, Errors: {error_count}.')
    else:
        print('No MONEYFLOW_SECTOR data found.') 