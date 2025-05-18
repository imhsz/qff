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

# 基于Pytdx的数据接口,好处是可以在linux/mac上联入通达信行情
# 具体参见rainx的pytdx(https://github.com/rainx/pytdx)

from datetime import datetime, timedelta
from pytdx.hq import TdxHq_API
from qff.tools.config import get_config, set_config
from qff.tools.logs import log
import json
import time
import pandas as pd
import numpy as np
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

# 全局服务器缓存，避免反复查找
_CACHED_BEST_IPS = None
_CACHE_TIME = 0  # 缓存时间戳

def select_market_code(code, market='stock'):
    """
    2 - bj
    1- sh
    0 -sz
    """
    code = str(code)
    if market == 'stock':
        if code[0] in ['5', '6', '9'] or code[:3] in ["009", "126", "110", "201", "202", "203", "204"]:
            return 1
        elif code[0] in ['0', '3']:
            return 0
        elif code[0] in ['4', '8']:
            return 2
        else:
            return None
    elif market == 'index':
        if code[0] == '3':
            return 0
        return 1
    elif market == 'etf':
        if code[:2] == '15':
            return 0
        elif code[:2] == '51':
            return 1


def select_index_code(code):
    code = str(code)
    if code[0] in ['0', '8', '9', '5']:
        return 1
    else:
        return 0


def ping(ip, port=7709):
    api = TdxHq_API()
    __time1 = datetime.now()
    try:
        with api.connect(ip, port):
            res = api.get_security_list(0, 1)

            if res is not None:
                if len(api.get_security_list(0, 1)) > 800:
                    delta = datetime.now() - __time1
                    log.info('GOOD RESPONSE {},{}'.format(ip, delta))
                    return delta
                else:
                    log.warning('BAD RESPONSE {}'.format(ip))
                    return timedelta(9, 9, 0)
            else:
                log.error('BAD RESPONSE {}'.format(ip))
                return timedelta(9, 9, 0)

    except Exception as e:
        if isinstance(e, TypeError):
            log.error(e)
            log.error('内置的pytdx版本不同, 请重新安装pytdx以解决此问题')
            log.error('pip uninstall pytdx')
            log.error('pip install pytdx')

        else:
            log.warning('BAD RESPONSE {}'.format(ip))
        return timedelta(9, 9, 0)


def get_best_ip_by_ping():
    # 根据ping排序返回可用的ip列表
    dt_min = timedelta(0, 9, 0)
    _best_ip = None
    for x in stock_ip_list:
        dt = ping(x['ip'], x['port'])
        if dt < dt_min:
            dt_min = dt
            _best_ip = x

    if _best_ip is None:
        log.warning('ALL IP PING TIMEOUT!')
        return {'ip': None, 'port': None}
    else:
        return _best_ip


def select_best_ip():
    log.debug('Selecting the Best Server IP of TDX')

    default_ip = {'ip': None, 'port': None}
    default_ip = get_config(section='IPLIST', option='default', default_value=default_ip)
    try:
        default_ip = json.loads(default_ip) if isinstance(default_ip, str) else default_ip
    except json.JSONDecodeError:
        log.warning(f"Failed to parse default IP from config: {default_ip}. Resetting.")
        default_ip = {'ip': None, 'port': None}
    assert isinstance(default_ip, dict)
    if default_ip['ip'] is None:
        best_stock_ip = get_best_ip_by_ping()
    else:
        if ping(default_ip['ip'], default_ip['port']) < timedelta(0, 1):
            log.info('USING DEFAULT STOCK IP')
            best_stock_ip = default_ip
        else:
            log.info('DEFAULT STOCK IP is BAD, RETESTING')
            best_stock_ip = get_best_ip_by_ping()

    if best_stock_ip != default_ip:
        set_config(
            section='IPLIST', option='default', value=best_stock_ip)

    log.info('=== The BEST SERVER ===\n stock_ip {} '.format(best_stock_ip['ip']))
    return best_stock_ip


best_ip = {
    'ip': None,
    'port': None
}


def get_best_ip():
    global best_ip
    if best_ip['ip'] is not None and best_ip['port'] is not None:
        ip = best_ip['ip']
        port = best_ip['port']
    else:
        best_ip = select_best_ip()
        ip = best_ip['ip']
        port = best_ip['port']
    return ip, port


