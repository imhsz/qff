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
获取股票相关数据，并保存至数据库中。
根据操作系统设置定时任务，执行本文件。
"""

import pandas as pd
import numpy as np
import datetime
import time
from typing import Optional
from qff.price.fetch import fetch_price, fetch_price_parallel, fetch_stock_xdxr, fetch_stock_block
from qff.price.query import get_all_securities
from qff.tools.date import get_real_trade_date, get_next_trade_day, util_get_date_gap, get_trade_days, get_pre_trade_day
from qff.tools.mongo import DATABASE
from qff.tools.utils import util_to_json_from_pandas, util_code_tolist
from pymongo.errors import PyMongoError
import pymongo


def normalize_date(date_str, default_date=None, as_start=True):
    """
    日期格式自动兼容和修复函数
    
    :param date_str: 输入的日期字符串，可能是任何格式
    :param default_date: 当日期无效时的默认日期，默认为None（使用'1990-01-01'或今天）
    :param as_start: 是否作为开始日期，影响默认值选择
    :return: 标准化后的YYYY-MM-DD格式日期字符串
    """
    if default_date is None:
        # 默认起始日期为1990-01-01，结束日期为今天
        default_date = '1990-01-01' if as_start else datetime.date.today().strftime('%Y-%m-%d')
    
    # 处理None或空字符串
    if date_str is None or date_str == '':
        return default_date
    
    # 已经是标准格式的日期字符串
    if isinstance(date_str, str) and len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
        try:
            # 检查是否真的是有效日期
            datetime.datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
        except:
            pass
    
    # 尝试从各种格式转换
    try:
        # 处理datetime对象
        if isinstance(date_str, datetime.datetime) or isinstance(date_str, datetime.date):
            return date_str.strftime('%Y-%m-%d')
        
        # 处理字符串
        if isinstance(date_str, str):
            # 尝试不同的日期格式
            formats = ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d', '%Y.%m.%d']
            for fmt in formats:
                try:
                    return datetime.datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
                except:
                    continue
            
            # 尝试处理带时间的日期格式（取日期部分）
            if len(date_str) > 10:
                try:
                    # 尝试多种分隔符
                    for separator in [' ', 'T']:
                        if separator in date_str:
                            date_part = date_str.split(separator)[0]
                            for fmt in formats:
                                try:
                                    return datetime.datetime.strptime(date_part, fmt).strftime('%Y-%m-%d')
                                except:
                                    continue
                except:
                    pass
    except:
        pass
    
    # 所有尝试都失败，返回默认日期
    print(f"无法解析日期: {date_str}，使用默认值: {default_date}")
    return default_date


def ensure_valid_date_range(start_date, end_date, code=None):
    """
    确保日期范围合法，如果不合法，进行修正
    
    :param start_date: 开始日期
    :param end_date: 结束日期
    :param code: 股票代码（用于日志）
    :return: 修正后的(start_date, end_date)
    """
    # 标准化日期格式
    start_date = normalize_date(start_date, as_start=True)
    end_date = normalize_date(end_date, as_start=False)
    
    # 确保开始日期不晚于结束日期
    if start_date > end_date:
        msg = f"起始日期{start_date}晚于结束日期{end_date}"
        if code:
            msg += f", 股票代码: {code}"
        print(msg)
        # 互换日期对于历史数据可能不太合适，最好使用更合理的处理
        return end_date, end_date
    
    # 确保有有效交易日
    try:
        trade_days = get_trade_days(start_date, end_date)
        if not trade_days:
            msg = f"在{start_date}和{end_date}之间没有交易日"
            if code:
                msg += f", 股票代码: {code}"
            print(msg)
            # 使用结束日期作为单独日期
            return end_date, end_date
    except Exception as e:
        msg = f"获取交易日异常: {e}"
        if code:
            msg += f", 股票代码: {code}"
        print(msg)
        # 出错时使用今天作为安全的日期
        today = datetime.date.today().strftime('%Y-%m-%d')
        return today, today
    
    return start_date, end_date


def save_security_day(market='stock', security=None, parallel=True, batch_size=100, max_workers=5):
    """
    从通达信获取交易日数据，并保存到数据库中
    :param market: 市场类型，目前支持"stock/index/etf", 默认"stock".
    :param security: list or None, 证券列表
    :param parallel: 是否使用并行处理，默认True
    :param batch_size: 并行处理时每批处理的股票数量，默认100
    :param max_workers: 并行处理时的最大线程数，默认5
    """
    try:
        # 标准化结束日期
        end_date = normalize_date(now_time()[:10], as_start=False)
        # stock_list = fetch_stock_list(market).index.to_list()
        stock_list = get_all_securities(market=market) if security is None else security
        table_name = market + '_day'
        print(f'====  Now Saving {table_name.upper()} ====')
        coll = DATABASE.get_collection(table_name)
        coll.create_index([("code", 1), ("date", 1)], unique=True)
        coll.create_index("date")
        
        # 检查当前库中的最新日期
        try:
            latest_record = coll.find_one(sort=[('date', -1)])
            db_latest_date = latest_record['date'] if latest_record else '1990-01-01'
            print(f"数据库当前最新日期: {db_latest_date}")
            
            # 检查当前日期是否为交易日
            if not is_trade_day(end_date):
                print(f"今日 {end_date} 非交易日")
                # 检查库中最新日期是否已经是最近的交易日
                last_trade_day = get_real_trade_date(pd.Timestamp(end_date) - pd.Timedelta(days=1))
                if db_latest_date >= last_trade_day:
                    print(f"数据库中 {db_latest_date} 已是最新交易日数据 {last_trade_day}，无需更新")
                    return
            # 交易日检查 - 如果今天是交易日但尚未收盘，使用上一个交易日
            elif is_trade_day(end_date) and pd.Timestamp.now().hour < 15:
                # 如果当前是交易时段，使用上一个交易日作为结束日期
                last_trade_day = get_real_trade_date(pd.Timestamp(end_date) - pd.Timedelta(days=1))
                end_date = last_trade_day
                print(f"当前为交易时段，使用上一交易日 {end_date} 作为更新截止日期")
                # 如果库中数据已经更新到这一天，则无需再更新
                if db_latest_date >= end_date:
                    print(f"数据库中 {db_latest_date} 已是最新交易日数据 {end_date}，无需更新")
                    return
        except Exception as e:
            print(f"检查数据库最新日期时出错: {e}")
        
        if not parallel:
            # 原来的串行处理代码
            data_num = 0
            data_list = []
            start = time.perf_counter()
            total = len(stock_list)
            for item in range(total):
                code = stock_list[item]
                print_progress(item, total, start, code)
                
                try:
                    last_recode = coll.find_one({'code': code}, sort=[('date', -1)])
                    start_date = last_recode['date'] if last_recode else '1990-01-01'
                except TypeError or PyMongoError:
                    start_date = '1990-01-01'
                    last_recode = None
                
                # 日期格式规范化和校验
                start_date, end_date = ensure_valid_date_range(start_date, end_date, code)

                if start_date != end_date: # 避免处理同日期数据
                    try:
                        # start_date = get_next_trade_day(start_date)
                        # print('Trying updating {} from {}'.format(code, start_date))
                        data = fetch_price(code, freq='day', market=market, start=start_date)
                        if data is None or len(data) == 0:
                            # 如果每日更新时遇见连续停牌股票，则fetch_price返回空，
                            # 如果start_date不为'1990-01-01'
                            # 需要将数据库中最后一条记录的收盘价，用于生成停牌日数据
                            if start_date > '1990-01-01':
                                # 确保交易日数据有效
                                trade_days = get_trade_days(start_date, end_date)
                                if not trade_days:
                                    print(f'股票{code}：{start_date}到{end_date}之间无交易日')
                                    continue
                                    
                                data = pd.DataFrame(
                                    index=pd.Index(trade_days, name='date'),
                                    columns=['code', 'open', 'close', 'low', 'high', 'vol', 'amount']
                                )
                                data['code'] = code
                                data[['open', 'close', 'high', 'low']] = last_recode['close'] if last_recode else 0
                                data[['vol', 'amount']] = 0
                            else:
                                print('股票{}无历史日数据！可能是未上市新股!'.format(code))
                                continue

                        else:

                            data = data.loc[:end_date]
                            if start_date == '1990-01-01':
                                start_date = data.index[0]   # fix bug like :updating 603125 data error!
                                                             # Exception:'1990-01-01'

                            trade_days = get_trade_days(start_date, end_date)

                            if len(trade_days) > len(data):
                                # 存在停牌日数据
                                dl_df = pd.DataFrame(index=pd.Index(trade_days, name='date'))
                                data = dl_df.join(data).sort_index()

                                data.code.fillna(value=code, inplace=True)

                                if start_date in data.index: # 检查 start_date 是否存在于索引中
                                    if pd.isna(data.loc[start_date, 'close']) and last_recode is not None:
                                        data.loc[start_date, 'close'] = last_recode['close']

                                data.close.fillna(method='ffill', inplace=True)

                                data = data.fillna(method='bfill', axis=1)
                                data.vol.fillna(value=0, inplace=True)
                                data.amount.fillna(value=0, inplace=True)
                                data = data.fillna(method='ffill', axis=1)

                        if start_date > '1990-01-01':
                            if start_date in data.index: # 检查 start_date 是否存在于索引中
                                data.drop(start_date, inplace=True)

                        data.reset_index(inplace=True)
                        data_num += len(data)
                        data_list.append(data)
                        if data_num > 2000:
                            data_batch = pd.concat(data_list)
                            data_num = 0
                            data_list.clear()
                            try:
                                # 转换为JSON文档列表
                                docs = util_to_json_from_pandas(data_batch)
                                # 使用批量操作，支持替换已存在的文档
                                bulk_ops = []
                                for doc in docs:
                                    # 创建upsert操作，如果记录存在则替换，不存在则插入
                                    bulk_ops.append(
                                        pymongo.UpdateOne(
                                            {"code": doc["code"], "date": doc["date"]},
                                            {"$set": doc},
                                            upsert=True
                                        )
                                    )
                                # 执行批量操作
                                if bulk_ops:
                                    result = coll.bulk_write(bulk_ops, ordered=False)
                                    print(f"保存了 {result.upserted_count} 条新记录, 更新了 {result.modified_count} 条已有记录")
                            except pymongo.errors.BulkWriteError as bwe:
                                # 提取成功插入的文档数量信息
                                result = bwe.details
                                print(f"部分文档插入成功: 插入 {result.get('nInserted', 0)} 条, "
                                      f"更新 {result.get('nMatched', 0)} 条, "
                                      f"有 {len(result.get('writeErrors', []))} 条错误")
                            except Exception as e:
                                print(f"保存数据时出错: {str(e)}")
                        print(f"处理了 {len(data_batch)} 条记录")

                    except Exception as e:
                        print(f'updating {code} data error!')
                        print('Exception:' + str(e))

            if data_num > 0:
                data = pd.concat(data_list)
                try:
                    # 转换为JSON文档列表
                    docs = util_to_json_from_pandas(data)
                    # 使用批量操作，支持替换已存在的文档
                    bulk_ops = []
                    for doc in docs:
                        # 创建upsert操作，如果记录存在则替换，不存在则插入
                        bulk_ops.append(
                            pymongo.UpdateOne(
                                {"code": doc["code"], "date": doc["date"]},
                                {"$set": doc},
                                upsert=True
                            )
                        )
                    # 执行批量操作
                    if bulk_ops:
                        result = coll.bulk_write(bulk_ops, ordered=False)
                        print(f"保存了 {result.upserted_count} 条新记录, 更新了 {result.modified_count} 条已有记录")
                except Exception as e:
                    print(f"保存数据时出错: {str(e)}")
        else:
            # 并行处理代码
            start = time.perf_counter()
            total = len(stock_list)
            
            # 获取每只股票的最后一条记录日期
            code_start_dates = {}
            code_last_records = {}
            need_update_codes = []
            
            print("正在检查需要更新的股票...")
            # 获取今日前最近的交易日日期作为最新日期标准
            latest_trade_day = get_real_trade_date(pd.Timestamp(end_date) - pd.Timedelta(days=1))
            print(f"最近交易日: {latest_trade_day}")
            
            # 确定最新标准
            if is_trade_day(end_date):
                now = pd.Timestamp.now()
                # 交易日已收盘，使用今日作为标准
                if now.hour >= 15:
                    latest_trade_day = end_date
                    print(f"今日 {end_date} 为交易日且已收盘，使用今日作为最新标准")
                else:
                    # 交易时段内，需要区别对待
                    today_data_needed = True
                    print(f"今日 {end_date} 为交易日且正在交易中，需要获取盘中数据")
            
            # 优化检查逻辑，使用批量查询提高效率
            stock_batches = [stock_list[i:i+1000] for i in range(0, len(stock_list), 1000)]
            total_checked = 0
            total_latest = 0
            today_codes = []  # 专门记录需要更新今日盘中数据的股票
            
            for batch in stock_batches:
                # 使用批量查询优化性能
                query_result = list(coll.find(
                    {'code': {'$in': batch}, 'type': freq},
                    {'_id': 0, 'code': 1, 'datetime': 1}
                ).sort([('code', 1), ('datetime', -1)]))
                
                # 处理查询结果，获取每只股票的最新记录
                codes_processed = set()
                for record in query_result:
                    code = record['code']
                    if code not in codes_processed:
                        codes_processed.add(code)
                        last_datetime = record['datetime']
                        last_date = last_datetime[:10]  # 提取日期部分
                        
                        # 根据不同情况判断是否需要更新
                        if is_trade_day(end_date) and pd.Timestamp.now().hour < 15:
                            # 交易日盘中 - 检查是否需要获取实时数据
                            if last_date == end_date:
                                # 已有今日数据，检查是否为最近30分钟
                                last_time = pd.Timestamp(last_datetime)
                                if (pd.Timestamp.now() - last_time).total_seconds() > 1800:  # 30分钟
                                    # 数据不是最新的，需要更新今日盘中数据
                                    today_codes.append(code)
                                    code_start_dates[code] = end_date
                                else:
                                    # 数据很新，不需要更新
                                    total_latest += 1
                            elif last_date >= latest_trade_day:
                                # 有昨日数据，需要获取今日盘中数据
                                today_codes.append(code)
                                code_start_dates[code] = end_date
                            else:
                                # 数据较旧，需要常规更新
                                need_update_codes.append(code)
                                next_date = get_next_trade_day(last_date)
                                code_start_dates[code] = next_date
                        else:
                            # 非交易时段或已收盘 - 只需检查是否为最新交易日
                            if last_date >= latest_trade_day:
                                # 已有最新数据
                                total_latest += 1
                            else:
                                # 数据不是最新的，需要更新
                                need_update_codes.append(code)
                                next_date = get_next_trade_day(last_date)
                                code_start_dates[code] = next_date
                
                # 处理未在数据库找到记录的股票
                for code in batch:
                    if code not in codes_processed:
                        code_start_dates[code] = '1990-01-01'
                        need_update_codes.append(code)
                
                total_checked += len(batch)
                print(f"已检查 {total_checked}/{len(stock_list)} 只股票，已是最新的有 {total_latest} 只")
            
            # 合并需要常规更新和需要获取盘中数据的股票
            if today_codes:
                print(f"有 {len(today_codes)} 只股票需要更新今日盘中数据")
                need_update_codes.extend(today_codes)
            
            total_stocks = len(need_update_codes)
            if total_stocks == 0:
                print(f"所有 {len(stock_list)} 只股票的 {freq} 数据均为最新（截至 {latest_trade_day}），无需更新")
                return
                
            print(f"筛选出 {total_stocks}/{len(stock_list)} 只需要更新的股票（最新标准: {latest_trade_day}）")
            
            # 增加成功失败统计
            success_count = 0
            fail_count = 0
            total_processed = 0
            total_records = 0
            
            # 分批处理
            for batch_start in range(0, len(need_update_codes), batch_size):
                batch_codes = need_update_codes[batch_start:batch_start+batch_size]
                current_batch = batch_start // batch_size + 1
                total_batches = (len(need_update_codes) + batch_size - 1) // batch_size
                print(f"正在并行处理第 {current_batch}/{total_batches} 批 (每批{batch_size}只)，当前批 {len(batch_codes)} 只，总计 {total_stocks} 只股票")
                
                # 并行获取数据
                results = fetch_price_parallel(batch_codes, freq='day', market=market, 
                                              start=None, max_workers=max_workers)
                
                # 处理和保存数据
                data_list = []
                batch_success = 0
                batch_fail = 0
                for code in batch_codes:
                    print_progress(batch_start + batch_codes.index(code), total, start, code)
                    code = str(code)[-6:]  # 统一格式
                    try:
                        start_date = code_start_dates[code]
                        last_recode = code_last_records[code]
                        data = None
                        # 增加重试机制
                        for retry in range(3):
                            try:
                                if code in results:
                                    data = results[code]
                                    break
                            except Exception as e:
                                if retry == 2:
                                    print(f'获取 {code} 数据失败: {e}')
                                time.sleep(2)
                        if data is not None and len(data) > 0:
                            data = data.loc[:end_date]
                            if start_date == '1990-01-01':
                                start_date = data.index[0] if len(data) > 0 else start_date
                                
                            # 确保交易日数据有效
                            trade_days = get_trade_days(start_date, end_date)
                            if not trade_days:
                                print(f'股票{code}：{start_date}到{end_date}之间无交易日')
                                continue
                                
                            if len(trade_days) > len(data):
                                dl_df = pd.DataFrame(index=pd.Index(trade_days, name='date'))
                                data = dl_df.join(data).sort_index()
                                data.code.fillna(value=code, inplace=True)
                                if start_date in data.index:
                                    if pd.isna(data.loc[start_date, 'close']) and last_recode is not None:
                                        data.loc[start_date, 'close'] = last_recode['close']
                                data.close.fillna(method='ffill', inplace=True)
                                data = data.fillna(method='bfill', axis=1)
                                data.vol.fillna(value=0, inplace=True)
                                data.amount.fillna(value=0, inplace=True)
                                data = data.fillna(method='ffill', axis=1)
                            if start_date > '1990-01-01':
                                if start_date in data.index:
                                    data.drop(start_date, inplace=True)
                            data.reset_index(inplace=True)
                            data_list.append(data)
                            batch_success += 1
                            success_count += 1
                        elif start_date > '1990-01-01' and last_recode is not None:
                            # 确保交易日数据有效
                            trade_days = get_trade_days(start_date, end_date)
                            if not trade_days:
                                print(f'股票{code}：{start_date}到{end_date}之间无交易日')
                                continue
                                
                            data = pd.DataFrame(
                                index=pd.Index(trade_days, name='date'),
                                columns=['code', 'open', 'close', 'low', 'high', 'vol', 'amount']
                            )
                            data['code'] = code
                            data[['open', 'close', 'high', 'low']] = last_recode['close']
                            data[['vol', 'amount']] = 0
                            if start_date in data.index:
                                data.drop(start_date, inplace=True)
                            data.reset_index(inplace=True)
                            data_list.append(data)
                            batch_success += 1
                            success_count += 1
                        else:
                            print(f'股票{code}无法获取数据或无历史日数据！')
                            batch_fail += 1
                            fail_count += 1
                    except Exception as e:
                        print(f'updating {code} data error!')
                        print('Exception:' + str(e))
                        batch_fail += 1
                        fail_count += 1
                # 保存这一批数据
                if data_list:
                    try:
                        data_batch = pd.concat(data_list)
                        if len(data_batch) > 0:
                            try:
                                # 转换为JSON文档列表
                                docs = util_to_json_from_pandas(data_batch)
                                # 使用批量操作，支持替换已存在的文档
                                bulk_ops = []
                                for doc in docs:
                                    # 创建upsert操作，如果记录存在则替换，不存在则插入
                                    bulk_ops.append(
                                        pymongo.UpdateOne(
                                            {"code": doc["code"], "date": doc["date"]},
                                            {"$set": doc},
                                            upsert=True
                                        )
                                    )
                                # 执行批量操作
                                if bulk_ops:
                                    result = coll.bulk_write(bulk_ops, ordered=False)
                                    print(f"保存了 {result.upserted_count} 条新记录, 更新了 {result.modified_count} 条已有记录")
                            except pymongo.errors.BulkWriteError as bwe:
                                # 提取成功插入的文档数量信息
                                result = bwe.details
                                print(f"部分文档插入成功: 插入 {result.get('nInserted', 0)} 条, "
                                      f"更新 {result.get('nMatched', 0)} 条, "
                                      f"有 {len(result.get('writeErrors', []))} 条错误")
                            except Exception as e:
                                print(f"保存数据时出错: {str(e)}")
                        print(f"处理了 {len(data_batch)} 条记录")
                        total_records += len(data_batch)
                    except Exception as e:
                        print(f"保存数据时出错: {str(e)}")
                
                # 批次统计
                total_processed += batch_success + batch_fail
                print(f"本批次: 成功 {batch_success}/{len(batch_codes)} 只, 失败 {batch_fail}/{len(batch_codes)} 只")
                print(f"累计进度: {total_processed}/{total_stocks} 只, 成功率: {success_count/total_processed*100:.1f}%")

                # 若本批全部失败，降级为单只重试
                if len(data_list) == 0:
                    print(f"批次中所有股票获取失败，降级为单只串行重试...")
                    for code in batch_codes:
                        code = str(code)[-6:]
                        try:
                            start_date = code_start_dates[code]
                            last_recode = code_last_records[code]
                            # 不再延时，立即重试
                            for retry in range(3):
                                try:
                                    data = fetch_price(code, freq='day', market=market, start=start_date)
                                    if data is not None and len(data) > 0:
                                        break
                                except Exception as e:
                                    if retry == 2:
                                        print(f'降级单只重试获取 {code} 数据失败: {e}')
                            if data is not None and len(data) > 0:
                                data = data.loc[:end_date]
                                if start_date == '1990-01-01':
                                    start_date = data.index[0] if len(data) > 0 else start_date
                                trade_days = get_trade_days(start_date, end_date)
                                if len(trade_days) > len(data):
                                    dl_df = pd.DataFrame(index=pd.Index(trade_days, name='date'))
                                    data = dl_df.join(data).sort_index()
                                    data.code.fillna(value=code, inplace=True)
                                    if start_date in data.index:
                                        if pd.isna(data.loc[start_date, 'close']) and last_recode is not None:
                                            data.loc[start_date, 'close'] = last_recode['close']
                                    data.close.fillna(method='ffill', inplace=True)
                                    data = data.fillna(method='bfill', axis=1)
                                    data.vol.fillna(value=0, inplace=True)
                                    data.amount.fillna(value=0, inplace=True)
                                    data = data.fillna(method='ffill', axis=1)
                                if start_date > '1990-01-01':
                                    if start_date in data.index:
                                        data.drop(start_date, inplace=True)
                                    data.reset_index(inplace=True)
                                    data_list.append(data)
                                    # 统计成功恢复
                                    success_count += 1
                                    batch_success += 1
                                    batch_fail -= 1
                                    fail_count -= 1
                                    print(f"降级模式成功恢复股票 {code} 的数据")
                        except Exception as e:
                            print(f'降级单只重试 {code} 依然失败: {e}')
        print(f'\n==== SUCCESS SAVE {table_name.upper()} DATA! ====')
        # 总体统计
        print(f"\n==== 统计信息 ====")
        print(f"总计处理: {total_processed} 只股票")
        print(f"成功获取: {success_count} 只 ({success_count/total_processed*100:.1f}%)")
        print(f"失败股票: {fail_count} 只 ({fail_count/total_processed*100:.1f}%)")
        print(f"入库记录: {total_records} 条")
        print(f"==== 处理完成 ====\n")
    except EOFError:
        time.sleep(1)
    except Exception as e:
        print(" \nError save_security_day exception!")
        print(str(e))
        import traceback
        print(traceback.format_exc())


def save_security_min(market='stock', freq='1min', security=None, parallel=True, batch_size=100, max_workers=5):
    """
    从通达信获取分钟数据，并保存到数据库中
    :param market: 市场类型，目前支持"stock/index/etf", 默认"stock".
    :param freq: 单位时间长度, 现在支持，1min/5min/15min/30min/60min
    :param security: list or None, 证券列表
    :param parallel: 是否使用并行处理，默认True
    :param batch_size: 并行处理时每批处理的股票数量，默认100
    :param max_workers: 并行处理时的最大线程数，默认5
    """
    try:
        end_date = normalize_date(now_time()[:10], as_start=False)
        stock_list = get_all_securities(market=market) if security is None else security
        print(f"==== Now Saving {market.upper()}_{freq.upper()} ====")
        
        table_name = market + '_min'
        coll = DATABASE.get_collection(table_name)
        coll.create_index([("type", 1), ("code", 1), ("datetime", 1)], unique=True)
        coll.create_index("datetime")
        
        # 检查当前库中的最新日期
        try:
            # 获取该频率下的最新记录日期
            latest_record = coll.find_one({"type": freq}, sort=[('datetime', -1)])
            db_latest_datetime = latest_record['datetime'] if latest_record else '1990-01-01 00:00:00'
            db_latest_date = db_latest_datetime[:10]  # 只取日期部分
            print(f"数据库 {freq} 当前最新日期: {db_latest_date}")
            
            # 检查当前日期是否为交易日
            if not is_trade_day(end_date):
                print(f"今日 {end_date} 非交易日")
                # 检查库中最新日期是否已经是最近的交易日
                last_trade_day = get_real_trade_date(pd.Timestamp(end_date) - pd.Timedelta(days=1))
                if db_latest_date >= last_trade_day:
                    print(f"数据库中 {db_latest_date} 已是最新交易日数据 {last_trade_day}，无需更新")
                    return
                    
            # 交易日检查 - 如果今天是交易日但尚未收盘
            elif is_trade_day(end_date):
                # 当前时间
                now = pd.Timestamp.now()
                # 如果是交易时段
                if now.hour < 15:  # 交易日但未收盘
                    # 如果库中最新日期就是昨天的交易日，无需更新
                    last_trade_day = get_real_trade_date(pd.Timestamp(end_date) - pd.Timedelta(days=1))
                    if db_latest_date >= last_trade_day:
                        # 检查是否已经有当天的盘中数据
                        today_data = coll.find_one({"type": freq, "datetime": {"$regex": f"^{end_date}"}})
                        if today_data:
                            # 已经有当天数据，检查最后更新时间与当前时间
                            latest_today = coll.find_one(
                                {"type": freq, "datetime": {"$regex": f"^{end_date}"}}, 
                                sort=[('datetime', -1)]
                            )
                            latest_time = pd.Timestamp(latest_today['datetime'])
                            # 如果最后更新时间在30分钟内，认为是最新数据
                            if (now - latest_time).total_seconds() < 1800:  # 30分钟
                                print(f"数据库中已有最新盘中数据，最后更新时间: {latest_today['datetime']}，无需更新")
                                return
                            else:
                                print(f"数据库中盘中数据需要更新，最后更新时间: {latest_today['datetime']}")
                        else:
                            print(f"数据库中无当天盘中数据，需要更新")
                    else:
                        print(f"数据库中无昨日交易数据，需要更新")
                # 收盘后
                else:
                    # 如果库中最新日期就是今天，无需更新
                    if db_latest_date >= end_date:
                        print(f"数据库中 {db_latest_date} 已是今日收盘后数据，无需更新")
                        return
        except Exception as e:
            print(f"检查数据库最新日期时出错: {e}")
        
        if not parallel:
            # 原来的串行处理代码
            data_num = 0
            data_list = []

            start = time.perf_counter()
            total = len(stock_list)
            for item in range(total):
                code = stock_list[item]
                print_progress(item, total, start, code)

                try:
                    start_date = coll.find_one({'type': freq, 'code': code}, sort=[('datetime', -1)])['datetime']
                    if start_date is None or start_date == 'nan':
                        raise TypeError
                except TypeError or PyMongoError:
                    start_date = '1990-01-01'

                if start_date != end_date:
                    try:
                        start_date = get_next_trade_day(start_date)
                        # print('Trying updating {} {} data from {}'.format(code, freq, start_date))
                        data = fetch_price(code, freq=freq, market=market, start=start_date)
                        if data is None or len(data) == 0:
                            continue
                        data = data.loc[:end_date]
                        data.reset_index(inplace=True)
                        data['type'] = freq

                        data_num += len(data)
                        data_list.append(data)
                        if data_num > 2000:
                            data = pd.concat(data_list)
                            data_num = 0
                            data_list.clear()
                            try:
                                # 转换为JSON文档列表
                                docs = util_to_json_from_pandas(data)
                                # 使用批量操作，支持替换已存在的文档
                                bulk_ops = []
                                for doc in docs:
                                    # 创建upsert操作，如果记录存在则替换，不存在则插入
                                    bulk_ops.append(
                                        pymongo.UpdateOne(
                                            {"type": doc["type"], "code": doc["code"], "datetime": doc["datetime"]},
                                            {"$set": doc},
                                            upsert=True
                                        )
                                    )
                                # 执行批量操作
                                if bulk_ops:
                                    result = coll.bulk_write(bulk_ops, ordered=False)
                                    print(f"保存了 {result.upserted_count} 条新记录, 更新了 {result.modified_count} 条已有记录")
                            except Exception as e:
                                print(f"保存数据时出错: {str(e)}")

                    except Exception as e:
                        print(f'\nupdating {code} {freq} data error!')
                        print('Exception:' + str(e))
            if data_num > 0:
                data = pd.concat(data_list)
                try:
                    # 转换为JSON文档列表
                    docs = util_to_json_from_pandas(data)
                    # 使用批量操作，支持替换已存在的文档
                    bulk_ops = []
                    for doc in docs:
                        # 创建upsert操作，如果记录存在则替换，不存在则插入
                        bulk_ops.append(
                            pymongo.UpdateOne(
                                {"type": doc["type"], "code": doc["code"], "datetime": doc["datetime"]},
                                {"$set": doc},
                                upsert=True
                            )
                        )
                    # 执行批量操作
                    if bulk_ops:
                        result = coll.bulk_write(bulk_ops, ordered=False)
                        print(f"保存了 {result.upserted_count} 条新记录, 更新了 {result.modified_count} 条已有记录")
                except Exception as e:
                    print(f"保存数据时出错: {str(e)}")
        else:
            # 并行处理代码
            start = time.perf_counter()
            total = len(stock_list)
            
            # 获取每只股票的最后一条记录日期
            code_start_dates = {}
            need_update_codes = []
            
            print("正在检查需要更新的股票...")
            # 获取今日前最近的交易日日期作为最新日期标准
            latest_trade_day = get_real_trade_date(pd.Timestamp(end_date) - pd.Timedelta(days=1))
            print(f"最近交易日: {latest_trade_day}")
            
            # 确定最新标准
            if is_trade_day(end_date):
                now = pd.Timestamp.now()
                # 交易日已收盘，使用今日作为标准
                if now.hour >= 15:
                    latest_trade_day = end_date
                    print(f"今日 {end_date} 为交易日且已收盘，使用今日作为最新标准")
                else:
                    # 交易时段内，需要区别对待
                    today_data_needed = True
                    print(f"今日 {end_date} 为交易日且正在交易中，需要获取盘中数据")
            
            # 优化检查逻辑，使用批量查询提高效率
            stock_batches = [stock_list[i:i+1000] for i in range(0, len(stock_list), 1000)]
            total_checked = 0
            total_latest = 0
            today_codes = []  # 专门记录需要更新今日盘中数据的股票
            
            for batch in stock_batches:
                # 使用批量查询优化性能
                query_result = list(coll.find(
                    {'code': {'$in': batch}, 'type': freq},
                    {'_id': 0, 'code': 1, 'datetime': 1}
                ).sort([('code', 1), ('datetime', -1)]))
                
                # 处理查询结果，获取每只股票的最新记录
                codes_processed = set()
                for record in query_result:
                    code = record['code']
                    if code not in codes_processed:
                        codes_processed.add(code)
                        last_datetime = record['datetime']
                        last_date = last_datetime[:10]  # 提取日期部分
                        
                        # 根据不同情况判断是否需要更新
                        if is_trade_day(end_date) and pd.Timestamp.now().hour < 15:
                            # 交易日盘中 - 检查是否需要获取实时数据
                            if last_date == end_date:
                                # 已有今日数据，检查是否为最近30分钟
                                last_time = pd.Timestamp(last_datetime)
                                if (pd.Timestamp.now() - last_time).total_seconds() > 1800:  # 30分钟
                                    # 数据不是最新的，需要更新今日盘中数据
                                    today_codes.append(code)
                                    code_start_dates[code] = end_date
                                else:
                                    # 数据很新，不需要更新
                                    total_latest += 1
                            elif last_date >= latest_trade_day:
                                # 有昨日数据，需要获取今日盘中数据
                                today_codes.append(code)
                                code_start_dates[code] = end_date
                            else:
                                # 数据较旧，需要常规更新
                                need_update_codes.append(code)
                                next_date = get_next_trade_day(last_date)
                                code_start_dates[code] = next_date
                        else:
                            # 非交易时段或已收盘 - 只需检查是否为最新交易日
                            if last_date >= latest_trade_day:
                                # 已有最新数据
                                total_latest += 1
                            else:
                                # 数据不是最新的，需要更新
                                need_update_codes.append(code)
                                next_date = get_next_trade_day(last_date)
                                code_start_dates[code] = next_date
                
                # 处理未在数据库找到记录的股票
                for code in batch:
                    if code not in codes_processed:
                        code_start_dates[code] = '1990-01-01'
                        need_update_codes.append(code)
                
                total_checked += len(batch)
                print(f"已检查 {total_checked}/{len(stock_list)} 只股票，已是最新的有 {total_latest} 只")
            
            # 合并需要常规更新和需要获取盘中数据的股票
            if today_codes:
                print(f"有 {len(today_codes)} 只股票需要更新今日盘中数据")
                need_update_codes.extend(today_codes)
            
            total_stocks = len(need_update_codes)
            if total_stocks == 0:
                print(f"所有 {len(stock_list)} 只股票的 {freq} 数据均为最新（截至 {latest_trade_day}），无需更新")
                return
                
            print(f"筛选出 {total_stocks}/{len(stock_list)} 只需要更新的股票（最新标准: {latest_trade_day}）")
            
            # 增加成功失败统计
            success_count = 0
            fail_count = 0
            total_processed = 0
            total_records = 0
            
            # 分批处理
            for batch_start in range(0, len(need_update_codes), batch_size):
                batch_codes = need_update_codes[batch_start:batch_start+batch_size]
                current_batch = batch_start // batch_size + 1
                total_batches = (len(need_update_codes) + batch_size - 1) // batch_size
                print(f"正在并行处理第 {current_batch}/{total_batches} 批，共 {len(batch_codes)} 只股票")
                
                # 并行获取数据
                results = fetch_price_parallel(batch_codes, freq=freq, market=market, 
                                              max_workers=max_workers)
                
                # 处理和保存数据
                data_list = []
                batch_success = 0
                batch_fail = 0
                
                for code in batch_codes:
                    print_progress(batch_start + batch_codes.index(code), total_stocks, start, code)
                    
                    try:
                        start_date = code_start_dates.get(code, '1990-01-01')
                        if start_date == '1990-01-01':
                            start_date = None  # 对于新股票直接获取全部数据
                        
                        if code in results and results[code] is not None and len(results[code]) > 0:
                            data = results[code]
                            data = data.loc[:end_date]
                            data.reset_index(inplace=True)
                            data['type'] = freq
                            data_list.append(data)
                            batch_success += 1
                            success_count += 1
                        else:
                            # 数据获取失败，记录下来
                            batch_fail += 1
                            fail_count += 1
                            print(f"\n警告: 获取 {code} 的{freq}数据失败或返回为空")
                    
                    except Exception as e:
                        batch_fail += 1
                        fail_count += 1
                        print(f'\nupdating {code} {freq} data error!')
                        print('Exception:' + str(e))
                
                # 保存这一批数据
                if data_list:
                    try:
                        data_batch = pd.concat(data_list)
                        if len(data_batch) > 0:
                            try:
                                # 转换为JSON文档列表
                                docs = util_to_json_from_pandas(data_batch)
                                # 使用批量操作，支持替换已存在的文档
                                bulk_ops = []
                                for doc in docs:
                                    # 创建upsert操作，如果记录存在则替换，不存在则插入
                                    bulk_ops.append(
                                        pymongo.UpdateOne(
                                            {"type": doc["type"], "code": doc["code"], "datetime": doc["datetime"]},
                                            {"$set": doc},
                                            upsert=True
                                        )
                                    )
                                # 执行批量操作
                                if bulk_ops:
                                    result = coll.bulk_write(bulk_ops, ordered=False)
                                    print(f"保存了 {result.upserted_count} 条新记录, 更新了 {result.modified_count} 条已有记录")
                            except pymongo.errors.BulkWriteError as bwe:
                                # 提取成功插入的文档数量信息
                                result = bwe.details
                                print(f"部分文档插入成功: 插入 {result.get('nInserted', 0)} 条, "
                                      f"更新 {result.get('nMatched', 0)} 条, "
                                      f"有 {len(result.get('writeErrors', []))} 条错误")
                            except Exception as e:
                                print(f"保存数据时出错: {str(e)}")
                        print(f"处理了 {len(data_batch)} 条记录")
                    except Exception as e:
                        print(f"保存数据时出错: {str(e)}")
                
                # 批次统计
                total_processed += batch_success + batch_fail
                print(f"本批次: 成功 {batch_success}/{len(batch_codes)} 只, 失败 {batch_fail}/{len(batch_codes)} 只")
                print(f"累计进度: {total_processed}/{total_stocks} 只, 成功率: {success_count/total_processed*100 if total_processed > 0 else 0:.1f}%")

        print(f'\n==== SUCCESS SAVE {table_name.upper()} {freq} DATA! ====')
    except EOFError:
        time.sleep(1)
    except Exception as e:
        print(f"\nError save_security_min exception!:{market.upper()} {freq.upper()} DATA")
        print(e)
        import traceback
        print(traceback.format_exc())


def save_stock_xdxr(security=None):
    """
    保存除权除息数据，并计算股票最新前复权系数，保存至数据库中
    """

    coll_xdxr = DATABASE.get_collection('stock_xdxr')
    coll_xdxr.create_index([('code', 1), ('date', 1), ('category', 1)], unique=True)

    coll_adj = DATABASE.get_collection('stock_adj')
    coll_adj.create_index([('code', 1), ('date', 1)], unique=True)

    print('==== NOW SAVE STOCK_XDXR DATA =====')
    if security is None:
        stock_list = get_all_securities()
    else:
        stock_list = util_code_tolist(security)
    start = time.perf_counter()
    total = len(stock_list)

    for item in range(total):
        code = stock_list[item]
        print_progress(item, total, start, code)
        try:

            xdxr = fetch_stock_xdxr(str(code))
            if xdxr is None:
                time.sleep(1)
                xdxr = fetch_stock_xdxr(str(code))
                if xdxr is None:
                    # print(f"\n {code}:无复权信息！")
                    continue
            new_count = len(xdxr)
            db_count = coll_xdxr.count_documents({'code': code})

            if new_count != db_count:

                # 出现数据库记录数量比实时获取的数据多，则删除
                coll_xdxr.delete_many({'code': code})

                # try:
                coll_xdxr.insert_many(util_to_json_from_pandas(xdxr))
                # except PyMongoError:
                #     pass

                # 判断更新的xdxr数据中是否有除权除息类型
                if new_count > db_count:
                    xdxr_new = xdxr.iloc[db_count - new_count:]
                    if 1 not in xdxr_new['category'].to_list():
                        continue

                # 计算并更新复权系数
                cursor = DATABASE.stock_day.find({'code': code}, {'_id': 0, 'date': 1, 'code': 1, 'close': 1})
                data = pd.DataFrame([item for item in cursor])
                if len(data) == 0:
                    continue
                data = data.set_index('date')

                qfq = calc_qfq_cof(data, xdxr)  # 计算前复权系数
                if qfq is None:
                    print(f"\n复权系数均为1，忽略！{code}")
                    continue
                hfq = calc_hfq_cof(qfq, xdxr)  # 计算后复权系数
                hfq = hfq.reset_index()
                adjdata = util_to_json_from_pandas(hfq.loc[:, ['date', 'code', 'qfq', 'hfq']])
                coll_adj.delete_many({'code': code})
                coll_adj.insert_many(adjdata)

        except Exception as e:
            print("\nError save_stock_xdxr exception!")

            print(e)

    print('\n==== SUCCESS SAVE STOCK_XDXR DATA! ====')


def save_security_block():
    """
    从通达信获取股票板块信息，并保存到数据库中
    :return: None
    """
    try:
        table_name = 'stock_block'
        DATABASE.drop_collection(table_name)
        coll = DATABASE.get_collection(table_name)
        coll.create_index('code')
        print(f'==== Now Saving {table_name.upper()} ====')
        data = fetch_stock_block()
        if data is not None:
            coll.insert_many(util_to_json_from_pandas(data))
        print(f'SUCCESS SAVE {table_name.upper()} ^_^')

    except Exception as e:
        print(" Error save_security_info exception!")
        print(e)


##########################################################################################################
def now_time():
    """获取当前交易日结束时间，如 '2025-05-05 15:00:00'"""
    today = datetime.date.today()
    now = datetime.datetime.now()
    
    # 检查系统时间是否合理
    if today.year > 2025:  # 可能是系统日期设置错误
        print("警告: 系统日期可能不正确! 使用硬编码的当前日期")
        today = datetime.date(2025, 5, 5)  # 使用硬编码的当前日期作为备选
    
    if now.hour < 15:  # 当日收盘前
        trade_date = get_real_trade_date(str(today - datetime.timedelta(days=1)))
    else:  # 当日收盘后
        trade_date = get_real_trade_date(str(today))
        
    # 确保不会返回未来日期
    tomorrow = str(today + datetime.timedelta(days=1))
    if trade_date > tomorrow:
        print(f"警告: 交易日期 {trade_date} 超过明天 {tomorrow}，将使用今天的日期")
        trade_date = str(today)
        
    return trade_date + ' 15:00:00'


def print_progress(item, total, start, code):
    finsh = "▓" * int(item * 100 / total)
    need_do = "-" * int((total - item) * 100 / total)
    progress = (item / total) * 100
    dur = time.perf_counter() - start
    tt = dur / (item + 1) * total
    print("\r{:^3.0f}%[{}->{}]{:.2f}s|{:.2f}s ({})".format(progress, finsh, need_do, dur, tt, code), end="")


def calc_qfq_cof(bfq: pd.DataFrame, xdxr: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    计算前复权系数
    :param bfq: 被复权股票ochl数据
    :param xdxr: 股票对应的xdxr数据
    :return: 在bfq数据后面增加一列 'adj' 保存对应的前复权系数，返回空表示复权系数均为1
    """
    info = xdxr.query('category==1')
    info = info.loc[bfq.index[1]:bfq.index[-1]]  # 注意取index[1],复权系数的变化是除权日上一个交易日

    if len(info) > 0:
        bfq['qfq'] = np.NAN
        cof = 1
        for i in range(len(info)-1, -1, -1):  # 前复权倒序
            r = info.iloc[i]
            _date = util_get_date_gap(info.index[i], -1)  #

            try:
                raw_close = bfq.loc[_date, 'close']  # 原始收盘价
            except KeyError:
                while _date not in bfq.index.to_list():
                    _date = util_get_date_gap(_date, -1)
                raw_close = bfq.loc[_date, 'close']

            fq_close = (raw_close * 10 - r['fenhong'] + r['peigu'] * r['peigujia']) / \
                       (10 + r['peigu'] + r['songzhuangu'])   # 复权后的收盘价
            cof = cof * (fq_close / raw_close)  # 计算系数 累乘
            bfq.loc[_date, 'qfq'] = cof

        bfq['qfq'] = bfq['qfq'].fillna(method='bfill').fillna(1)

        return bfq
    else:

        return None    # 回复空表示不保存复权系数，


