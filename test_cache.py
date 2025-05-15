"""
测试缓存模块是否正常工作
"""

import os
import sys
from qff.tools.cache import init_cache_data, get_cache_path, get_cached_data, CACHE_DIR

def main():
    print("开始测试缓存模块...", flush=True)
    print(f"缓存目录: {CACHE_DIR}", flush=True)
    
    # 测试初始化缓存
    print("初始化缓存数据...", flush=True)
    result = init_cache_data()
    print(f"初始化结果: {result}", flush=True)
    
    # 检查缓存文件是否创建
    industry_cache = get_cache_path('industry_list')
    concept_cache = get_cache_path('concept_list')
    
    print(f"行业板块缓存文件: {industry_cache}", flush=True)
    print(f"行业板块缓存文件存在: {os.path.exists(industry_cache)}", flush=True)
    
    print(f"概念板块缓存文件: {concept_cache}", flush=True)
    print(f"概念板块缓存文件存在: {os.path.exists(concept_cache)}", flush=True)
    
    # 尝试读取缓存数据
    print("读取行业板块缓存...", flush=True)
    industry_data = get_cached_data('industry_list')
    if industry_data is not None:
        print(f"行业板块数据行数: {len(industry_data)}", flush=True)
        print(f"行业板块数据列: {industry_data.columns.tolist()}", flush=True)
    else:
        print("未能读取行业板块数据", flush=True)
    
    print("测试完成", flush=True)

if __name__ == "__main__":
    main() 