stock_ip_list = [
    # 2023年更新的高可用服务器
    {"ip": "119.147.212.81", "port": 7709, "name": "深圳新增主站1"},
    {"ip": "47.107.75.159", "port": 7709, "name": "深圳新增主站2"},
    {"ip": "101.132.35.193", "port": 7709, "name": "上海新增主站1"},
    {"ip": "45.192.129.230", "port": 7709, "name": "上海新增主站2"},
    # 主要通达信行情服务器
    {"ip": "106.120.74.86", "port": 7711, "name": "北京行情主站1"},
    {"ip": "113.105.73.88", "port": 7709, "name": "深圳行情主站"},
    {"ip": "113.105.73.88", "port": 7711, "name": "深圳行情主站"},
    {"ip": "114.80.80.222", "port": 7711, "name": "上海行情主站"},
    {"ip": "117.184.140.156", "port": 7711, "name": "移动行情主站"},
    {"ip": "119.147.171.206", "port": 443, "name": "广州行情主站"},
    {"ip": "119.147.171.206", "port": 80, "name": "广州行情主站"},
    {"ip": "218.108.50.178", "port": 7711, "name": "杭州行情主站"},
    {"ip": "221.194.181.176", "port": 7711, "name": "北京行情主站2"},
    # 其他备用服务器
    {"ip": "47.93.52.95", "port": 7709, "name": "阿里云主站"},
    {"ip": "202.108.253.131", "port": 7709, "name": "华泰主站"},
    # 原有服务器列表
    {"ip": "106.120.74.86", "port": 7709},  # 北京
    {"ip": "112.95.140.74", "port": 7709},
    {"ip": "112.95.140.92", "port": 7709},
    {"ip": "112.95.140.93", "port": 7709},
    {"ip": "113.05.73.88", "port": 7709},  # 深圳
    {"ip": "114.67.61.70", "port": 7709},
    {"ip": "114.80.149.19", "port": 7709},
    {"ip": "114.80.149.22", "port": 7709},
    {"ip": "114.80.149.84", "port": 7709},
    {"ip": "114.80.80.222", "port": 7709},  # 上海
    {"ip": "115.238.56.198", "port": 7709},
    {"ip": "115.238.90.165", "port": 7709},
    {"ip": "117.184.140.156", "port": 7709},  # 移动
    {"ip": "119.147.164.60", "port": 7709},  # 广州
    {"ip": "119.147.171.206", "port": 7709},  # 广州
    {"ip": "119.29.51.30", "port": 7709},
    {"ip": "121.14.104.70", "port": 7709},
    {"ip": "121.14.104.72", "port": 7709},
    {"ip": "121.14.110.194", "port": 7709},  # 深圳
    {"ip": "121.14.2.7", "port": 7709},
    {"ip": "123.125.108.23", "port": 7709},
    {"ip": "123.125.108.24", "port": 7709},
    {"ip": "124.160.88.183", "port": 7709},
    {"ip": "180.153.18.17", "port": 7709},
    {"ip": "180.153.18.170", "port": 7709},
    {"ip": "180.153.18.171", "port": 7709},
    {"ip": "180.153.39.51", "port": 7709},
    {"ip": "218.108.47.69", "port": 7709},
    {"ip": "218.108.50.178", "port": 7709},  # 杭州
    {"ip": "218.108.98.244", "port": 7709},
    {"ip": "218.75.126.9", "port": 7709},
    {"ip": "218.9.148.108", "port": 7709},
    {"ip": "221.194.181.176", "port": 7709},  # 北京
    {"ip": "59.173.18.69", "port": 7709},
    {"ip": "60.12.136.250", "port": 7709},
    {"ip": "60.191.117.167", "port": 7709},
    {"ip": "60.28.29.69", "port": 7709},
    {"ip": "61.135.142.73", "port": 7709},
    {"ip": "61.135.142.88", "port": 7709},  # 北京
    {"ip": "61.152.107.168", "port": 7721},
    {"ip": "61.152.249.56", "port": 7709},  # 上海
    {"ip": "61.153.144.179", "port": 7709},
    {"ip": "61.153.209.138", "port": 7709},
    {"ip": "61.153.209.139", "port": 7709},
    {"ip": "hq.cjis.cn", "port": 7709},
    {"ip": "hq1.daton.com.cn", "port": 7709},
    {"ip": "jstdx.gtjas.com", "port": 7709},
    {"ip": "shtdx.gtjas.com", "port": 7709},
    {"ip": "sztdx.gtjas.com", "port": 7709},
    {"ip": "113.105.142.162", "port": 7721},
    {"ip": "23.129.245.199", "port": 7721},
]


