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
from qff.price.fetch import fetch_price, fetch_stock_xdxr, fetch_stock_block
from qff.price.query import get_all_securities
from qff.tools.date import get_real_trade_date, get_next_trade_day, util_get_date_gap, get_trade_days, get_pre_trade_day
from qff.tools.mongo import DATABASE
from qff.tools.utils import util_to_json_from_pandas, util_code_tolist
from pymongo.errors import PyMongoError


def save_security_day(market='stock', security=None):
    """
    从通达信获取交易日数据，并保存到数据库中
    :param market: 市场类型，目前支持"stock/index/etf", 默认"stock".
    :param security: list or None, 证券列表
    """
    try:

        end_date = now_time()[:10]
        # stock_list = fetch_stock_list(market).index.to_list()
        stock_list = get_all_securities(market=market) if security is None else security
        table_name = market + '_day'
        print(f'====  Now Saving {table_name.upper()} ====')
        coll = DATABASE.get_collection(table_name)
        coll.create_index([("code", 1), ("date", 1)], unique=True)
        coll.create_index("date")

        data_num = 0
        data_list = []
        start = time.perf_counter()
        total = len(stock_list)
        for item in range(total):
            code = stock_list[item]
            print_progress(item, total, start, code)

            try:
                last_recode = coll.find_one({'code': code}, sort=[('date', -1)])
                start_date = last_recode['date']
            except TypeError or PyMongoError:
                start_date = '1990-01-01'
                last_recode = None

            if start_date != end_date:
                try:
                    # start_date = get_next_trade_day(start_date)
                    # print('Trying updating {} from {}'.format(code, start_date))
                    data = fetch_price(code, freq='day', market=market, start=start_date)
                    if data is None or len(data) == 0:
                        # 如果每日更新时遇见连续停牌股票，则fetch_price返回空，
                        # 如果start_date不为'1990-01-01'
                        # 需要将数据库中最后一条记录的收盘价，用于生成停牌日数据
                        if start_date > '1990-01-01':
                            data = pd.DataFrame(
                                index=pd.Index(get_trade_days(start_date, end_date), name='date'),
                                columns=['code', 'open', 'close', 'low', 'high', 'vol', 'amount']
                            )
                            data['code'] = code
                            data[['open', 'close', 'high', 'low']] = last_recode['close']
                            data[['vol', 'amount']] = 0
                        else:
                            print('股票{}无历史日数据！可能是未上市新股!'.format(code))
                            continue

                    else:

                        data = data.loc[:end_date]
                        if start_date == '1990-01-01':
                            start_date = data.index[0]   # fix bug like :updating 603125 data error!
                                                         # Exception:'1990-01-01'

                        dl = get_trade_days(start_date, end_date)

                        if len(dl) > len(data):
                            # 存在停牌日数据
                            dl_df = pd.DataFrame(index=pd.Index(dl, name='date'))
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
                        coll.insert_many(util_to_json_from_pandas(data_batch))

                except Exception as e:
                    print(f'updating {code} data error!')
                    print('Exception:' + str(e))

        if data_num > 0:
            data = pd.concat(data_list)
            coll.insert_many(util_to_json_from_pandas(data))

        print(f'\n==== SUCCESS SAVE {table_name.upper()} DATA! ====')
    except EOFError:
        time.sleep(1)
    except Exception as e:
        print(" \nError save_security_day exception!")
        print(str(e))


