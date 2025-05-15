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

import configparser
import os
import json
from subprocess import call
import platform
from qff.tools.local import setting_path

__all__ = ['get_config', 'set_config', 'list_config', 'edit_config', 'unset_config']

CONFIGFILE_PATH = '{}{}{}'.format(setting_path, os.sep, 'config.ini')


def get_config(section, option, default_value=None):
    """
    从配置文件config.ini中读取配置参数
    :param section: 配置文件中的节名称
    :param option:  配置文件中的配置项
    :param default_value: 未找到配置项返回的默认值
    :return: 配置参数对应的值
    """
    try:
        config = configparser.ConfigParser()
        config.read(CONFIGFILE_PATH)
        if not config.has_section(section) or not config.has_option(section, option):
            print(f'config.ini文件中无该配置项 [{section}] {option}，使用默认值: {default_value}')
            if default_value is not None:
                set_config(section, option, default_value)
            return default_value
        return config.get(section, option)
    except Exception as e:
        print(f'读取配置文件出错: {e}, 使用默认值: {default_value}')
        if default_value is not None:
            try:
                set_config(section, option, default_value)
            except:
                pass  # 如果设置失败，忽略错误
        return default_value


def set_config(section, option, value):
    """
    向配置文件config.ini中写入配置参数
    :param section: 配置文件中的节名称
    :param option: 配置文件中的配置项
    :param value: 配置文件中的配置项对应的参数值
    :return: 返回True 或者 False
    """
    try:
        config = configparser.ConfigParser()
        if os.path.exists(CONFIGFILE_PATH):
            config.read(CONFIGFILE_PATH)
            if not config.has_section(section):
                config.add_section(section)
        else:
            config.add_section(section)

        if isinstance(value, str):
            val = value
        else:
            val = json.dumps(value)
        config.set(section, option, val)
        f = open(CONFIGFILE_PATH, 'w')
        config.write(f)
        f.close()
        print("Writing to {}!".format(CONFIGFILE_PATH))
        return True
    except Exception as e:
        print("set_config函数运行错误!\n {}".format(e))
        return False


def list_config():
    config = configparser.ConfigParser()
    config.read(CONFIGFILE_PATH)
    sections = config.sections()
    for section in sections:
        options = config.options(section)
        for option in options:
            value = config.get(section, option)
            print(f"{section}.{option}={value}")


def edit_config():
    if platform.system() == 'Windows':
        os.startfile(CONFIGFILE_PATH)
    elif platform.system() == 'Linux':
        call(["vim", CONFIGFILE_PATH])
    else:
        os.system(f'open {CONFIGFILE_PATH}')


def unset_config(section, option):
    config = configparser.ConfigParser()
    config.read(CONFIGFILE_PATH)
    sections = config.sections()
    if section not in sections:
        print('参数section不存在！')
        return False
    options = config.options(section)
    if option not in options:
        print('参数option不存在！')
        return False
    config.remove_option(section, option)
    print("Writing to {}!".format(CONFIGFILE_PATH))
    return True