def calc_hfq_cof(bfq: pd.DataFrame, xdxr: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    计算后复权系数
    :param bfq: 被复权股票ochl数据
    :param xdxr: 股票对应的xdxr数据
    :return: 在bfq数据后面增加一列 'adj' 保存对应的后复权系数，返回空表示复权系数均为1
    """

    info = xdxr.query('category==1')
    info = info.loc[bfq.index[1]:bfq.index[-1]]  # 注意取index[1],复权系数计算需用到前一天的收盘价

    if len(info) > 0:
        bfq['hfq'] = np.NAN
        cof = 1
        for i in range(len(info)):  # 前复权倒序
            r = info.iloc[i]
            xdxr_date = get_real_trade_date(info.index[i], towards=1)
            _date = get_pre_trade_day(xdxr_date)

            try:
                pre_close = bfq.loc[_date, 'close']  # 前一天收盘价,处理停牌缺失数据情况
            except KeyError:
                while _date not in bfq.index.to_list():
                    _date = get_pre_trade_day(_date)
                pre_close = bfq.loc[_date, 'close']

            fq_close = (pre_close * 10 - r['fenhong'] + r['peigu'] * r['peigujia']) / \
                       (10 + r['peigu'] + r['songzhuangu'])   # 复权后的收盘价
            cof = cof * (pre_close / fq_close)  # 计算系数 累乘
            bfq.loc[xdxr_date, 'hfq'] = cof

        bfq['hfq'] = bfq['hfq'].fillna(method='ffill').fillna(1)

        return bfq
    else:
        # bfq['adj'] = 1.0
        return None    # 回复空表示不保存复权系数，


if __name__ == '__main__':

    save_stock_xdxr('601399')
