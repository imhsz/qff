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
通过通达信接口获取股票实时价格数据
"""
import json
import pandas as pd
from datetime import date
from pytdx.hq import TdxHq_API
from retrying import retry
from qff.tools.date import is_trade_day, get_trade_gap, get_real_trade_date
from qff.tools.logs import log
from qff.tools.tdx import get_best_ip, select_market_code, select_index_code, stock_ip_list, select_best_ip_list
import traceback
import concurrent.futures
from functools import partial
import time
import random


__all__ = ["fetch_price", "fetch_price_parallel", "fetch_ticks", "fetch_current_ticks",
           "fetch_today_transaction", "fetch_today_min_curve", "fetch_stock_xdxr", "fetch_stock_block"]


def _select_freq(freq):
    if freq in ['day', 'd', 'D', 'DAY', 'Day']:
        freq, c = 9, 1
    elif str(freq) in ['1', '1m', '1min', 'one']:
        freq, c = 8, 240
    elif str(freq) in ['5', '5m', '5min', 'five']:
        freq, c = 0, 48
    elif str(freq) in ['15', '15m', '15min', 'fifteen']:
        freq, c = 1, 16
    elif str(freq) in ['30', '30m', '30min', 'half']:
        freq, c = 2, 8
    elif str(freq) in ['60', '60m', '60min', '1h']:
        freq, c = 3, 4
    elif freq in ['w', 'W', 'Week', 'week']:
        freq, c = 5, 1/5
    elif freq in ['month', 'M', 'mon', 'Month']:
        freq, c = 6, 1/20
    elif freq in ['Q', 'Quarter', 'q']:
        freq, c = 10, 1/60
    elif freq in ['y', 'Y', 'year', 'Year']:
        freq, c = 11, 1/250
    else:
        freq, c = 0, 0

    return freq, c


def _calc_today_min_len():
    # 计算当天1分钟曲线的数据记录长度
    _now = pd.Timestamp.now()
    s_now = _now.strftime('%Y-%m-%d')
    if not is_trade_day(s_now):
        data_len = 240
    else:
        open_time = pd.to_datetime('{0} 09:31:00'.format(s_now))
        # 计算当前时间和开盘时间的分钟数
        interval = int((_now.ceil('1min') - open_time).total_seconds()/60)
        if interval <= 0:
            data_len = 240
        elif 0 < interval <= 120:
            data_len = interval
        elif 120 < interval <= 210:
            data_len = interval - 120
        else:
            data_len = 240
    return data_len


# @retry(stop_max_attempt_number=3, wait_random_min=50, wait_random_max=100)
def fetch_price(code, count=None, freq='day', market='stock', start=None):
    """
    从tdx服务器上获取曲线数据，仅可查询一支股票，按天或者分钟，返回数据格式为 DataFrame

    :param code: 一支股票代码或者一个指数代码
    :param count: 返回的结果集的行数, 即表示获取至当前时刻之前几个frequency的数据,-1表示所有数据。
        与 start 二选一，不可同时使用，如果同时存在，start参数无效
    :param freq: 单位时间长度, 天或者分钟, 现在支持，day/week/month/quarter/year/1m/5m/15m/30m/60m ,默认值是day
    :param market: 市场类型，目前支持"stock/index/etf", 默认"stock".
    :param start: 开始日期，不带分钟信息。与 count 二选一，不可同时使用. 字符串或者 datetime.date 对象,如果 count
        和 start 参数都没有, 则取count=1,即获取最近一条数据。

    :type code: str
    :type count: int
    :type freq: str
    :type market: str
    :type start: str

    :return:
        返回[pandas.DataFrame]对象, 行索引是date(分钟级别数据为datetime), 列索引是行情字段名字.
        如果只获取了一天,而当天停牌,返回None，注意：所有数据都未复权
    """
    freq, c = _select_freq(freq)
    if count is None:
        if start is None:
            count = 1
        else:
            count = get_trade_gap(start, str(date.today()))
            count = int(count * c)
            if count > 40800:
                count = 40800
    elif count <= 0:
        count = 40800

    ip, port = get_best_ip()
    api = TdxHq_API()
    try:
        with api.connect(ip, port):
            ret = []
            _start = 0
            while count > 0:
                _len = 800 if count > 800 else count
                if market in ['stock', 'etf']:
                    df = api.get_security_bars(freq, select_market_code(code), code, _start, _len)
                elif market == 'index':
                    df = api.get_index_bars(freq, select_index_code(code), code, _start, _len)
                if df is not None and len(df) > 0:
                    df = api.to_df(df)
                    ret.append(df)
                    _start += _len
                    count -= _len
                else:
                    break

            if len(ret) > 0:
                data = pd.concat(ret, axis=0, sort=False) if len(ret) > 1 else ret[0]

                if freq in [0, 1, 2, 3, 8]:  # 分钟数据
                    data = data.drop(['year', 'month', 'day', 'hour', 'minute'], axis=1, inplace=False)
                    data = data.assign(datetime=data['datetime'] + ':00')
                    data.set_index('datetime', inplace=True)

                else:
                    data = data.assign(date=data['datetime'].apply(lambda x: str(x[0:10])))
                    data = data.drop(['year', 'month', 'day', 'hour', 'minute', 'datetime'], axis=1, inplace=False)
                    data.set_index('date', inplace=True)
                data.sort_index(inplace=True)
                data.insert(0, 'code', code)
                if start is not None:
                    data = data.loc[start:]
                return data
            else:
                # 这里的问题是: 如果只取了一天的股票,而当天停牌, 那么就直接返回None了
                return None

    except Exception as err:
        # log.error(f'fetch_price exception:{err}')
        log.error(f'fetch_price exception for code {code}, market {market}, freq {freq}: {err}')
        log.error(traceback.format_exc())
        return None


def fetch_today_min_curve(code, market='stock'):
    """
    获取当天的分钟曲线，返回当前时间前的当日1分钟曲线数据，用于模拟交易环境

    :param code: 一支股票代码或者一个指数代码
    :param market: 市场类型，目前支持"stock/index/etf", 默认"stock".

    :type code: str
    :type market: str

    :return:
        返回[pandas.DataFrame]对象, 行索引是date(分钟级别数据为datetime), 列索引是行情字段名字.

    """
    count = _calc_today_min_len()
    return fetch_price(code, count, freq='1m', market=market)


def fetch_current_ticks(code, market='stock'):
    """
    获取单个股票或指数当前时刻的ticks数据

    :param code: 一支股票代码或者一个指数代码
    :param market: 市场类型，目前支持"stock"和"index", 默认"stock".

    :type code: str
    :type market: str

    :return: 返回[Dict]对象,各字段含义如下:

        ==================  ====================
        字段名	                含义
        ==================  ====================
        price               当前价格
        last_close          昨日收盘价
        open                当日开盘价
        high                截至到当前时刻的日内最高价
        low                 截至到当前时刻的日内最低价
        vol                 截至到当前时刻的日内总手数
        cur_vol             当前tick成交笔数
        amount              截至到当前时刻的日内总成交额
        s_vol               内盘
        b_vol               外盘
        bid1~bid5           买一到买五价格
        ask1~ask5           卖一到卖五价格
        bid_vol1~bid_vol5   买一到买五挂单手数
        ask_vol1~ask_vol5   卖一到卖五挂单手数
        ==================  ====================

    """
    ip, port = get_best_ip()
    api = TdxHq_API()
    with api.connect(ip, port):
        data = api.get_security_quotes([(select_market_code(code, market), code)])[0]
        data = json.loads(json.dumps(data))
    return data


@retry(stop_max_attempt_number=3, wait_random_min=50, wait_random_max=100)
def fetch_ticks(code, market='stock'):
    """
    获取股票或指数列表当前时刻的ticks数据

    :param code: 一支股票代码或者一个指数代码列表
    :param market: 市场类型，目前支持"stock"和"index", 默认"stock".

    :type code: list
    :type market: str

    :return: 返回[pandas.DataFrame]对象,当前股票列表对应的tick数据。tick字段描述请见 :ref:`class_tick`

    """
    stocks = [(select_market_code(code, market), code) for code in code]
    ip, port = get_best_ip()
    api = TdxHq_API()
    with api.connect(ip, port):
        data = pd.concat(
            [api.to_df(api.get_security_quotes(stocks[i: i+80])) for i in range(len(stocks) + 1)]
        )
        return data


def fetch_today_transaction(code):
    """
    获取当日实时分笔成交信息，包含集合竞价

    :param code: 一支股票代码
    :type code: str

    :return: 返回对应股票的分笔成交信息，

    ::

                          price    vol   num       buyorsell
        datetime
        2022-12-30 09:25  13.04   3119  153          2
        2022-12-30 09:30  13.04   2965   89          0
        2022-12-30 09:30  13.05  10320  182          0

        其中： buyorsell 1--sell 0--buy 2--盘前'

    """
    ip, port = get_best_ip()
    api = TdxHq_API()

    try:
        with api.connect(ip, port):
            # data = pd.DataFrame()
            data = pd.concat([api.to_df(api.get_transaction_data(
                select_market_code(str(code)), code, (2 - i) * 2000, 2000))
                for i in range(3)], axis=0, sort=False)
            data = data.dropna()
            day = get_real_trade_date(date.today())
            data = data.assign(datetime=data['time'].apply(lambda x: day + ' ' + str(x)))
            data = data.drop(['time'], axis=1)
            data.set_index('datetime', inplace=True)
            if 'value' in data.columns:
                data = data.drop(['value'], axis=1)
            return data
    except Exception as err:
        log.error(f'fetch_today_transaction exception:{err}')
        return None


def fetch_stock_info(code):
    """
    获取当日股票基本信息

    :param code: 股票代码
    :return: dict

    """
    ip, port = get_best_ip()
    api = TdxHq_API()
    market_code = select_market_code(code)
    with api.connect(ip, port):
        return api.get_finance_info(market_code, code)


def fetch_stock_list(market='stock'):
    """
    获取当日股票/指数/ETF列表

    :param market: 市场类型stock/index/etf

    :return: dataframe

    """
    ip, port = get_best_ip()
    api = TdxHq_API()
    with api.connect(ip, port):

        # 读取深圳市场股票代码
        sz = pd.concat([api.to_df(api.get_security_list(0, i * 1000))
                       for i in range(int(api.get_security_count(0) / 1000) + 1)], axis=0, sort=False)
        sz = sz[['code', 'name']].dropna()
        if market == 'stock':
            sz = sz[sz['code'].str[:2].isin(['00', '30', '02'])]
        elif market == 'index':
            sz = sz[sz['code'].str[:2].isin(['39'])]
        elif market == 'etf':
            sz = sz[sz['code'].str[:2].isin(['15'])]
        else:
            log.error("fetch_stock_list: 参数market错误！")
            return None
        # 读取上海市场股票代码
        sh = pd.concat([api.to_df(api.get_security_list(1, i*1000))
                       for i in range(int(api.get_security_count(1) / 1000) + 1)], axis=0, sort=False)
        sh = sh[['code', 'name']].dropna()
        if market == 'stock':
            sh = sh[sh['code'].str.startswith('6')]
        elif market == 'index':
            sh = sh[sh['code'].str[:3].isin(['000', '880'])]
        elif market == 'etf':
            sh = sh[sh['code'].str[:2].isin(['51'])]
        else:
            log.error("fetch_stock_list: 参数market错误！")
            return None

        # 读取北京市场股票代码
        # bj = pd.concat([api.to_df(api.get_security_list(2, i*1000))
        #                for i in range(int(api.get_security_count(2) / 1000) + 1)], axis=0, sort=False)
        # if bj is not None and len(bj) > 0:
        #     bj = bj[['code', 'name']].dropna()
        #     if market == 'stock':
        #         bj = bj[bj['code'].str[:2].isin(['43', '83', '87', '82', '88'])]
        #     elif market == 'index':
        #         bj = bj[bj['code'].str[:2].isin(['89'])]
        #     else:
        #         log.error("fetch_stock_list: 参数market错误！")
        #         return None
        #     data = pd.concat([sz, sh, bj], sort=False).set_index('code')
        # else:
        #     data = pd.concat([sz, sh], sort=False).set_index('code')

        data = pd.concat([sz, sh], sort=False).set_index('code')
        return data.sort_index().assign(name=data['name'].apply(lambda x: str(x)[0:6].strip().strip(b'\x00'.decode())))


@retry(stop_max_attempt_number=3, wait_random_min=50, wait_random_max=100)
def fetch_stock_xdxr(code):
    """
    获取除权除息数据
    :param code:
    :return:
    """
    market_code = select_market_code(code)
    ip, port = get_best_ip()
    api = TdxHq_API()
    # with api.connect(ip, port):
    api.connect(ip, port)
    category = {
        '1': '除权除息', '2': '送配股上市', '3': '非流通股上市', '4': '未知股本变动',
        '5': '股本变化',
        '6': '增发新股', '7': '股份回购', '8': '增发新股上市', '9': '转配股上市',
        '10': '可转债上市',
        '11': '扩缩股', '12': '非流通股缩股', '13': '送认购权证', '14': '送认沽权证'}
    data = api.to_df(api.get_xdxr_info(market_code, code))
    if len(data) >= 1 and 'year' in data.columns:
        data = data \
            .assign(date=pd.to_datetime(data[['year', 'month', 'day']])) \
            .drop(['year', 'month', 'day'], axis=1) \
            .assign(category_meaning=data['category'].apply(
                lambda x: category[str(x)])) \
            .assign(code=str(code)) \
            .rename(index=str, columns={'panhouliutong': 'liquidity_after',
                                        'panqianliutong': 'liquidity_before',
                                        'houzongguben': 'shares_after',
                                        'qianzongguben': 'shares_before'}) \

        data = data.assign(date=data['date'].apply(lambda x: str(x)[0:10]))\
            .set_index('date', drop=False, inplace=False).sort_index()

    else:
        data = None
    api.close()
    return data


def fetch_stock_block():
    """
    获取股票板块数据，包括概念板块、风格板块、指数板块

    """
    ip, port = get_best_ip()
    api = TdxHq_API()
    with api.connect(ip, port):

        data = pd.concat([api.to_df(
            api.get_and_parse_block_info("block_gn.dat")).assign(type='gn'),
            api.to_df(api.get_and_parse_block_info(
                "block.dat")).assign(type='yb'),
            api.to_df(api.get_and_parse_block_info(
                "block_zs.dat")).assign(type='zs'),
            api.to_df(api.get_and_parse_block_info(
                "block_fg.dat")).assign(type='fg')], sort=False)

        if len(data) > 10:
            return data.assign(source='tdx').drop(['block_type', 'code_index'],
                                                  axis=1).set_index('code',
                                                                    drop=False,
                                                                    inplace=False).drop_duplicates()
        else:
            log.error("fetch_stock_block: 错误！")
            return None


def fetch_price_parallel(codes, count=None, freq='day', market='stock', start=None, max_workers=5, max_retry=3):
    """
    并行从多个tdx服务器上获取多只股票的曲线数据，按天或者分钟，返回数据格式为 Dict[股票代码, DataFrame]

    :param codes: 股票代码列表
    :param count: 返回的结果集的行数, 即表示获取至当前时刻之前几个frequency的数据,-1表示所有数据
    :param freq: 单位时间长度, 天或者分钟, 现在支持，day/week/month/quarter/year/1m/5m/15m/30m/60m
    :param market: 市场类型，目前支持"stock/index/etf", 默认"stock"
    :param start: 开始日期，不带分钟信息
    :param max_workers: 最大线程数，默认5
    :param max_retry: 单个股票失败后最大重试次数，默认3
    :return: Dict[股票代码, DataFrame]
    """
    if not codes:
        return {}
    
    # 获取最佳服务器列表
    best_ips = select_best_ip_list(n=max_workers)
    if not best_ips:
        log.error("无法获取可用的 TDX 服务器")
        return {}
    
    # 使用线程池并行获取数据
    results = {}
    failed_codes = []  # 记录获取失败的股票
    
    def _fetch_single_stock(code, ip_port_pair, retry_count=0):
        """单个股票获取函数，支持重试"""
        try:
            ip, port = ip_port_pair
            api = TdxHq_API(heartbeat=True)  # 启用心跳检测
            with api.connect(ip, port, time_out=10):  # 设置超时时间为10秒
                ret = []
                _start = 0
                _count = 40800 if count is None or count <= 0 else count
                
                while _count > 0:
                    _len = 800 if _count > 800 else _count
                    if market in ['stock', 'etf']:
                        df = api.get_security_bars(freq, select_market_code(code), code, _start, _len)
                    elif market == 'index':
                        df = api.get_index_bars(freq, select_index_code(code), code, _start, _len)
                    else:
                        return None
                        
                    if df is not None and len(df) > 0:
                        df = api.to_df(df)
                        ret.append(df)
                        _start += _len
                        _count -= _len
                    else:
                        break
                
                if len(ret) > 0:
                    data = pd.concat(ret, axis=0, sort=False) if len(ret) > 1 else ret[0]
                    
                    if int(freq) in [0, 1, 2, 3, 8]:  # 分钟数据
                        data = data.drop(['year', 'month', 'day', 'hour', 'minute'], axis=1, inplace=False)
                        data = data.assign(datetime=data['datetime'] + ':00')
                        data.set_index('datetime', inplace=True)
                    else:
                        data = data.assign(date=data['datetime'].apply(lambda x: str(x[0:10])))
                        data = data.drop(['year', 'month', 'day', 'hour', 'minute', 'datetime'], axis=1, inplace=False)
                        data.set_index('date', inplace=True)
                    
                    data.sort_index(inplace=True)
                    data.insert(0, 'code', code)
                    if start is not None:
                        data = data.loc[start:]
                    return data
                else:
                    return None
                    
        except Exception as e:
            error_msg = str(e)
            log.error(f"获取 {code} 数据时出错 (重试 {retry_count}/{max_retry}): {error_msg}")
            
            # 超时或连接错误时尝试重试
            if retry_count < max_retry and ("timed out" in error_msg or 
                                          "连接失败" in error_msg or 
                                          "timeout" in error_msg or
                                          "connection" in error_msg.lower()):
                # 随机等待一段时间后重试，避免所有线程同时重试
                time.sleep(0.5 + random.random())
                # 尝试使用不同的服务器
                new_ip_port = random.choice(best_ips)
                log.info(f"重试 {code} 使用服务器 {new_ip_port[0]}:{new_ip_port[1]}")
                return _fetch_single_stock(code, new_ip_port, retry_count + 1)
            return None
    
    # 将股票分配给不同的服务器
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 创建任务列表
        future_to_code = {}
        for i, code in enumerate(codes):
            ip_port = best_ips[i % len(best_ips)]
            future = executor.submit(_fetch_single_stock, code, ip_port)
            future_to_code[future] = code
        
        # 收集结果
        for future in concurrent.futures.as_completed(future_to_code):
            code = future_to_code[future]
            try:
                data = future.result()
                if data is not None:
                    results[code] = data
                else:
                    failed_codes.append(code)
                    log.warning(f"获取 {code} 数据失败或返回为空")
            except Exception as e:
                failed_codes.append(code)
                log.error(f"处理 {code} 数据时发生异常: {str(e)}")
    
    if failed_codes:
        failed_count = len(failed_codes)
        total_count = len(codes)
        log.warning(f"共有 {failed_count}/{total_count} ({failed_count/total_count*100:.1f}%) 的股票数据获取失败")
        
    return results


if __name__ == '__main__':
    fetch_stock_list("stock")
