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
        try:
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
        
        print(f'SUCCESS SAVE LIMIT_UP DATA, Total: {success_count} records, Errors: {error_count}.')
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
        try:
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
        
        print(f'SUCCESS SAVE LIMIT_DOWN DATA, Total: {success_count} records, Errors: {error_count}.')
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
        try:
            delete_result = coll.delete_many({'date': date})
            print(f"删除旧数据: {delete_result.deleted_count} 条记录")
        except Exception as e:
            print(f"删除旧数据时出错: {e}")
        
        # 使用upsert方式插入新数据，避免重复键错误
        success_count = 0
        error_count = 0
        
        for _, row in df.iterrows():
            data = util_to_json_from_pandas(row.to_frame().T)[0]
            # 确保所有必要的字段都存在
            required_fields = ['code', 'buyer', 'seller']
            missing_fields = [field for field in required_fields if field not in data or data[field] is None]
            
            if missing_fields:
                # 如果缺少任何必需字段，为其分配默认值
                for field in missing_fields:
                    data[field] = f"unknown_{field}" if field != 'code' else "000000"
                print(f"记录缺少必要字段 {', '.join(missing_fields)}，已使用默认值")
            
            try:
                coll.replace_one(
                    {'date': date, 'code': data['code'], 'buyer': data['buyer'], 'seller': data['seller']},
                    data,
                    upsert=True
                )
                success_count += 1
            except Exception as e:
                print(f"插入数据时出错 code={data.get('code', 'unknown')}: {e}")
                error_count += 1
        
        print(f'SUCCESS SAVE BLOCK_TRADE DATA, Total: {success_count} records, Errors: {error_count}.')
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
        try:
            delete_result = coll.delete_many({'date': date})
            print(f"删除旧数据: {delete_result.deleted_count} 条记录")
        except Exception as e:
            print(f"删除旧数据时出错: {e}")
        
        # 确保code字段符合要求（无前缀，统一格式）
        if 'code' in df.columns:
            df['code'] = df['code'].apply(lambda x: str(x).split('.')[-1] if isinstance(x, str) else str(x))
        
        # 使用upsert方式插入新数据，避免重复键错误
        success_count = 0
        error_count = 0
        
        for _, row in df.iterrows():
            try:
                data = util_to_json_from_pandas(row.to_frame().T)[0]
                # 确保date字段存在且符合格式
                if 'date' not in data or not data['date']:
                    data['date'] = date
                
                coll.replace_one(
                    {'date': data['date'], 'code': data['code']},
                    data,
                    upsert=True
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                code = row.get('code', 'unknown') if hasattr(row, 'get') else 'unknown'
                print(f"插入数据时出错 code={code}: {e}")
        
        print(f'SUCCESS SAVE MARGIN_DETAIL DATA, Total: {success_count} records, Errors: {error_count}.')
    else:
        print('No MARGIN_DETAIL data found.') 