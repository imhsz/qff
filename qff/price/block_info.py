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
获取概念板块和行业板块数据及成分股模块
"""

import akshare as ak
import pandas as pd
import datetime
import time
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from qff.tools.logs import log
from qff.tools.date import get_real_trade_date
import os
from qff.price.finance import get_valuation

__all__ = ['fetch_concept_list', 'fetch_concept_stocks', 'fetch_concept_daily', 
           'fetch_industry_list', 'fetch_industry_stocks', 'fetch_industry_daily']


def create_session():
    """
    创建一个带有重试机制的HTTP会话
    
    :return: 配置好的requests.Session对象
    """
    session = requests.Session()
    
    # 配置重试策略
    retry_strategy = Retry(
        total=5,  # 最大重试次数
        backoff_factor=2,  # 重试间隔的指数因子
        status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的HTTP状态码
        allowed_methods=["GET", "POST"]  # 允许重试的HTTP方法
    )
    
    # 使用重试策略配置会话的适配器
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # 设置通用的User-Agent，模拟浏览器
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    })
    
    return session


def fetch_concept_list():
    """
    获取概念板块列表
    
    :return: DataFrame，包含板块代码、名称等信息
    """
    max_retries = 5
    retry_count = 0
    retry_delay = 2  # 初始延迟2秒
    
    # 首先尝试使用akshare的方法获取
    while retry_count < 2:  # 只尝试两次akshare方法
        try:
            # 添加随机延时
            random_delay = random.uniform(1, 3)
            time.sleep(random_delay)
            
            df = ak.stock_board_concept_name_em()
            
            if df is not None and len(df) > 0:
                # 处理数据...（保留原有处理逻辑）
                columns_map = {
                    '排名': 'index',
                    '板块名称': 'name',
                    '板块代码': 'code',
                    '最新价': 'close',
                    '涨跌额': 'change',
                    '涨跌幅': 'pct_chg',
                    '总市值': 'total_mv',
                    '换手率': 'turnover',
                    '上涨家数': 'up_count',
                    '下跌家数': 'down_count',
                    '领涨股票': 'lead_stock',
                    '领涨股票-涨跌幅': 'lead_stock_pct_chg'
                }
                
                safe_columns_map = {}
                for en, cn in columns_map.items():
                    if en in df.columns:
                        safe_columns_map[en] = cn
                    else:
                        log.warning(f"概念板块数据中缺少列: {en}")
                
                df = df.rename(columns=safe_columns_map)
                
                for col in ['close', 'change', 'pct_chg', 'total_mv', 'turnover', 'up_count', 'down_count', 'lead_stock_pct_chg']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df['date'] = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
                df['type'] = 'concept'
                
                return df
            else:
                log.warning("未通过akshare获取到概念板块列表数据")
                retry_count += 1
        except Exception as e:
            log.warning(f"通过akshare获取概念板块列表失败: {str(e)}")
            retry_count += 1
    
    # 如果akshare方法失败，使用自定义请求方法
    log.info("尝试使用自定义请求方法获取概念板块列表...")
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            # 创建带有重试机制的Session
            session = create_session()
            
            # 添加随机延时，模拟人类操作
            random_delay = random.uniform(2, 5)
            time.sleep(random_delay)
            
            # 直接访问东方财富概念板块网页
            url = "http://quote.eastmoney.com/center/boardlist.html#concept_board"
            response = session.get(url, timeout=30)
            
            if response.status_code == 200:
                # 使用BeautifulSoup解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 尝试多种方式解析数据
                try:
                    # 方法1: 从JavaScript中提取数据
                    import re
                    js_data = re.search(r'var\s+board_data\s*=\s*(\[.*?\]);', response.text, re.DOTALL)
                    
                    if js_data:
                        import json
                        board_data = json.loads(js_data.group(1))
                        
                        # 转换为DataFrame
                        df = pd.DataFrame(board_data)
                        
                        # 根据实际数据结构重命名列
                        if 'f14' in df.columns and 'f3' in df.columns:
                            df = df.rename(columns={
                                'f14': 'name',     # 板块名称
                                'f12': 'code',     # 板块代码
                                'f2': 'close',     # 最新价
                                'f4': 'change',    # 涨跌额
                                'f3': 'pct_chg',   # 涨跌幅
                                'f20': 'total_mv', # 总市值
                                'f8': 'turnover',  # 换手率
                                'f104': 'up_count',   # 上涨家数
                                'f105': 'down_count', # 下跌家数
                                'f128': 'lead_stock', # 领涨股票
                                'f136': 'lead_stock_pct_chg' # 领涨股票涨跌幅
                            })
                            
                            # 选择需要的列
                            columns = [col for col in ['name', 'code', 'close', 'change', 'pct_chg', 
                                     'total_mv', 'turnover', 'up_count', 'down_count', 
                                     'lead_stock', 'lead_stock_pct_chg'] if col in df.columns]
                            df = df[columns]
                            
                            # 处理数据格式
                            for col in ['close', 'change', 'pct_chg', 'total_mv', 'turnover', 
                                         'up_count', 'down_count', 'lead_stock_pct_chg']:
                                if col in df.columns:
                                    df[col] = pd.to_numeric(df[col], errors='coerce')
                            
                            # 添加索引列
                            df['index'] = range(1, len(df) + 1)
                            
                            # 添加日期和类型
                            df['date'] = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
                            df['type'] = 'concept'
                            
                            return df
                    else:
                        log.warning("无法从JavaScript中提取概念板块数据")
                    
                    # 方法2: 尝试直接从表格解析
                    tables = soup.find_all('table')
                    if tables:
                        log.info(f"找到{len(tables)}个表格，尝试解析")
                        for i, table in enumerate(tables):
                            try:
                                # 使用pandas从HTML表格解析
                                table_df = pd.read_html(str(table))
                                if table_df and len(table_df) > 0:
                                    df = table_df[0]
                                    log.info(f"成功从表格{i+1}解析数据，列: {df.columns.tolist()}")
                                    
                                    # 检查是否包含必要的列
                                    if '板块名称' in df.columns and '板块代码' in df.columns:
                                        # 重命名列
                                        columns_map = {
                                            '排名': 'index',
                                            '板块名称': 'name',
                                            '板块代码': 'code',
                                            '最新价': 'close',
                                            '涨跌额': 'change',
                                            '涨跌幅': 'pct_chg',
                                            '总市值': 'total_mv',
                                            '换手率': 'turnover',
                                            '上涨家数': 'up_count',
                                            '下跌家数': 'down_count',
                                            '领涨股票': 'lead_stock',
                                            '领涨股票-涨跌幅': 'lead_stock_pct_chg'
                                        }
                                        
                                        # 仅重命名存在的列
                                        safe_columns_map = {k: v for k, v in columns_map.items() if k in df.columns}
                                        df = df.rename(columns=safe_columns_map)
                                        
                                        # 处理数据格式
                                        for col in ['close', 'change', 'pct_chg', 'total_mv', 'turnover', 
                                                    'up_count', 'down_count', 'lead_stock_pct_chg']:
                                            if col in df.columns:
                                                df[col] = pd.to_numeric(df[col], errors='coerce')
                                        
                                        # 添加日期和类型
                                        df['date'] = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
                                        df['type'] = 'concept'
                                        
                                        return df
                            except Exception as table_e:
                                log.warning(f"解析表格{i+1}失败: {str(table_e)}")
                                continue
                    
                    # 保存HTML内容以供调试
                    debug_path = os.path.join(os.path.expanduser('~'), '.qff', 'debug')
                    os.makedirs(debug_path, exist_ok=True)
                    with open(os.path.join(debug_path, 'concept_html.txt'), 'w', encoding='utf-8') as f:
                        f.write(response.text[:10000])  # 保存前10000个字符用于调试
                    log.info(f"已保存HTML内容到: {os.path.join(debug_path, 'concept_html.txt')}")
                        
                except Exception as parse_e:
                    log.error(f"解析概念板块HTML失败: {str(parse_e)}")
            
            log.warning(f"自定义请求获取概念板块列表失败，状态码: {response.status_code}")
            retry_count += 1
            time.sleep(retry_delay)
            retry_delay = retry_delay * 2
        except Exception as e:
            log.warning(f"自定义请求获取概念板块列表失败: {str(e)}")
            retry_count += 1
            time.sleep(retry_delay)
            retry_delay = retry_delay * 2
            
    # 如果自定义方法也失败，则尝试使用备用数据源
    try:
        log.info("尝试使用备用数据源获取概念板块列表...")
        
        # 示例：使用本地缓存的概念板块数据（如果有）
        try:
            # 尝试从本地缓存加载（需要实现相应的缓存机制）
            from qff.tools.cache import get_cached_data
            cached_data = get_cached_data('concept_list')
            if cached_data is not None:
                log.info("成功从缓存加载概念板块列表数据")
                return cached_data
        except:
            pass
        
        # 如果没有缓存或无法加载，可以返回一个最基本的概念板块列表
        log.warning("使用硬编码的基本概念板块列表作为最后的备用选项")
        
        # 创建一个基本的概念板块DataFrame（包含常用概念）
        basic_concepts = [
            {'code': 'BK0638', 'name': '人工智能'},
            {'code': 'BK0644', 'name': '大数据'},
            {'code': 'BK0579', 'name': '云计算'},
            {'code': 'BK0662', 'name': '物联网'},
            {'code': 'BK0635', 'name': '区块链'},
            {'code': 'BK0493', 'name': '新能源汽车'},
            {'code': 'BK0666', 'name': '5G概念'},
            {'code': 'BK0712', 'name': '特斯拉'},
            {'code': 'BK0536', 'name': '智能电网'},
            {'code': 'BK0427', 'name': '新能源'}
        ]
        
        df = pd.DataFrame(basic_concepts)
        df['date'] = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
        df['type'] = 'concept'
        df['close'] = 0.0
        df['change'] = 0.0
        df['pct_chg'] = 0.0
        df['total_mv'] = 0.0
        df['turnover'] = 0.0
        df['up_count'] = 0
        df['down_count'] = 0
        df['lead_stock'] = ''
        df['lead_stock_pct_chg'] = 0.0
        df['index'] = range(1, len(df) + 1)
        
        log.warning("返回硬编码的基本概念板块数据，仅用于系统正常运行")
        return df
        
    except Exception as backup_e:
        log.error(f"使用备用数据源获取概念板块列表失败: {str(backup_e)}")
        return None
    
    log.error("所有获取概念板块列表的方法都失败")
    return None


def fetch_concept_stocks(concept_code):
    """
    获取指定概念板块的成分股
    
    :param concept_code: 概念板块代码
    :return: DataFrame，包含成分股信息
    """
    try:
        # 使用akshare获取概念板块成分股
        df = ak.stock_board_concept_cons_em(symbol=concept_code)
        
        if df is not None and len(df) > 0:
            # 重命名列
            columns_map = {
                '序号': 'index', '代码': 'code', '名称': 'name',
                '最新价': 'close', '涨跌幅': 'pct_chg', '成交额': 'amount',
                '换手率': 'turnover', '流通市值': 'circ_mv', 
                '市盈率-动态': 'pe_ttm', '所属行业': 'industry'
            }
            
            # 确保所有需要的列都存在，避免在迭代过程中修改字典
            safe_columns_map = {}
            for en, cn in columns_map.items():
                if en in df.columns:
                    safe_columns_map[en] = cn
                else:
                    log.warning(f"概念板块成分股数据中缺少列: {en}")
            
            df = df.rename(columns=safe_columns_map)

            # 正向补全流通市值（历史）
            if 'circ_mv' not in df.columns and 'code' in df.columns and 'date' in df.columns:
                try:
                    codes = df['code'].apply(lambda x: str(x).split('.')[-1]).tolist()
                    date = df['date'].iloc[0] if df['date'].nunique() == 1 else None
                    if date:
                        val_df = get_valuation(codes, start=date, end=date, fields=['circulating_market_cap'])
                        if val_df is not None and len(val_df) > 0:
                            val_df['code'] = val_df['code'].apply(lambda x: str(x).split('.')[-1])
                            val_map = dict(zip(val_df['code'], val_df['circulating_market_cap']))
                            if val_map:
                                df['circ_mv'] = codes.map(val_map)
                            else:
                                df['circ_mv'] = None
                        else:
                            raise Exception('get_valuation返回空')
                    else:
                        # 多日期情况，逐行补全
                        circ_mv_list = []
                        for idx, row in df.iterrows():
                            val_df = get_valuation([row['code']], start=row['date'], end=row['date'], fields=['circulating_market_cap'])
                            if val_df is not None and len(val_df) > 0:
                                circ_mv_list.append(val_df.iloc[0]['circulating_market_cap'])
                            else:
                                circ_mv_list.append(pd.NA)
                        df['circ_mv'] = circ_mv_list
                except Exception as e:
                    log.warning(f"历史流通市值补全失败: {e}, 尝试用最新市值")
                    try:
                        codes = df['code'].apply(lambda x: str(x).split('.')[-1])
                        mv_df = ak.stock_a_lg_indicator_em()
                        if '流通市值' in mv_df.columns and '代码' in mv_df.columns:
                            mv_map = dict(zip(mv_df['代码'], mv_df['流通市值']))
                        else:
                            mv_map = {}
                            log.warning("流通市值字段缺失，无法补全流通市值")
                        if mv_map:
                            df['circ_mv'] = codes.map(mv_map)
                        else:
                            df['circ_mv'] = None
                    except Exception as e2:
                        log.warning(f"补全最新流通市值也失败: {e2}")
                        df['circ_mv'] = pd.NA

            # 正向补全所属行业
            if 'industry' not in df.columns and 'code' in df.columns:
                try:
                    codes = df['code'].apply(lambda x: str(x).split('.')[-1])
                    industry_df = ak.stock_board_industry_cons_em(symbol="全部")
                    if '所属行业' in industry_df.columns and '代码' in industry_df.columns:
                        ind_map = dict(zip(industry_df['代码'], industry_df['所属行业']))
                    else:
                        ind_map = {}
                        log.warning("所属行业字段缺失，无法补全所属行业")
                    if ind_map:
                        df['industry'] = codes.map(ind_map)
                    else:
                        df['industry'] = None
                except Exception as e:
                    log.warning(f"补全所属行业失败: {e}")
                    df['industry'] = pd.NA

            # 处理数据格式
            for col in ['close', 'pct_chg', 'amount', 'turnover', 'circ_mv', 'pe_ttm']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
            # 添加板块代码列
            df['block_code'] = concept_code
            
            # 添加板块类型列
            df['block_type'] = 'concept'
            
            # 添加日期列
            df['date'] = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
            
            # 去掉code列前缀的数字和点，例如1.600001转为600001
            if 'code' in df.columns and len(df) > 0 and '.' in str(df['code'].iloc[0]):
                df['code'] = df['code'].apply(lambda x: str(x).split('.')[-1])
            
            return df
        else:
            log.warning(f"未获取到概念板块 {concept_code} 的成分股数据")
            return None
    except Exception as e:
        log.error(f"获取概念板块 {concept_code} 成分股异常: {str(e)}")
        return None


def fetch_concept_daily(concept_code, start_date=None, end_date=None):
    """
    获取指定概念板块的日线数据
    
    :param concept_code: 概念板块代码
    :param start_date: 开始日期，格式为'YYYY-MM-DD'，默认为前60个交易日
    :param end_date: 结束日期，格式为'YYYY-MM-DD'，默认为当前日期
    :return: DataFrame，包含板块日线数据
    """
    max_retries = 5  # 增加重试次数
    retry_count = 0
    retry_delay = 2  # 初始延迟2秒
    
    try:
        if end_date is None:
            end_date = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
        
        if start_date is None:
            # 默认获取近60个交易日的数据
            start_date = (datetime.datetime.strptime(end_date, '%Y-%m-%d') - datetime.timedelta(days=120)).strftime('%Y-%m-%d')
        
        # 首先需要获取概念板块代码对应的名称
        concept_name = None
        try:
            concept_list_df = fetch_concept_list()
            if concept_list_df is not None and len(concept_list_df) > 0:
                # 查找对应的概念板块名称
                filtered_df = concept_list_df[concept_list_df['code'] == concept_code]
                if len(filtered_df) > 0:
                    concept_name = filtered_df.iloc[0]['name']
                    log.info(f"找到概念板块 {concept_code} 对应的名称: {concept_name}")
                else:
                    log.warning(f"在概念板块列表中未找到代码 {concept_code} 对应的名称")
                    return None
            else:
                log.warning("获取概念板块列表失败，无法找到概念板块名称")
                return None
        except Exception as e:
            log.warning(f"获取概念板块名称时出错: {str(e)}")
            return None
        
        # 将日期格式从YYYY-MM-DD转为YYYYMMDD
        start_date_fmt = start_date.replace('-', '')
        end_date_fmt = end_date.replace('-', '')
        
        # 使用概念板块名称获取日线数据，添加重试机制
        while retry_count < max_retries:
            try:
                # 添加随机延时
                random_delay = random.uniform(1, 3)
                time.sleep(random_delay)
                
                df = ak.stock_board_concept_hist_em(symbol=concept_name, period="daily", 
                                            start_date=start_date_fmt, end_date=end_date_fmt)
                
                if df is not None and len(df) > 0:
                    # 重命名列
                    columns_map = {
                        '日期': 'date', 
                        '开盘': 'open', 
                        '收盘': 'close',
                        '最高': 'high', 
                        '最低': 'low', 
                        '成交量': 'volume',
                        '成交额': 'amount', 
                        '涨跌幅': 'pct_chg',
                        '涨跌额': 'change',
                        '振幅': 'amplitude',
                        '换手率': 'turnover'
                    }
                    
                    # 确保所有需要的列都存在，避免在迭代过程中修改字典
                    safe_columns_map = {}
                    for en, cn in columns_map.items():
                        if en in df.columns:
                            safe_columns_map[en] = cn
                        else:
                            log.warning(f"概念板块日线数据中缺少列: {en}")
                    
                    # 只有当有列可以重命名时才进行重命名
                    if safe_columns_map:
                        df = df.rename(columns=safe_columns_map)
                    
                    # 处理数据格式
                    for col in ['open', 'close', 'high', 'low', 'volume', 'amount', 'pct_chg', 
                               'change', 'amplitude', 'turnover']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # 添加板块代码列
                    df['block_code'] = concept_code
                    
                    # 添加板块类型列
                    df['block_type'] = 'concept'
                    
                    # 确保日期列格式一致
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                    
                    return df
                else:
                    log.warning(f"未获取到概念板块 {concept_name}({concept_code}) 的日线数据")
                    retry_count += 1
                    if retry_count < max_retries:
                        log.info(f"尝试重新获取概念板块日线数据，第 {retry_count} 次重试")
                        time.sleep(retry_delay)
                        retry_delay = retry_delay * 2  # 指数退避，增加延迟
                    else:
                        return None
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    log.warning(f"获取概念板块日线数据失败，正在进行第 {retry_count} 次重试: {str(e)}")
                    time.sleep(retry_delay)
                    retry_delay = retry_delay * 2  # 指数退避，增加延迟
                else:
                    log.error(f"获取概念板块 {concept_code} 日线数据异常，已重试 {max_retries} 次: {str(e)}")
                    return None
        
        return None
    except Exception as e:
        log.error(f"获取概念板块 {concept_code} 日线数据异常: {str(e)}")
        return None


def fetch_industry_list():
    """
    获取行业板块列表
    
    :return: DataFrame，包含板块代码、名称等信息
    """
    max_retries = 5
    retry_count = 0
    retry_delay = 2  # 初始延迟2秒
    
    # 首先尝试使用akshare的方法获取
    while retry_count < 2:  # 只尝试两次akshare方法
        try:
            # 添加随机延时
            random_delay = random.uniform(1, 3)
            time.sleep(random_delay)
            
            df = ak.stock_board_industry_name_em()
            
            if df is not None and len(df) > 0:
                # 处理数据...（保留原有处理逻辑）
                columns_map = {
                    '排名': 'index',
                    '板块名称': 'name',
                    '板块代码': 'code',
                    '最新价': 'close',
                    '涨跌额': 'change',
                    '涨跌幅': 'pct_chg',
                    '总市值': 'total_mv',
                    '换手率': 'turnover',
                    '上涨家数': 'up_count',
                    '下跌家数': 'down_count',
                    '领涨股票': 'lead_stock',
                    '领涨股票-涨跌幅': 'lead_stock_pct_chg'
                }
                
                safe_columns_map = {}
                for en, cn in columns_map.items():
                    if en in df.columns:
                        safe_columns_map[en] = cn
                    else:
                        log.warning(f"行业板块数据中缺少列: {en}")
                
                df = df.rename(columns=safe_columns_map)
                
                for col in ['close', 'change', 'pct_chg', 'total_mv', 'turnover', 'up_count', 'down_count', 'lead_stock_pct_chg']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df['date'] = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
                df['type'] = 'industry'
                
                return df
            else:
                log.warning("未通过akshare获取到行业板块列表数据")
                retry_count += 1
        except Exception as e:
            log.warning(f"通过akshare获取行业板块列表失败: {str(e)}")
            retry_count += 1
    
    # 如果akshare方法失败，使用自定义请求方法
    log.info("尝试使用自定义请求方法获取行业板块列表...")
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            # 创建带有重试机制的Session
            session = create_session()
            
            # 添加随机延时，模拟人类操作
            random_delay = random.uniform(2, 5)
            time.sleep(random_delay)
            
            # 直接访问东方财富行业板块网页
            url = "http://quote.eastmoney.com/center/boardlist.html#industry_board"
            response = session.get(url, timeout=30)
            
            if response.status_code == 200:
                # 使用BeautifulSoup解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 尝试多种方式解析数据
                try:
                    # 方法1: 从JavaScript中提取数据
                    import re
                    js_data = re.search(r'var\s+board_data\s*=\s*(\[.*?\]);', response.text, re.DOTALL)
                    
                    if js_data:
                        import json
                        board_data = json.loads(js_data.group(1))
                        
                        # 转换为DataFrame
                        df = pd.DataFrame(board_data)
                        
                        # 根据实际数据结构重命名列
                        if 'f14' in df.columns and 'f3' in df.columns:
                            df = df.rename(columns={
                                'f14': 'name',     # 板块名称
                                'f12': 'code',     # 板块代码
                                'f2': 'close',     # 最新价
                                'f4': 'change',    # 涨跌额
                                'f3': 'pct_chg',   # 涨跌幅
                                'f20': 'total_mv', # 总市值
                                'f8': 'turnover',  # 换手率
                                'f104': 'up_count',   # 上涨家数
                                'f105': 'down_count', # 下跌家数
                                'f128': 'lead_stock', # 领涨股票
                                'f136': 'lead_stock_pct_chg' # 领涨股票涨跌幅
                            })
                            
                            # 选择需要的列
                            columns = [col for col in ['name', 'code', 'close', 'change', 'pct_chg', 
                                     'total_mv', 'turnover', 'up_count', 'down_count', 
                                     'lead_stock', 'lead_stock_pct_chg'] if col in df.columns]
                            df = df[columns]
                            
                            # 处理数据格式
                            for col in ['close', 'change', 'pct_chg', 'total_mv', 'turnover', 
                                         'up_count', 'down_count', 'lead_stock_pct_chg']:
                                if col in df.columns:
                                    df[col] = pd.to_numeric(df[col], errors='coerce')
                            
                            # 添加索引列
                            df['index'] = range(1, len(df) + 1)
                            
                            # 添加日期和类型
                            df['date'] = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
                            df['type'] = 'industry'
                            
                            return df
                    else:
                        log.warning("无法从JavaScript中提取行业板块数据")
                    
                    # 方法2: 尝试直接从表格解析
                    tables = soup.find_all('table')
                    if tables:
                        log.info(f"找到{len(tables)}个表格，尝试解析")
                        for i, table in enumerate(tables):
                            try:
                                # 使用pandas从HTML表格解析
                                table_df = pd.read_html(str(table))
                                if table_df and len(table_df) > 0:
                                    df = table_df[0]
                                    log.info(f"成功从表格{i+1}解析数据，列: {df.columns.tolist()}")
                                    
                                    # 检查是否包含必要的列
                                    if '板块名称' in df.columns and '板块代码' in df.columns:
                                        # 重命名列
                                        columns_map = {
                                            '排名': 'index',
                                            '板块名称': 'name',
                                            '板块代码': 'code',
                                            '最新价': 'close',
                                            '涨跌额': 'change',
                                            '涨跌幅': 'pct_chg',
                                            '总市值': 'total_mv',
                                            '换手率': 'turnover',
                                            '上涨家数': 'up_count',
                                            '下跌家数': 'down_count',
                                            '领涨股票': 'lead_stock',
                                            '领涨股票-涨跌幅': 'lead_stock_pct_chg'
                                        }
                                        
                                        # 仅重命名存在的列
                                        safe_columns_map = {k: v for k, v in columns_map.items() if k in df.columns}
                                        df = df.rename(columns=safe_columns_map)
                                        
                                        # 处理数据格式
                                        for col in ['close', 'change', 'pct_chg', 'total_mv', 'turnover', 
                                                    'up_count', 'down_count', 'lead_stock_pct_chg']:
                                            if col in df.columns:
                                                df[col] = pd.to_numeric(df[col], errors='coerce')
                                        
                                        # 添加日期和类型
                                        df['date'] = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
                                        df['type'] = 'industry'
                                        
                                        return df
                            except Exception as table_e:
                                log.warning(f"解析表格{i+1}失败: {str(table_e)}")
                                continue
                    
                    # 保存HTML内容以供调试
                    debug_path = os.path.join(os.path.expanduser('~'), '.qff', 'debug')
                    os.makedirs(debug_path, exist_ok=True)
                    with open(os.path.join(debug_path, 'industry_html.txt'), 'w', encoding='utf-8') as f:
                        f.write(response.text[:10000])  # 保存前10000个字符用于调试
                    log.info(f"已保存HTML内容到: {os.path.join(debug_path, 'industry_html.txt')}")
                        
                except Exception as parse_e:
                    log.error(f"解析行业板块HTML失败: {str(parse_e)}")
            
            log.warning(f"自定义请求获取行业板块列表失败，状态码: {response.status_code}")
            retry_count += 1
            time.sleep(retry_delay)
            retry_delay = retry_delay * 2
        except Exception as e:
            log.warning(f"自定义请求获取行业板块列表失败: {str(e)}")
            retry_count += 1
            time.sleep(retry_delay)
            retry_delay = retry_delay * 2
            
    # 如果自定义方法也失败，则尝试使用备用数据源
    try:
        log.info("尝试使用备用数据源获取行业板块列表...")
        
        # 这里可以添加备用数据源的获取逻辑
        # 例如，使用tushare、baostock等其他金融数据API
        # 或者使用预先保存的行业板块列表（作为最后的备用选项）
        
        # 示例：使用本地缓存的行业板块数据（如果有）
        try:
            # 尝试从本地缓存加载（需要实现相应的缓存机制）
            from qff.tools.cache import get_cached_data
            cached_data = get_cached_data('industry_list')
            if cached_data is not None:
                log.info("成功从缓存加载行业板块列表数据")
                return cached_data
        except:
            pass
        
        # 如果没有缓存或无法加载，可以返回一个最基本的行业板块列表
        # 这只是一个应急方案，用于系统正常运行
        log.warning("使用硬编码的基本行业板块列表作为最后的备用选项")
        
        # 创建一个基本的行业板块DataFrame（包含最常用的行业）
        basic_industries = [
            {'code': 'BK0428', 'name': '医药制造'},
            {'code': 'BK0475', 'name': '银行'},
            {'code': 'BK0447', 'name': '房地产'},
            {'code': 'BK0437', 'name': '证券'},
            {'code': 'BK0438', 'name': '保险'},
            {'code': 'BK0429', 'name': '电子元件'},
            {'code': 'BK0456', 'name': '软件服务'},
            {'code': 'BK0427', 'name': '煤炭'},
            {'code': 'BK0736', 'name': '通信设备'},
            {'code': 'BK0451', 'name': '汽车整车'}
        ]
        
        df = pd.DataFrame(basic_industries)
        df['date'] = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
        df['type'] = 'industry'
        df['close'] = 0.0
        df['change'] = 0.0
        df['pct_chg'] = 0.0
        df['total_mv'] = 0.0
        df['turnover'] = 0.0
        df['up_count'] = 0
        df['down_count'] = 0
        df['lead_stock'] = ''
        df['lead_stock_pct_chg'] = 0.0
        df['index'] = range(1, len(df) + 1)
        
        log.warning("返回硬编码的基本行业板块数据，仅用于系统正常运行")
        return df
        
    except Exception as backup_e:
        log.error(f"使用备用数据源获取行业板块列表失败: {str(backup_e)}")
        return None
    
    log.error("所有获取行业板块列表的方法都失败")
    return None


def fetch_industry_stocks(industry_code):
    """
    获取指定行业板块的成分股
    
    :param industry_code: 行业板块代码
    :return: DataFrame，包含成分股信息
    """
    try:
        # 使用akshare获取行业板块成分股
        df = ak.stock_board_industry_cons_em(symbol=industry_code)
        
        if df is not None and len(df) > 0:
            # 重命名列
            columns_map = {
                '序号': 'index', '代码': 'code', '名称': 'name',
                '最新价': 'close', '涨跌幅': 'pct_chg', '成交额': 'amount',
                '换手率': 'turnover', '流通市值': 'circ_mv', 
                '市盈率-动态': 'pe_ttm', '所属行业': 'industry'
            }
            
            # 确保所有需要的列都存在，避免在迭代过程中修改字典
            safe_columns_map = {}
            for en, cn in columns_map.items():
                if en in df.columns:
                    safe_columns_map[en] = cn
                else:
                    log.warning(f"行业板块成分股数据中缺少列: {en}")
            
            df = df.rename(columns=safe_columns_map)
            
            # 处理数据格式
            for col in ['close', 'pct_chg', 'amount', 'turnover', 'circ_mv', 'pe_ttm']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
            # 添加板块代码列
            df['block_code'] = industry_code
            
            # 添加板块类型列
            df['block_type'] = 'industry'
            
            # 添加日期列
            df['date'] = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
            
            # 去掉code列前缀的数字和点，例如1.600001转为600001
            if 'code' in df.columns and len(df) > 0 and '.' in str(df['code'].iloc[0]):
                df['code'] = df['code'].apply(lambda x: str(x).split('.')[-1])
            
            return df
        else:
            log.warning(f"未获取到行业板块 {industry_code} 的成分股数据")
            return None
    except Exception as e:
        log.error(f"获取行业板块 {industry_code} 成分股异常: {str(e)}")
        return None


def fetch_industry_daily(industry_code, start_date=None, end_date=None):
    """
    获取指定行业板块的日线数据
    
    :param industry_code: 行业板块代码
    :param start_date: 开始日期，格式为'YYYY-MM-DD'，默认为前60个交易日
    :param end_date: 结束日期，格式为'YYYY-MM-DD'，默认为当前日期
    :return: DataFrame，包含板块日线数据
    """
    max_retries = 5  # 增加重试次数
    retry_count = 0
    retry_delay = 2  # 初始延迟2秒
    
    try:
        if end_date is None:
            end_date = get_real_trade_date(datetime.date.today().strftime('%Y-%m-%d'))
            
        if start_date is None:
            # 默认获取近60个交易日的数据
            start_date = (datetime.datetime.strptime(end_date, '%Y-%m-%d') - datetime.timedelta(days=120)).strftime('%Y-%m-%d')
        
        # 首先需要获取行业板块代码对应的名称
        industry_name = None
        try:
            industry_list_df = fetch_industry_list()
            if industry_list_df is not None and len(industry_list_df) > 0:
                # 查找对应的行业板块名称
                filtered_df = industry_list_df[industry_list_df['code'] == industry_code]
                if len(filtered_df) > 0:
                    industry_name = filtered_df.iloc[0]['name']
                    log.info(f"找到行业板块 {industry_code} 对应的名称: {industry_name}")
                else:
                    log.warning(f"在行业板块列表中未找到代码 {industry_code} 对应的名称")
                    return None
            else:
                log.warning("获取行业板块列表失败，无法找到行业板块名称")
                return None
        except Exception as e:
            log.warning(f"获取行业板块名称时出错: {str(e)}")
            return None
        
        # 将日期格式从YYYY-MM-DD转为YYYYMMDD
        start_date_fmt = start_date.replace('-', '')
        end_date_fmt = end_date.replace('-', '')
        
        # 使用行业板块名称获取日线数据，添加重试机制
        while retry_count < max_retries:
            try:
                # 添加随机延时
                random_delay = random.uniform(1, 3)
                time.sleep(random_delay)
                
                df = ak.stock_board_industry_hist_em(symbol=industry_name, 
                                            start_date=start_date_fmt, 
                                            end_date=end_date_fmt,
                                            period="日k")
                
                if df is not None and len(df) > 0:
                    # 重命名列
                    columns_map = {
                        '日期': 'date', 
                        '开盘': 'open', 
                        '收盘': 'close',
                        '最高': 'high', 
                        '最低': 'low', 
                        '成交量': 'volume',
                        '成交额': 'amount', 
                        '涨跌幅': 'pct_chg',
                        '涨跌额': 'change',
                        '振幅': 'amplitude',
                        '换手率': 'turnover'
                    }
                    
                    # 确保所有需要的列都存在，避免在迭代过程中修改字典
                    safe_columns_map = {}
                    for en, cn in columns_map.items():
                        if en in df.columns:
                            safe_columns_map[en] = cn
                        else:
                            log.warning(f"行业板块日线数据中缺少列: {en}")
                    
                    # 只有当有列可以重命名时才进行重命名
                    if safe_columns_map:
                        df = df.rename(columns=safe_columns_map)
                    
                    # 处理数据格式
                    for col in ['open', 'close', 'high', 'low', 'volume', 'amount', 'pct_chg', 
                                'change', 'amplitude', 'turnover']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # 添加板块代码列
                    df['block_code'] = industry_code
                    
                    # 添加板块类型列
                    df['block_type'] = 'industry'
                    
                    # 确保日期列格式一致
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                    
                    return df
                else:
                    log.warning(f"未获取到行业板块 {industry_name}({industry_code}) 的日线数据")
                    retry_count += 1
                    if retry_count < max_retries:
                        log.info(f"尝试重新获取行业板块日线数据，第 {retry_count} 次重试")
                        time.sleep(retry_delay)
                        retry_delay = retry_delay * 2  # 指数退避，增加延迟
                    else:
                        return None
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    log.warning(f"获取行业板块日线数据失败，正在进行第 {retry_count} 次重试: {str(e)}")
                    time.sleep(retry_delay)
                    retry_delay = retry_delay * 2  # 指数退避，增加延迟
                else:
                    log.error(f"获取行业板块 {industry_code} 日线数据异常，已重试 {max_retries} 次: {str(e)}")
                    return None
        
        return None
    except Exception as e:
        log.error(f"获取行业板块 {industry_code} 日线数据异常: {str(e)}")
        return None 