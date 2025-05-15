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
获取龙虎榜、解禁股、资金流向等信息模块
"""

import akshare as ak
import pandas as pd
import datetime
import json
import time
from qff.tools.logs import log
from qff.tools.date import get_real_trade_date

__all__ = ['fetch_top_list', 'fetch_top_inst', 'fetch_restricted_release', 
           'fetch_moneyflow_hsgt', 'fetch_moneyflow_stock', 'fetch_moneyflow_sector']


def fetch_top_list(date=None):
    """
    获取指定日期的龙虎榜数据
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: DataFrame，包含龙虎榜数据
    """
    try:
        if date is None:
            date = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
        
        # 尝试使用不同的API获取龙虎榜数据
        try:
            # 尝试使用stock_lhb_detail_em API
            # 注意：此API需要使用start_date和end_date参数
            df = ak.stock_lhb_detail_em(start_date=date.replace('-', ''), end_date=date.replace('-', ''))
            log.info(f"使用 stock_lhb_detail_em API 获取龙虎榜数据")
        except Exception as e1:
            log.warning(f"使用 stock_lhb_detail_em API 失败: {str(e1)}")
            try:
                # 尝试其他龙虎榜相关API
                df = ak.stock_lhb_stock_detail_em(date=date)
                log.info(f"使用 stock_lhb_stock_detail_em API 获取龙虎榜数据")
            except Exception as e2:
                log.error(f"获取龙虎榜数据失败：所有API调用均失败: {str(e2)}")
                return None
        
        if df is not None and len(df) > 0:
            # 更新重命名列以匹配新的API返回值
            columns_map = {
                '序号': 'index', '代码': 'code', '名称': 'name',
                '上榜日': 'list_date', '解读': 'explanation', 
                '收盘价': 'close', '涨跌幅': 'pct_chg',
                '龙虎榜净买额': 'net_buy_amount', '龙虎榜买入额': 'buy_amount',
                '龙虎榜卖出额': 'sell_amount', '龙虎榜成交额': 'amount',
                '市场总成交额': 'total_amount', 
                '净买额占总成交比': 'net_buy_ratio', 
                '成交额占总成交比': 'amount_ratio',
                '换手率': 'turnover', '流通市值': 'circ_mv',
                '上榜原因': 'reason', 
                '上榜后1日': 'after_1day', '上榜后2日': 'after_2day',
                '上榜后5日': 'after_5day', '上榜后10日': 'after_10day'
            }
            
            # 确保所有需要的列都存在，避免在迭代过程中修改字典
            safe_columns_map = {}
            for en, cn in columns_map.items():
                if en in df.columns:
                    safe_columns_map[en] = cn
                else:
                    log.warning(f"龙虎榜数据中缺少列: {en}")
            
            df = df.rename(columns=safe_columns_map)
            
            # 添加日期列
            df['date'] = date
            
            # 处理数据格式
            for col in ['close', 'pct_chg', 'net_buy_amount', 'buy_amount', 'sell_amount',
                       'amount', 'total_amount', 'net_buy_ratio', 'amount_ratio',
                       'turnover', 'circ_mv', 'after_1day', 'after_2day', 'after_5day', 'after_10day']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 处理上榜日期字段，如果是时间戳格式则转为日期字符串
            if 'list_date' in df.columns:
                try:
                    if isinstance(df['list_date'].iloc[0], (int, float)):
                        # 将时间戳转换为日期字符串
                        df['list_date'] = pd.to_datetime(df['list_date'], unit='ms').dt.strftime('%Y-%m-%d')
                except Exception as e:
                    log.warning(f"处理上榜日期字段失败: {str(e)}")
            
            # 去掉code列前缀的数字和点，例如1.600001转为600001
            if 'code' in df.columns and len(df) > 0 and '.' in str(df['code'].iloc[0]):
                df['code'] = df['code'].apply(lambda x: str(x).split('.')[-1])
            
            return df
        else:
            log.warning(f"未获取到 {date} 的龙虎榜数据")
            return None
    except Exception as e:
        log.error(f"获取龙虎榜数据异常: {str(e)}")
        return None


def fetch_top_inst(date=None):
    """
    获取指定日期的龙虎榜机构数据
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: DataFrame，包含龙虎榜机构数据
    """
    try:
        if date is None:
            date = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
        
        # 使用akshare获取龙虎榜机构数据
        df = ak.stock_em_lhb_jgmmtj(start_date=date, end_date=date)
        
        if df is not None and len(df) > 0:
            # 重命名列
            columns_map = {
                '序号': 'index', '代码': 'code', '名称': 'name',
                '上榜日': 'list_date', '上榜原因': 'reason',
                '涨跌幅': 'pct_chg', '买入额(万)': 'buy_amount',
                '买入金额占总成交比例': 'buy_ratio', '卖出额(万)': 'sell_amount',
                '卖出金额占总成交比例': 'sell_ratio', '净额(万)': 'net_amount',
                '成交额(万)': 'amount', '买入金额占成交额比': 'buy_amount_ratio',
                '卖出金额占成交额比': 'sell_amount_ratio'
            }
            
            # 确保所有需要的列都存在，避免在迭代过程中修改字典
            safe_columns_map = {}
            for en, cn in columns_map.items():
                if en in df.columns:
                    safe_columns_map[en] = cn
                else:
                    log.warning(f"龙虎榜机构数据中缺少列: {en}")
            
            df = df.rename(columns=safe_columns_map)
            
            # 添加日期列
            df['date'] = date
            
            # 处理数据格式
            for col in ['pct_chg', 'buy_amount', 'buy_ratio', 'sell_amount', 
                        'sell_ratio', 'net_amount', 'amount', 'buy_amount_ratio', 
                        'sell_amount_ratio']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 去掉code列前缀的数字和点，例如1.600001转为600001
            if 'code' in df.columns and len(df) > 0 and '.' in str(df['code'].iloc[0]):
                df['code'] = df['code'].apply(lambda x: str(x).split('.')[-1])
            
            return df
        else:
            log.warning(f"未获取到 {date} 的龙虎榜机构数据")
            return None
    except Exception as e:
        log.error(f"获取龙虎榜机构数据异常: {str(e)}")
        return None


def fetch_restricted_release(date=None):
    """
    获取指定日期解禁股数据
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为当前日期
    :return: DataFrame，包含解禁股数据
    """
    try:
        # 使用akshare获取解禁股数据
        # 如果不指定日期，获取未来一年的数据
        df = ak.stock_restricted_shares()
        
        if df is not None and len(df) > 0:
            # 重命名列
            columns_map = {
                '序号': 'index', '代码': 'code', '名称': 'name',
                '解禁日期': 'release_date', '解禁数量(万股)': 'release_count',
                '解禁数量占总股本比例': 'release_ratio', '股价(元)': 'price',
                '解禁市值(亿元)': 'release_market_value', '解禁股类型': 'release_type',
                '解禁股东': 'release_shareholder'
            }
            
            # 确保所有需要的列都存在，避免在迭代过程中修改字典
            safe_columns_map = {}
            for en, cn in columns_map.items():
                if en in df.columns:
                    safe_columns_map[en] = cn
                else:
                    log.warning(f"解禁股数据中缺少列: {en}")
            
            df = df.rename(columns=safe_columns_map)
            
            # 处理数据格式
            for col in ['release_count', 'release_ratio', 'price', 'release_market_value']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 去掉code列前缀的数字和点，例如1.600001转为600001
            if 'code' in df.columns and len(df) > 0 and '.' in str(df['code'].iloc[0]):
                df['code'] = df['code'].apply(lambda x: str(x).split('.')[-1])
            
            # 如果指定了日期，筛选出该日期的数据
            if date is not None:
                if 'release_date' in df.columns:
                    df = df[df['release_date'] == date]
                    if len(df) == 0:
                        log.warning(f"未获取到 {date} 的解禁股数据")
                        return None
            
            return df
        else:
            log.warning("未获取到解禁股数据")
            return None
    except Exception as e:
        log.error(f"获取解禁股数据异常: {str(e)}")
        return None


def fetch_moneyflow_hsgt(date=None):
    """
    获取指定日期沪深港通资金流向数据
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: DataFrame，包含沪深港通资金流向数据
    """
    try:
        if date is None:
            date = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
        
        # 使用akshare获取沪深港通资金流向数据
        df = ak.stock_em_hsgt_hist(start_date=date, end_date=date)
        
        if df is not None and len(df) > 0:
            # 重命名列
            columns_map = {
                '日期': 'date', '当日成交净买额': 'net_amount',
                '港股通(沪)': 'hk_sh', '港股通(深)': 'hk_sz',
                '沪股通': 'sh_hk', '深股通': 'sz_hk',
                '南向资金': 'south_money', '北向资金': 'north_money'
            }
            
            # 确保所有需要的列都存在，避免在迭代过程中修改字典
            safe_columns_map = {}
            for en, cn in columns_map.items():
                if en in df.columns:
                    safe_columns_map[en] = cn
                else:
                    log.warning(f"沪深港通资金流向数据中缺少列: {en}")
            
            df = df.rename(columns=safe_columns_map)
            
            # 处理数据格式
            for col in ['net_amount', 'hk_sh', 'hk_sz', 'sh_hk', 'sz_hk', 'south_money', 'north_money']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 确保日期列格式一致
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            return df
        else:
            log.warning(f"未获取到 {date} 的沪深港通资金流向数据")
            return None
    except Exception as e:
        log.error(f"获取沪深港通资金流向数据异常: {str(e)}")
        return None


def fetch_moneyflow_stock(date=None):
    """
    获取指定日期个股资金流向数据
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: DataFrame，包含个股资金流向数据
    """
    try:
        if date is None:
            date = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
        
        # 使用akshare获取个股资金流向数据
        df = ak.stock_individual_fund_flow(date=date)
        
        if df is not None and len(df) > 0:
            # 重命名列
            columns_map = {
                '序号': 'index', '代码': 'code', '名称': 'name',
                '最新价': 'close', '涨跌幅': 'pct_chg',
                '今日主力净流入-净额': 'main_net_inflow',
                '今日主力净流入-净占比': 'main_net_inflow_ratio',
                '今日超大单净流入-净额': 'huge_net_inflow',
                '今日超大单净流入-净占比': 'huge_net_inflow_ratio',
                '今日大单净流入-净额': 'big_net_inflow',
                '今日大单净流入-净占比': 'big_net_inflow_ratio',
                '今日中单净流入-净额': 'medium_net_inflow',
                '今日中单净流入-净占比': 'medium_net_inflow_ratio',
                '今日小单净流入-净额': 'small_net_inflow',
                '今日小单净流入-净占比': 'small_net_inflow_ratio'
            }
            
            # 确保所有需要的列都存在，避免在迭代过程中修改字典
            safe_columns_map = {}
            for en, cn in columns_map.items():
                if en in df.columns:
                    safe_columns_map[en] = cn
                else:
                    log.warning(f"个股资金流向数据中缺少列: {en}")
            
            df = df.rename(columns=safe_columns_map)
            
            # 添加日期列
            df['date'] = date
            
            # 处理数据格式
            for col in ['close', 'pct_chg', 'main_net_inflow', 'main_net_inflow_ratio',
                        'huge_net_inflow', 'huge_net_inflow_ratio', 'big_net_inflow',
                        'big_net_inflow_ratio', 'medium_net_inflow', 'medium_net_inflow_ratio',
                        'small_net_inflow', 'small_net_inflow_ratio']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 去掉code列前缀的数字和点，例如1.600001转为600001
            if 'code' in df.columns and len(df) > 0 and '.' in str(df['code'].iloc[0]):
                df['code'] = df['code'].apply(lambda x: str(x).split('.')[-1])
            
            return df
        else:
            log.warning(f"未获取到 {date} 的个股资金流向数据")
            return None
    except Exception as e:
        log.error(f"获取个股资金流向数据异常: {str(e)}")
        return None


def fetch_moneyflow_sector(date=None):
    """
    获取指定日期板块资金流向数据
    
    :param date: 指定日期，格式为'YYYY-MM-DD'，默认为最近交易日
    :return: DataFrame，包含板块资金流向数据
    """
    try:
        if date is None:
            date = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
        
        # 使用akshare获取板块资金流向数据
        df = ak.stock_sector_fund_flow(date=date)
        
        if df is not None and len(df) > 0:
            # 重命名列
            columns_map = {
                '序号': 'index', '板块名称': 'name',
                '今日涨跌幅': 'pct_chg',
                '主力净流入-净额': 'main_net_inflow',
                '主力净流入-净占比': 'main_net_inflow_ratio',
                '超大单净流入-净额': 'huge_net_inflow',
                '超大单净流入-净占比': 'huge_net_inflow_ratio',
                '大单净流入-净额': 'big_net_inflow',
                '大单净流入-净占比': 'big_net_inflow_ratio',
                '中单净流入-净额': 'medium_net_inflow',
                '中单净流入-净占比': 'medium_net_inflow_ratio',
                '小单净流入-净额': 'small_net_inflow',
                '小单净流入-净占比': 'small_net_inflow_ratio'
            }
            
            # 确保所有需要的列都存在，避免在迭代过程中修改字典
            safe_columns_map = {}
            for en, cn in columns_map.items():
                if en in df.columns:
                    safe_columns_map[en] = cn
                else:
                    log.warning(f"板块资金流向数据中缺少列: {en}")
            
            df = df.rename(columns=safe_columns_map)
            
            # 添加日期列
            df['date'] = date
            
            # 处理数据格式
            for col in ['pct_chg', 'main_net_inflow', 'main_net_inflow_ratio',
                        'huge_net_inflow', 'huge_net_inflow_ratio', 'big_net_inflow',
                        'big_net_inflow_ratio', 'medium_net_inflow', 'medium_net_inflow_ratio',
                        'small_net_inflow', 'small_net_inflow_ratio']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
        else:
            log.warning(f"未获取到 {date} 的板块资金流向数据")
            return None
    except Exception as e:
        log.error(f"获取板块资金流向数据异常: {str(e)}")
        return None 