def select_best_ip_list(n=5, timeout=1.0, ip_list=None):
    """
    选择多个最佳的服务器，用于并行连接
    
    :param n: 返回的服务器数量，默认5
    :param timeout: 测试连接超时时间，默认1.0秒
    :param ip_list: 指定要测试的IP列表，默认为None，使用内置的stock_ip_list
    :return: list of tuple(ip, port)，最佳服务器IP和端口列表
    """
    global _CACHED_BEST_IPS, _CACHE_TIME
    
    # 检查缓存是否有效（30分钟内的缓存视为有效）
    cache_valid = _CACHED_BEST_IPS is not None and len(_CACHED_BEST_IPS) >= n and time.time() - _CACHE_TIME < 1800
    
    if cache_valid:
        log.info(f"使用缓存的 {len(_CACHED_BEST_IPS)} 个服务器 (剩余有效期: {int(1800-(time.time()-_CACHE_TIME))}秒)")
        return _CACHED_BEST_IPS[:n]
    
    if ip_list is None:
        ip_list = stock_ip_list
    
    # 确保至少返回3个服务器，增加容错性
    n = max(n, 3)
    
    log.info(f"正在筛选最佳的 {n} 个通达信服务器...")
    
    # 先尝试从配置读取
    default_ips = get_config(section='IPLIST', option='best_ips', default_value=None)
    if default_ips:
        try:
            default_ips = json.loads(default_ips)
            if isinstance(default_ips, list) and len(default_ips) >= n:
                ip_ports = [(ip_port['ip'], ip_port['port']) for ip_port in default_ips[:n]]
                # 快速测试这些保存的服务器
                for ip, port in ip_ports[:2]:  # 只测试前两个
                    try:
                        api = TdxHq_API()
                        with api.connect(ip, port, time_out=2):  # 减少超时时间以加快测试
                            if api.get_security_count(0) > 0:
                                log.info(f"从配置中获取到有效服务器 {ip}:{port}")
                                break
                    except:
                        continue
                else:
                    # 如果所有保存的服务器都连不上，重新测试
                    log.warning("配置中的服务器均无法连接，重新测试")
                    raise Exception("Saved servers not available")
                    
                log.info(f"从配置中获取到 {len(ip_ports)} 个服务器")
                # 更新缓存
                _CACHED_BEST_IPS = ip_ports
                _CACHE_TIME = time.time()
                return ip_ports
        except Exception as e:
            log.warning(f"配置中的 best_ips 无法使用: {str(e)}")
    
    # 增加超时时间，增强稳定性
    timeout = max(timeout, 1.5)  # 减少超时时间到1.5秒，加快测试速度
    
    # 推荐的第一批测试服务器 - 这些通常是质量较好的
    priority_ips = [
        # 根据日志中实际可用的服务器优先测试
        {"ip": "60.191.117.167", "port": 7709},  # 日志中可用
        {"ip": "180.153.18.170", "port": 7709},  # 日志中可用
        {"ip": "218.75.126.9", "port": 7709},    # 日志中可用
        {"ip": "sztdx.gtjas.com", "port": 7709}, # 日志中可用
        {"ip": "shtdx.gtjas.com", "port": 7709}, # 日志中可用
        # 加入一些常用服务器作为后备
        {"ip": "119.147.212.81", "port": 7709},  # 深圳新增主站1
        {"ip": "47.107.75.159", "port": 7709},   # 深圳新增主站2
        {"ip": "114.80.80.222", "port": 7711}    # 上海行情主站
    ]
    
    # 测试一个股票是否可以获取数据的函数 - 简单但有效的测试
    def can_get_stock_data(api):
        try:
            # 使用已知通常可以获取数据的股票代码
            test_stock = "000001"  # 平安银行
            df = api.get_security_bars(9, 0, test_stock, 0, 1)
            return df is not None and len(df) > 0
        except:
            return False
        
    # 并行测试多个IP的响应时间
    def test_connection(ip_port):
        ip, port = ip_port['ip'], ip_port['port']
        api = TdxHq_API()
        try:
            start = time.time()
            with api.connect(ip, port, time_out=timeout):
                # 测试连接有效性 - 先试简单的API
                try:
                    if api.get_security_count(0) > 0:
                        # 进一步测试是否可以获取股票数据
                        if can_get_stock_data(api):
                            cost = time.time() - start
                            log.info(f"找到有效服务器 {ip}:{port}，响应时间 {cost:.3f}秒")
                            return {'ip': ip, 'port': port, 'cost': cost}
                        else:
                            log.debug(f"服务器 {ip}:{port} 连接成功但无法获取股票数据")
                    else:
                        log.debug(f"服务器 {ip}:{port} 连接成功但 get_security_count 失败")
                except Exception as inner_e:
                    # 如果 get_security_count 失败，尝试其他简单的API
                    try:
                        if len(api.get_security_list(0, 1)) > 0:
                            # 同样测试是否可以获取股票数据
                            if can_get_stock_data(api):
                                cost = time.time() - start
                                log.info(f"找到备用有效服务器 {ip}:{port}，响应时间 {cost:.3f}秒")
                                return {'ip': ip, 'port': port, 'cost': cost}
                            else:
                                log.debug(f"备用服务器 {ip}:{port} 连接成功但无法获取股票数据")
                        else:
                            log.debug(f"备用服务器 {ip}:{port} 连接成功但 get_security_list 失败")
                    except:
                        pass
        except Exception as e:
            log.debug(f"测试服务器 {ip}:{port} 连接失败: {str(e)[:100]}")  # 截断错误信息
        return None
    
    # 两阶段测试 - 先测试优先级服务器
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:  # 增加并行度，加快测试速度
        futures = [executor.submit(test_connection, ip_port) for ip_port in priority_ips]
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
                if len(results) >= n:
                    # 发现足够的服务器，停止等待
                    break
    
    # 如果优先服务器没找到足够的，再测试更多服务器
    if len(results) < n:
        log.info(f"从优先服务器中只找到 {len(results)} 个可用，继续测试其他服务器")
        # 排除已测试的服务器
        priority_ips_set = {(ip['ip'], ip['port']) for ip in priority_ips}
        remaining_ips = [ip for ip in ip_list if (ip['ip'], ip['port']) not in priority_ips_set]
        
        # 随机抽取更多服务器测试，提高找到可用服务器的概率
        test_sample = random.sample(remaining_ips, min(20, len(remaining_ips)))  # 减少测试数量，加快速度
        
        with ThreadPoolExecutor(max_workers=20) as executor:  # 增加并行度，加快测试速度
            futures = [executor.submit(test_connection, ip_port) for ip_port in test_sample]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
                    if len(results) >= n:
                        break
    
    # 确保至少返回一个结果 - 即使测试全部失败
    if not results:
        log.warning("未找到可用的通达信服务器，使用默认服务器列表")
        # 返回更多经常可用的默认服务器
        default_servers = [
            ('119.147.212.81', 7709),  # 深圳新增主站1
            ('47.107.75.159', 7709),   # 深圳新增主站2
            ('47.93.52.95', 7709),     # 阿里云主站
            ('101.132.35.193', 7709),  # 上海新增主站1
            ('114.80.80.222', 7711),   # 上海
            ('113.105.73.88', 7711),   # 深圳
            ('106.120.74.86', 7711)    # 北京
        ]
        return default_servers[:n]
    
    # 按响应时间排序
    results.sort(key=lambda x: x['cost'])
    
    # 返回最快的n个
    best_ips = results[:min(n, len(results))]
    
    # 转换为(ip, port)元组列表
    ip_ports = [(ip_info['ip'], ip_info['port']) for ip_info in best_ips]
    
    # 保存到配置
    try:
        set_config('IPLIST', 'best_ips', json.dumps(best_ips))
    except Exception as e:
        log.warning(f"保存最佳IP列表到配置文件失败: {str(e)}")
    
    # 更新缓存
    _CACHED_BEST_IPS = ip_ports
    _CACHE_TIME = time.time()
    
    log.info(f"已选择 {len(ip_ports)} 个最佳服务器")
    return ip_ports
