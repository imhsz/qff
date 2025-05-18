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
        
        # 尝试使用不同的API获取涨停数据
        try:
            # 尝试新API: stock_zt_pool_em
            df = ak.stock_zt_pool_em(date=date)
            log.info(f"使用 stock_zt_pool_em API 获取涨停数据")
        except Exception as e1:
            log.warning(f"使用 stock_zt_pool_em API 失败: {str(e1)}")
            try:
                # 尝试另一个可能的API: stock_limit_up_em
                df = ak.stock_limit_up_em(date=date)
                log.info(f"使用 stock_limit_up_em API 获取涨停数据")
            except Exception as e2:
                log.warning(f"使用 stock_limit_up_em API 失败: {str(e2)}")
                # 尝试其他可能的API名称
                try:
                    # 尝试原始API名称
                    df = ak.stock_em_zt_pool(date=date)
                    log.info(f"使用 stock_em_zt_pool API 获取涨停数据")
                except Exception as e3:
                    log.error(f"所有尝试获取涨停数据的API均失败")
                    return None
        
        if df is not None and len(df) > 0:
            # 重命名列
            columns_map = {
                '序号': 'index', '代码': 'code', '名称': 'name',
                '最新价': 'close', '涨跌幅': 'pct_chg', '成交额': 'amount',
                '流通市值': 'circ_mv', '总市值': 'total_mv',
                '换手率': 'turnover', '封单资金': 'seal_money',
                '首次封板时间': 'first_limit_time', '最后封板时间': 'last_limit_time',
                '炸板次数': 'break_limit_times', '涨停统计': 'limit_times',
                '连板数': 'limit_days',
                # 下面是新API可能的列名
                '涨停价': 'limit_price', '涨停原因': 'reason',
                '涨停类型': 'limit_type', '封单金额': 'seal_money',
                '当日成交额': 'daily_amount', '流通股本': 'float_shares',
                '流通市值': 'circ_mv'
            }
            
            # 确保所有需要的列都存在
            for en, cn in list(columns_map.items()):
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
        
        # 尝试使用不同的API获取跌停数据
        try:
            # 获取所有涨跌停数据，然后通过涨跌幅筛选跌停股票
            df = ak.stock_zt_pool_em(date=date)
            log.info(f"获取涨跌停数据，通过涨跌幅筛选跌停股票")
            
            # 如果数据包含涨跌幅列，筛选出跌停股票（一般跌幅 <= -9.5%）
            if df is not None and len(df) > 0 and '涨跌幅' in df.columns:
                df = df[df['涨跌幅'] <= -9.5]
                log.info(f"通过涨跌幅筛选出跌停股票，共 {len(df)} 条记录")
            else:
                log.warning(f"数据中没有涨跌幅列或数据为空，无法筛选跌停股票")
                
        except Exception as e:
            log.warning(f"使用 stock_zt_pool_em API 获取涨跌停数据失败: {str(e)}")
            try:
                # 尝试stock_em_zt_pool的跌停类型
                df = ak.stock_em_zt_pool(date=date)
                # 如果数据包含涨跌幅列，筛选出跌停股票（一般跌幅 <= -9.5%）
                if '涨跌幅' in df.columns:
                    df = df[df['涨跌幅'] <= -9.5]
                    log.info(f"使用 stock_em_zt_pool API 筛选跌停股票，共 {len(df)} 条记录")
                else:
                    log.warning(f"stock_em_zt_pool返回的数据中没有涨跌幅列，无法筛选跌停股票")
            except Exception as e3:
                log.error(f"所有尝试获取跌停数据的API均失败: {str(e3)}")
                return None
        
        if df is not None and len(df) > 0:
            # 重命名列
            columns_map = {
                '序号': 'index', '代码': 'code', '名称': 'name',
                '最新价': 'close', '涨跌幅': 'pct_chg', '成交额': 'amount',
                '流通市值': 'circ_mv', '总市值': 'total_mv',
                '换手率': 'turnover', '封单资金': 'seal_money',
                '跌停统计': 'limit_times',
                # 下面是新API可能的列名
                '跌停价': 'limit_price', '跌停原因': 'reason',
                '跌停类型': 'limit_type', '封单金额': 'seal_money',
                '当日成交额': 'daily_amount', '流通股本': 'float_shares',
                '流通市值': 'circ_mv'
            }
            
            # 确保所有需要的列都存在
            for en, cn in list(columns_map.items()):
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
        
        # 尝试不同的API获取大宗交易数据
        try:
            # 尝试新API
            df = ak.stock_dzjy_mrtj(start_date=date_str, end_date=date_str)
            log.info(f"使用 stock_dzjy_mrtj API 获取大宗交易数据")
        except Exception as e:
            log.warning(f"使用 stock_dzjy_mrtj API 失败: {str(e)}")
            try:
                # 尝试另一个可能的API
                df = ak.stock_block_trade_em(date=date)
                log.info(f"使用 stock_block_trade_em API 获取大宗交易数据")
            except Exception as e2:
                log.error(f"所有尝试获取大宗交易数据的API均失败")
                return None
        
        if df is not None and len(df) > 0:
            # 重命名列 - 保留原有的columns_map，但新API可能有不同的列名
            columns_map = {
                '证券代码': 'code', '证券简称': 'name',
                '成交价格': 'price', '成交价格(元)': 'price',
                '成交量': 'volume', '成交量(万股)': 'volume',
                '成交金额': 'amount', '成交金额(万元)': 'amount',
                '买方营业部': 'buyer', '卖方营业部': 'seller',
                '证券类型': 'type', '涨跌幅': 'pct_chg',
                '涨跌幅(%)': 'pct_chg', '收盘价': 'close'
            }
            
            # 确保所有需要的列都存在，但不要在迭代过程中修改字典
            safe_columns_map = {}
            for en, cn in columns_map.items():
                if en in df.columns:
                    safe_columns_map[en] = cn
            
            df = df.rename(columns=safe_columns_map)
            
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
        
        # 日期格式转换，某些API可能需要不同的格式
        date_no_dash = date.replace('-', '')
        
        # 尝试所有可能的API获取融资融券明细数据
        df = None
        api_tried = []
        
        # 尝试 stock_margin_detail_sse API
        if hasattr(ak, 'stock_margin_detail_sse'):
            try:
                df = ak.stock_margin_detail_sse(date=date)
                log.info(f"使用 stock_margin_detail_sse API 获取融资融券明细数据")
                api_tried.append("stock_margin_detail_sse")
            except Exception as e:
                log.warning(f"使用 stock_margin_detail_sse API 失败: {str(e)}")
        else:
            log.warning(f"akshare 模块没有 stock_margin_detail_sse 属性")
        
        # 尝试 stock_margin_detail_szse API
        if hasattr(ak, 'stock_margin_detail_szse'):
            try:
                df = ak.stock_margin_detail_szse(date=date)
                log.info(f"使用 stock_margin_detail_szse API 获取融资融券明细数据")
                api_tried.append("stock_margin_detail_szse")
            except Exception as e:
                log.warning(f"使用 stock_margin_detail_szse API 失败: {str(e)}")
        else:
            log.warning(f"akshare 模块没有 stock_margin_detail_szse 属性")
        
        if df is not None and len(df) > 0:
            # 重命名列 - 列名可能因为API变化而不同
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
                '标的证券代码': 'code', '证券代码': 'code', '股票代码': 'code', 
                'stock_code': 'code', '代码': 'code',
                '标的证券简称': 'name', '证券简称': 'name', '股票简称': 'name', 
                'stock_name': 'name', '简称': 'name', '名称': 'name',
                '日期': 'date', 'date': 'date', '交易日期': 'date', '统计日期': 'date'
            }
            
            # 确保所有需要的列都存在
            safe_columns_map = {}
            for en, cn in columns_map.items():
                if en in df.columns:
                    safe_columns_map[en] = cn
            
            if safe_columns_map:
                df = df.rename(columns=safe_columns_map)
            
            # 如果date不在已重命名的列中，添加日期列
            if 'date' not in df.columns:
                df['date'] = date
            
            # 处理数据格式
            # 首先确保code列格式正确
            if 'code' in df.columns:
                df['code'] = df['code'].astype(str).apply(lambda x: x.split('.')[-1])
            
            # 处理数值列
            numeric_cols = [col for col in df.columns if col not in ['code', 'name', 'date']]
            for col in numeric_cols:
                if col in df.columns:
                    # 处理可能的字符串格式化问题，如千分位分隔符或百分比
                    if df[col].dtype == object:
                        df[col] = df[col].astype(str).str.replace(',', '').str.replace('%', '')
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            log.info(f"成功获取到 {len(df)} 条融资融券明细数据")
            return df
        else:
            log.warning(f"未获取到 {date} 的融资融券明细数据")
            return None
    except Exception as e:
        log.error(f"获取融资融券明细数据异常: {str(e)}")
        return None 