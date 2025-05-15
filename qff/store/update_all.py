# ！/usr/bin/python

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
数据保存统一接口文件，在定时任务中自动执行
"""

from qff.store.save_info import save_stock_list, init_index_list, init_etf_list, \
    init_stock_list, save_index_stock, save_industry_stock, init_stock_name
from qff.store.save_price import save_security_day, save_security_min, save_stock_xdxr, \
    save_security_block
from qff.store.save_report import save_report
from qff.store.save_valuation import save_valuation_data
from qff.store.save_mtss import save_mtss_data
from qff.tools.mongo import DATABASE
from qff.tools.date import is_trade_day
from qff.tools.logs import log
import prettytable as pt
import datetime
import pandas as pd

# 引入新的保存函数
from qff.store.save_hot_info import save_limit_up, save_limit_down, save_block_trade, save_margin_detail
from qff.store.save_block_info import (save_concept_list, save_concept_stocks, save_concept_daily,
                                     save_industry_list, save_industry_stocks, save_industry_daily)
from qff.store.save_special_info import (save_top_list, save_top_inst, save_restricted_release,
                                        save_moneyflow_hsgt, save_moneyflow_stock, save_moneyflow_sector)


def update_all(date=None):
    """
    更新所有财务数据
    """
    if date is None:
        date = str(datetime.date.today())

    log.info('==== 开始更新数据 ==========')

    # 初始化股票列表
    try:
        init_stock_list()
        init_block_list()
    except Exception as e:
        print(f"initialize stock list error: {e}")

    # 更新股票基本信息
    try:
        save_stock_list()
    except Exception as e:
        print(f"updating stock list data error: {e}")

    # 更新行情数据
    try:
        save_stock_day()
        save_stock_block()
    except Exception as e:
        print(f"updating stock price data error: {e}")

    # 更新最新财务数据
    try:
        save_stock_report()
    except Exception as e:
        print(f"updating stock report data error: {e}")

    # 更新估值数据
    try:
        save_stock_valuation()
    except Exception as e:
        print(f"updating stock valuation data error: {e}")

    # 更新融资融券数据
    try:
        save_mtss()
    except Exception as e:
        print(f"updating mtss data error: {e}")

    # 更新分钟线数据
    try:
        save_stock_min()
    except Exception as e:
        print(f"updating stock min data error: {e}")

    # 更新短线数据
    try:
        save_limit_up()
        save_limit_down()
        save_block_trade()
        save_margin_detail()
    except Exception as e:
        print(f"updating hot_info data error: {e}")

    # 更新概念板块和行业板块数据
    try:
        # 概念板块
        concept_codes = save_concept_list()
        save_concept_stocks()
        save_concept_daily()
        
        # 行业板块
        industry_codes = save_industry_list()
        save_industry_stocks()
        save_industry_daily()
    except Exception as e:
        print(f"updating block_info data error: {e}")

    # 更新龙虎榜、解禁股、资金流向等数据
    try:
        save_top_list()
        save_top_inst()
        save_restricted_release()
        save_moneyflow_hsgt()
        save_moneyflow_stock()
        save_moneyflow_sector()
    except Exception as e:
        print(f"updating special_info data error: {e}")

    log.info('==== 更新数据完成 ==========')


def init_delist_date():
    from qff.price.query import get_all_securities
    stock_list = get_all_securities('delist')
    save_security_day('stock', stock_list)
    for freq_ in ["1min", "5min", "15min", "30min", "60min"]:
        save_security_min(market='stock', freq=freq_, security=stock_list)

    save_stock_xdxr(stock_list)


def bytes_to_human(n):
    symbols = ('K', 'M', 'G', 'T', 'P')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)
    return '%sB' % n


def mongo_info():
    colls = sorted(DATABASE.list_collection_names())
    if len(colls) == 0:
        print("数据库qff未创建或数据集为空！")
    else:
        value = []
        for item in colls:
            coll = DATABASE.get_collection(item)
            stats = DATABASE.command("collstats", item)
            if stats['count'] > 0:
                columns = coll.find_one().keys()
                col_num = len(columns)
                count = "{:,}".format(stats['count'])
            else:
                col_num = 0
                count = 0

            data_size = bytes_to_human(stats['size'])
            storage_size = bytes_to_human(stats['storageSize'])
            nindex = stats['nindexes']
            total_index_size = bytes_to_human(stats['totalIndexSize'])
            index = list(stats['indexSizes'].keys())

            value.append([item, count, col_num, data_size, storage_size, nindex, total_index_size, index])
        df = pd.DataFrame(value,
                          columns=['数据集合', '记录数量', '字段数量', '集合大小', '存储空间', '索引数量', '索引大小',
                                   '索引值'])
        # df = pd.DataFrame(value, columns=['table_name', 'count', 'column_num', 'column'])
        # pd.set_option('display.width', 300)
        # pd.set_option('display.max_colwidth', 80)
        # pd.set_option('display.max_columns', 4)

        tb = pt.PrettyTable()
        tb.add_column('序号', df.index)
        for col in df.columns.values:
            tb.add_column(col, df[col])
            tb.align[col] = "r"

        print(tb)

        print("\n")
        last_date = DATABASE.stock_day.find_one({'code': '000001'}, sort=[('date', -1)])['date']
        print(f"数据库最后一次更新日期：{last_date}")


def qff_save(*args):
    if args[0] == 'all':
        update_all()

    elif args[0] == 'day':
        for market_ in ['stock', 'index', 'etf']:
            save_security_day(market_)

    elif args[0] == 'min':
        for market_ in ['stock', 'index', 'etf']:
            for freq_ in ["1min", "5min", "15min", "30min", "60min"]:
                save_security_min(market=market_, freq=freq_)

    elif args[0] == 'stock_list':
        save_stock_list()

    elif args[0] in ['stock_day', 'index_day', 'etf_day']:
        save_security_day(str(args[0]).split('_')[0])

    elif args[0] in ['stock_min', 'index_min', 'etf_min']:
        for freq_ in ["1min", "5min", "15min", "30min", "60min"]:
            save_security_min(market=str(args[0]).split('_')[0], freq=freq_)

    elif args[0] == 'stock_xdxr':
        save_stock_xdxr()

    elif args[0] == 'stock_block':
        save_security_block()

    elif args[0] == 'report':
        save_report(True)

    elif args[0] == 'valuation':
        save_valuation_data()

    elif args[0] == 'mtss':
        save_mtss_data()

    elif args[0] == 'index_stock':
        save_index_stock()

    elif args[0] == 'industry_stock':
        save_industry_stock()

    elif args[0] == 'init_info':
        init_stock_list()
        init_index_list()
        init_etf_list()

    elif args[0] == 'init_name':
        init_stock_name()
    elif args[0] == 'save_delist':
        init_delist_date()
    else:
        print("命令格式不合法！")


def qff_drop(*args):
    table_name = args[0]
    table_list = DATABASE.list_collection_names()
    if table_name not in table_list:
        print("输入的数据库不存在！")
    else:
        ack = input(f"注意：请确认是否真的删除数据表{table_name}(Y/N)?:")
        if ack.strip().lower() == 'y':
            DATABASE.drop_collection(table_name)
            print(f"qff数据表{table_name}删除成功！")
        else:
            print(f"qff数据表{table_name}删除取消！")


if __name__ == '__main__':
    op_date = str(datetime.date.today())
    if not is_trade_day(op_date):
        print('======== 当前不是交易日，无需更新数据！ ==========')
    else:

        update_all(op_date)

    # mongo_info()
