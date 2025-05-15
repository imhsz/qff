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
获取涨停信息、封单强度等短线数据模块
"""

import akshare as ak
import pandas as pd
import datetime
import json
import time
from qff.tools.logs import log
from qff.tools.date import get_real_trade_date, now_time

__all__ = ['fetch_limit_up', 'fetch_limit_down', 'fetch_block_trade', 'fetch_margin_detail']


def fetch_limit_up(date=None):
    """
    获取指定日期的涨停信息，包括涨停股票、涨停原因、封单金额等
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: DataFrame，包含涨停股票信息
    """
    try:
        if date is None:
            date = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
        
        # 使用akshare获取涨停数据
        df = ak.stock_em_zt_pool(date=date)
        
        if df is not None and len(df) > 0:
            # 重命名列
            columns_map = {
                '序号': 'index', '代码': 'code', '名称': 'name',
                '最新价': 'close', '涨跌幅': 'pct_chg', '成交额': 'amount',
                '流通市值': 'circ_mv', '总市值': 'total_mv',
                '换手率': 'turnover', '封单资金': 'seal_money',
                '首次封板时间': 'first_limit_time', '最后封板时间': 'last_limit_time',
                '炸板次数': 'break_limit_times', '涨停统计': 'limit_times',
                '连板数': 'limit_days'
            }
            
            # 确保所有需要的列都存在
            for en, cn in columns_map.items():
                if en not in df.columns:
                    log.warning(f"涨停数据中缺少列: {en}")
                    columns_map.pop(en)
            
            df = df.rename(columns=columns_map)
            
            # 添加日期列
            df['date'] = date
            
            # 处理数据格式
            for col in ['close', 'pct_chg', 'amount', 'circ_mv', 'total_mv', 'turnover', 'seal_money']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 去掉code列前缀的数字和点，例如1.600001转为600001
            if 'code' in df.columns:
                df['code'] = df['code'].apply(lambda x: str(x).split('.')[-1])
            
            return df
        else:
            log.warning(f"未获取到 {date} 的涨停数据")
            return None
    except Exception as e:
        log.error(f"获取涨停数据异常: {str(e)}")
        return None


def fetch_limit_down(date=None):
    """
    获取指定日期的跌停信息
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: DataFrame，包含跌停股票信息
    """
    try:
        if date is None:
            date = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
        
        # 使用akshare获取跌停数据
        df = ak.stock_em_dt_pool(date=date)
        
        if df is not None and len(df) > 0:
            # 重命名列
            columns_map = {
                '序号': 'index', '代码': 'code', '名称': 'name',
                '最新价': 'close', '涨跌幅': 'pct_chg', '成交额': 'amount',
                '流通市值': 'circ_mv', '总市值': 'total_mv',
                '换手率': 'turnover', '封单资金': 'seal_money',
                '跌停统计': 'limit_times'
            }
            
            # 确保所有需要的列都存在
            for en, cn in columns_map.items():
                if en not in df.columns:
                    log.warning(f"跌停数据中缺少列: {en}")
                    columns_map.pop(en)
            
            df = df.rename(columns=columns_map)
            
            # 添加日期列
            df['date'] = date
            
            # 处理数据格式
            for col in ['close', 'pct_chg', 'amount', 'circ_mv', 'total_mv', 'turnover', 'seal_money']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 去掉code列前缀的数字和点，例如1.600001转为600001
            if 'code' in df.columns:
                df['code'] = df['code'].apply(lambda x: str(x).split('.')[-1])
            
            return df
        else:
            log.warning(f"未获取到 {date} 的跌停数据")
            return None
    except Exception as e:
        log.error(f"获取跌停数据异常: {str(e)}")
        return None


def fetch_block_trade(date=None):
    """
    获取指定日期的大宗交易数据
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: DataFrame，包含大宗交易信息
    """
    try:
        if date is None:
            date = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
            
        # 日期格式转换，从YYYY-MM-DD转为YYYYMMDD
        date_str = date.replace('-', '')
        
        # 使用akshare获取大宗交易数据
        df = ak.stock_dzjy_mrtj(start_date=date_str, end_date=date_str)
        
        if df is not None and len(df) > 0:
            # 重命名列
            columns_map = {
                '证券代码': 'code', '证券简称': 'name',
                '成交价格(元)': 'price', '成交量(万股)': 'volume',
                '成交金额(万元)': 'amount', '买方营业部': 'buyer',
                '卖方营业部': 'seller', '证券类型': 'type',
                '涨跌幅(%)': 'pct_chg', '收盘价': 'close'
            }
            
            # 确保所有需要的列都存在
            for en, cn in columns_map.items():
                if en not in df.columns:
                    log.warning(f"大宗交易数据中缺少列: {en}")
                    columns_map.pop(en)
            
            df = df.rename(columns=columns_map)
            
            # 添加日期列
            df['date'] = date
            
            # 处理数据格式
            for col in ['price', 'volume', 'amount', 'pct_chg', 'close']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
        else:
            log.warning(f"未获取到 {date} 的大宗交易数据")
            return None
    except Exception as e:
        log.error(f"获取大宗交易数据异常: {str(e)}")
        return None


def fetch_margin_detail(date=None):
    """
    获取指定日期的融资融券明细数据
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: DataFrame，包含融资融券明细信息
    """
    try:
        if date is None:
            date = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
        
        # 使用akshare获取融资融券明细数据
        df = ak.stock_margin_detail_sse(date=date)
        
        if df is not None and len(df) > 0:
            # 重命名列
            columns_map = {
                '余额': 'balance', '余量': 'volume',
                '买入金额': 'buy_amount', '买入量': 'buy_volume',
                '偿还额': 'repay_amount', '偿还量': 'repay_volume',
                '卖出金额': 'sell_amount', '卖出量': 'sell_volume',
                '融券余量': 'short_volume', '融券余额': 'short_balance',
                '融资买入额': 'finance_buy_amount', '融资买入量': 'finance_buy_volume',
                '融资偿还额': 'finance_repay_amount', '融资偿还量': 'finance_repay_volume',
                '融资余额': 'finance_balance', '融资余量': 'finance_volume',
                '融券偿还量': 'short_repay_volume', '融券偿还额': 'short_repay_amount',
                '融券卖出量': 'short_sell_volume', '融券卖出额': 'short_sell_amount',
                '标的证券代码': 'code', '标的证券简称': 'name'
            }
            
            # 确保所有需要的列都存在
            for en, cn in columns_map.items():
                if en not in df.columns:
                    log.warning(f"融资融券明细数据中缺少列: {en}")
                    columns_map.pop(en)
            
            df = df.rename(columns=columns_map)
            
            # 添加日期列
            df['date'] = date
            
            # 处理数据格式
            numeric_cols = [col for col in df.columns if col not in ['code', 'name', 'date']]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
        else:
            log.warning(f"未获取到 {date} 的融资融券明细数据")
            return None
    except Exception as e:
        log.error(f"获取融资融券明细数据异常: {str(e)}")
        return None 