def save_security_min(market='stock', freq='1min', security=None):
    """
    从通达信获取交易日数据，并保存到数据库中
    :param market: 市场类型，目前支持"stock/index/etf", 默认"stock".
    :param freq: 分钟频率，支持1min/5min/15min/30min/60min.
    :param security: list or None, 证券列表
    """
    if freq not in ["1min", "5min", "15min", "30min", "60min"] or\
       market not in ["stock", "index", "etf"]:
        print("save_security_min: 输入参数错误！")
        return

    try:
        end_date = now_time()
        # stock_list = fetch_stock_list(market).index.to_list()
        # stock_list = get_all_securities(market=market)
        stock_list = get_all_securities(market=market) if security is None else security
        table_name = market + '_min'
        print(f'==== NOW SAVE {market.upper()}_{freq.upper()} DATA =====')
        coll = DATABASE.get_collection(table_name)
        coll.create_index([("type", 1), ("code", 1), ("datetime", 1)], unique=True)

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
                        coll.insert_many(util_to_json_from_pandas(data))

                except Exception as e:
                    print(f'\nupdating {code} {freq} data error!')
                    print('Exception:' + str(e))
        if data_num > 0:
            data = pd.concat(data_list)
            coll.insert_many(util_to_json_from_pandas(data))

        print(f'\n==== SUCCESS SAVE {table_name.upper()} {freq} DATA! ====')
    except EOFError:
        time.sleep(1)
    except Exception as e:
        print(f"\nError save_security_min exception!:{market.upper()} {freq.upper()} DATA")
        print(e)


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
    return str(get_real_trade_date(str(datetime.date.today() - datetime.timedelta(days=1)))) + \
           ' 15:00:00' if datetime.datetime.now().hour < 15 \
           else str(get_real_trade_date(str(datetime.date.today()))) + ' 15:00:00'


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
    :return: 在bfq数据后面增加一列 'qfq' 保存对应的前复权系数，返回空表示复权系数均为1
    """
    info = xdxr.query('category==1')
    # 修复：正确处理索引范围，确保包含所有需要复权的日期
    if len(bfq.index) > 1:
        info = info.loc[bfq.index[0]:bfq.index[-1]]  # 从第一个交易日到最后一个交易日
    elif len(bfq.index) == 1:
        info = info.loc[bfq.index[0]:bfq.index[0]]
    else:
        info = pd.DataFrame()

    if len(info) > 0:
        bfq = bfq.copy()  # 创建副本避免修改原始数据
        bfq['qfq'] = 1.0  # 初始化为1
        
        # 前复权：从后往前计算，保持最新价格不变，调整历史价格
        adj_factors = {}  # 存储每个日期的复权因子
        
        for i in range(len(info)-1, -1, -1):  # 倒序处理
            r = info.iloc[i]
            xdxr_date = info.index[i]  # 除权除息日期
            _date = get_pre_trade_day(xdxr_date)  # 除权日前一个交易日

            # 确保日期在数据范围内
            if _date not in bfq.index:
                continue

            try:
                raw_close = bfq.loc[_date, 'close']  # 除权日前一天的收盘价
            except KeyError:
                continue

            # 避免除零错误
            if raw_close == 0:
                continue

            # 计算复权后的收盘价
            numerator = raw_close * 10 - r['fenhong'] + r['peigu'] * r['peigujia']
            denominator = 10 + r['peigu'] + r['songzhuangu']
            
            if denominator == 0:
                continue
                
            fq_close = numerator / denominator
            
            # 前复权系数计算：复权价格/原始价格
            if raw_close != 0:
                adj_factor = fq_close / raw_close
                adj_factors[_date] = adj_factor

        # 应用复权因子
        if adj_factors:
            # 按日期排序
            sorted_dates = sorted(adj_factors.keys(), reverse=True)  # 从最近的日期开始
            
            # 从前一个交易日开始向前应用复权因子
            cumulative_factor = 1.0
            for date in bfq.index[::-1]:  # 从后向前遍历
                # 如果该日期有复权事件，更新累积因子
                if date in adj_factors:
                    cumulative_factor *= adj_factors[date]
                
                # 应用累积因子
                bfq.loc[date, 'qfq'] = cumulative_factor

        return bfq
    else:
        return None  # 返回空表示不保存复权系数


def calc_hfq_cof(bfq: pd.DataFrame, xdxr: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    计算后复权系数
    :param bfq: 被复权股票ochl数据
    :param xdxr: 股票对应的xdxr数据
    :return: 在bfq数据后面增加一列 'hfq' 保存对应的后复权系数，返回空表示复权系数均为1
    """
    info = xdxr.query('category==1')
    # 修复：正确处理索引范围，确保包含所有需要复权的日期
    if len(bfq.index) > 1:
        info = info.loc[bfq.index[0]:bfq.index[-1]]  # 从第一个交易日到最后一个交易日
    elif len(bfq.index) == 1:
        info = info.loc[bfq.index[0]:bfq.index[0]]
    else:
        info = pd.DataFrame()

    if len(info) > 0:
        bfq = bfq.copy()  # 创建副本避免修改原始数据
        bfq['hfq'] = 1.0  # 初始化为1
        
        # 后复权：从前往后计算，保持历史价格不变，调整最新价格
        adj_factors = {}  # 存储每个日期的复权因子
        
        for i in range(len(info)):  # 正序处理
            r = info.iloc[i]
            xdxr_date = info.index[i]  # 除权除息日期
            _date = get_pre_trade_day(xdxr_date)  # 除权日前一个交易日

            # 确保日期在数据范围内
            if _date not in bfq.index:
                continue

            try:
                pre_close = bfq.loc[_date, 'close']  # 除权日前一天的收盘价
            except KeyError:
                continue

            # 避免除零错误
            if pre_close == 0:
                continue

            # 计算复权后的收盘价
            numerator = pre_close * 10 - r['fenhong'] + r['peigu'] * r['peigujia']
            denominator = 10 + r['peigu'] + r['songzhuangu']
            
            if denominator == 0:
                continue
                
            fq_close = numerator / denominator
            
            # 后复权系数计算：原始价格/复权价格
            if fq_close != 0:
                adj_factor = pre_close / fq_close
                adj_factors[xdxr_date] = adj_factor

        # 应用复权因子
        if adj_factors:
            # 按日期排序
            sorted_dates = sorted(adj_factors.keys())
            
            # 从除权除息日开始向后应用复权因子
            cumulative_factor = 1.0
            for date in bfq.index:  # 从前向后遍历
                # 如果该日期有复权事件，更新累积因子
                if date in adj_factors:
                    cumulative_factor *= adj_factors[date]
                
                # 应用累积因子
                bfq.loc[date, 'hfq'] = cumulative_factor

        return bfq
    else:
        return None  # 返回空表示不保存复权系数


if __name__ == '__main__':

    save_stock_xdxr('601399')
