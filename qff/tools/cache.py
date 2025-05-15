"""
缓存模块，用于在API获取数据失败时提供本地缓存功能
"""

import os
import pandas as pd
import pickle
import datetime
import time
from qff.tools.logs import log
from qff.tools.config import get_config
from qff.tools.date import get_real_trade_date

# 缓存文件的默认存储目录
try:
    cache_dir = get_config('cache_dir', os.path.join(os.path.expanduser('~'), '.qff', 'cache'))
    if cache_dir is None:  # 确保配置不为None
        cache_dir = os.path.join(os.path.expanduser('~'), '.qff', 'cache')
        log.warning(f"缓存目录配置为None，使用默认目录: {cache_dir}")
    CACHE_DIR = cache_dir
except Exception as e:
    # 如果发生任何错误，使用硬编码的默认目录
    CACHE_DIR = os.path.join(os.path.expanduser('~'), '.qff', 'cache')
    log.warning(f"获取缓存目录配置出错: {str(e)}，使用默认目录: {CACHE_DIR}")

# 缓存有效期（秒）
CACHE_MAX_AGE = {
    'industry_list': 86400,   # 1天
    'concept_list': 86400,    # 1天
    'industry_stocks': 86400, # 1天
    'concept_stocks': 86400,  # 1天
    'industry_daily': 3600,   # 1小时
    'concept_daily': 3600     # 1小时
}


def ensure_cache_dir():
    """确保缓存目录存在"""
    if not os.path.exists(CACHE_DIR):
        try:
            os.makedirs(CACHE_DIR)
            log.info(f"创建缓存目录：{CACHE_DIR}")
        except Exception as e:
            log.error(f"创建缓存目录失败：{str(e)}")
            return False
    return True


def get_cache_path(cache_key):
    """获取缓存文件路径"""
    return os.path.join(CACHE_DIR, f"{cache_key}.pkl")


def save_data_to_cache(data, cache_key):
    """
    将数据保存到缓存
    
    :param data: 要缓存的数据（通常是DataFrame）
    :param cache_key: 缓存键名
    :return: 是否成功缓存
    """
    if data is None:
        log.warning(f"尝试缓存空数据，跳过缓存：{cache_key}")
        return False
        
    if not ensure_cache_dir():
        return False
    
    cache_path = get_cache_path(cache_key)
    
    try:
        # 创建缓存数据结构
        cache_data = {
            'data': data,
            'timestamp': time.time(),
            'datetime': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 保存到文件
        with open(cache_path, 'wb') as f:
            pickle.dump(cache_data, f)
            
        log.info(f"数据已缓存到：{cache_path}")
        return True
    except Exception as e:
        log.error(f"缓存数据失败：{str(e)}")
        return False


def get_cached_data(cache_key, max_age=None):
    """
    从缓存获取数据
    
    :param cache_key: 缓存键名
    :param max_age: 最大缓存年龄（秒），如果为None则使用默认值
    :return: 缓存的数据，如果缓存不存在或已过期则返回None
    """
    cache_path = get_cache_path(cache_key)
    
    if not os.path.exists(cache_path):
        log.info(f"缓存不存在：{cache_path}")
        return None
    
    try:
        with open(cache_path, 'rb') as f:
            cache_data = pickle.load(f)
        
        # 获取缓存时间戳
        timestamp = cache_data.get('timestamp', 0)
        cached_datetime = cache_data.get('datetime', 'unknown')
        
        # 计算缓存时间
        cache_age = time.time() - timestamp
        
        # 确定最大缓存年龄
        if max_age is None:
            max_age = CACHE_MAX_AGE.get(cache_key, 3600)  # 默认1小时
        
        # 检查缓存是否过期
        if cache_age > max_age:
            log.info(f"缓存已过期（{cache_age:.1f}秒），最大期限：{max_age}秒，缓存时间：{cached_datetime}")
            return None
        
        log.info(f"使用缓存数据（{cache_age:.1f}秒前缓存，有效期：{max_age}秒）：{cache_path}")
        return cache_data.get('data')
    except Exception as e:
        log.error(f"读取缓存失败：{str(e)}")
        return None


def clear_cache(cache_key=None):
    """
    清除缓存
    
    :param cache_key: 要清除的缓存键名，如果为None则清除所有缓存
    :return: 是否成功清除
    """
    if not ensure_cache_dir():
        return False
    
    try:
        if cache_key is None:
            # 清除所有缓存
            file_count = 0
            for filename in os.listdir(CACHE_DIR):
                if filename.endswith('.pkl'):
                    os.remove(os.path.join(CACHE_DIR, filename))
                    file_count += 1
            log.info(f"已清除所有缓存文件，共{file_count}个")
        else:
            # 清除特定缓存
            cache_path = get_cache_path(cache_key)
            if os.path.exists(cache_path):
                os.remove(cache_path)
                log.info(f"已清除缓存：{cache_path}")
            else:
                log.info(f"缓存不存在，无需清除：{cache_path}")
        return True
    except Exception as e:
        log.error(f"清除缓存失败：{str(e)}")
        return False


def init_cache_data():
    """
    初始化基础缓存数据，确保第一次运行时也能有基础数据
    主要用于克服API不稳定的问题
    """
    try:
        if not ensure_cache_dir():
            log.warning("缓存目录创建失败，跳过初始化缓存数据")
            return False
        
        # 获取当前交易日
        try:
            current_date = get_real_trade_date(datetime.datetime.now().strftime('%Y-%m-%d'))
        except Exception as e:
            log.warning(f"获取当前交易日失败: {str(e)}，使用当前日期代替")
            current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 检查行业板块列表缓存是否存在
        industry_list_cache = get_cache_path('industry_list')
        if not os.path.exists(industry_list_cache):
            log.info("初始化行业板块列表缓存...")
            
            try:
                # 创建一个基本的行业板块DataFrame
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
                df['date'] = current_date
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
                
                save_data_to_cache(df, 'industry_list')
                log.info("行业板块列表缓存初始化成功")
            except Exception as e:
                log.error(f"初始化行业板块列表缓存失败: {str(e)}")
        
        # 检查概念板块列表缓存是否存在
        concept_list_cache = get_cache_path('concept_list')
        if not os.path.exists(concept_list_cache):
            log.info("初始化概念板块列表缓存...")
            
            try:
                # 创建一个基本的概念板块DataFrame
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
                df['date'] = current_date
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
                
                save_data_to_cache(df, 'concept_list')
                log.info("概念板块列表缓存初始化成功")
            except Exception as e:
                log.error(f"初始化概念板块列表缓存失败: {str(e)}")
        
        return True
    except Exception as e:
        log.error(f"初始化缓存数据时发生未知错误: {str(e)}")
        return False 