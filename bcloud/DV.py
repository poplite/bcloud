
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Copyright (C) poplite <poplite.xyz@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

'''
这个模块用于生成登录需要的dv参数.
'''

import random
import re

from bcloud import const
from bcloud import encoder
from bcloud import util

## 不同平台的ID编号.
platform_group = [
    ('1',  'win'   ),  # Windows
    ('2',  'linux' ),  # Linux
    ('3',  'Mac'   ),  # Mac
    ('4',  'iPhone'),  # iPhone
    ('5',  'iPod'  ),  # iPod
    ('6',  'iPad'  ),  # iPad
]

## 识别浏览器，并解析出其版本号.
## 元组的第一个元素是浏览器ID编号，第二个元素是用作解析的正则表达式.
## 如果有第三个元素-1，则表示无法解析出浏览器的版本号.
browser_group = [
    ( '1',  'msie ([\d.]+)'                         ),  # IE
    ( '2',  'chrome\/([\d.]+)'                      ),  # Chrome
    ( '3',  'firefox\/([\d.]+)'                     ),  # Firefox
    ( '4',  'msie.*360se',                      -1  ),  # 360浏览器
    ( '5',  'msie.*360ee',                      -1  ),  # 360浏览器
    ( '6',  'Opera.+Version\/([\d.]+)'              ),  # Opera
    ( '6',  'opr\/([\d.]+)'                         ),  # Opera
    ( '7',  'se ([\d]+.[\w]*) metasr ([\d.]+)'      ),  # 搜狗浏览器
    ( '8',  'msie.*qihu theworld',              -1  ),  # 世界之窗
    ( '9',  'tencenttraveler ([\d.]+)'              ),  # TT浏览器
    ('10',  'qqbrowser\/([\d.]+)'                   ),  # QQ浏览器
    ('11',  'version\/([\d.]+).*safari'             ),  # Safari
    ('12',  'maxthon[\/ ]([\d.]+)'                  ),  # 傲游浏览器
]

## 屏幕信息，以下数值可以修改.
screenInfo = [
      '27',  # 浏览器窗口相对于显示屏屏幕的水平坐标
       '0',  # 浏览器窗口相对于显示屏屏幕的垂直坐标
    '1920',  # body元素的宽度
     '918',  # body元素的高度
    '1920',  # 显示屏屏幕的宽度
    '1080',  # 显示屏屏幕的高度
    '1920',  # 浏览器窗口的可用宽度
#   '1053',  # 浏览器窗口的可用高度
    '1920',  # 浏览器窗口外部的宽度
    '1053',  # 浏览器窗口外部的高度
]

## 网页属性
location = const.PAN_URL
userAgent = const.USER_AGENT

## 用于生成dv参数的字典, 是字符列表.
dict1 = []
dict2 = []

def split_into_list(s):
    '''将字符串分割成一个列表'''
    return [c for c in s]

def get_PageToken():
    '''获得PageToken'''
    return 'tk' + str(random.random()) + util.timestamp()

def get_Location():
    '''获得网页位置'''
    if len(location) <= 50:
        return ','.join([encoder.encode_uri(location),
                        'undefined'])
    else:
        return ','.join([encoder.encode_uri(location[:50]),
                        'undefined'])

def get_browserInfo():
    '''从userAgent获得浏览器以及平台信息.

    platformID - 平台ID编号
    browserID  - 浏览器ID编号
    browserVer - 浏览器的大版本号
    '''
    platformID = '0' # 未知平台
    for platid, regex_rule in platform_group:
        if re.search(regex_rule, userAgent, re.I):
            platformID = platid
            break
    browserID = "An unknown browser" # 未知浏览器
    browserVer = "an unknown version"
    for browser in browser_group:
        result = re.search(browser[1], userAgent, re.I)
        if result:
            browserID = browser[0]
            if not (len(browser) == 3 and browser[2] == -1):
                browserVer = result.group(1).split('.')[0]
            break
    return ','.join([platformID, browserID, browserVer])

def get_screenInfo():
    '''获得屏幕信息'''
    return ','.join(screenInfo)

def generate_dict(token):
    '''生成字典'''
    def generate_func(d, token):
        '''根据token打乱字符顺序'''
        char_list = split_into_list(token)
        for m in range(0, len(d)):
            n = ord(char_list[m % len(char_list)]) % len(d)
            temp = d[m]
            d[m] = d[n]
            d[n] = temp
        return d

    d1 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-~'
    d1 = split_into_list(d1)
    d2 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-~'
    d2 = split_into_list(d2)
    return generate_func(d1, token), generate_func(d2, token)

def get_str_by_num(num, d):
    '''接受一个整数/浮点数，使用字典生成一个字符串'''
    num = abs(int(num)) # 取正整数
    rst_str = ''
    if num:
        while num:
            rst_str += d[num % len(d)]
            num = int(num / len(d))
    else:
        rst_str = d[0]
    return rst_str

def get_str_by_str(string, d):
    '''接受一个字符串，使用字典生成一个字符串'''
    char_list  = split_into_list(string)
    length = len(char_list)
    rst_str = ''
    i = 0
    while i < length:
        a = ord(char_list[i])
        i += 1
        rst_str += d[a >> 2]
        if i >= length:
            rst_str += d[(3 & a) << 4]
            rst_str += "__"
            break
        else:
            b = ord(char_list[i])
            i += 1
            rst_str += d[(3 & a) << 4 | (240 & b) >> 4]
            if i >= length:
                rst_str += d[(15 & b) << 2]
                rst_str += "_"
                break
            else:
                c = ord(char_list[i])
                i += 1
                rst_str += d[(15 & b) << 2 | (192 & c) >> 6]
                rst_str += d[63 & c]
    return rst_str

def get_str_by_list(lst):
    '''接受一个整数列表，使用字典生成一个字符串'''
    rst_str = ''
    for num in lst:
        char = get_str_by_num(num, dict2)
        rst_str += char
    return rst_str

def generate_dv(info):
    '''生成dv参数'''
    str_list = [get_str_by_list([2])]
    for info_id, key, value in info:
        if value:
            if isinstance(value, int) or isinstance(value, float):
                rst = get_str_by_num(value, dict1)
                string = get_str_by_list([info_id, 1, len(rst)])
            elif isinstance(value, str):
                rst = get_str_by_str(value, dict1)
                string = get_str_by_list([info_id, 0, len(rst)])
            str_list.append(string + rst)
    return ''.join(str_list)

def get_new_dv():
    '''获得新的dv参数'''
    global dict1
    global dict2

    token = get_PageToken()
    loadTime = int(util.timestamp()) / 1000
    dict1, dict2 = generate_dict(token)

    ## 用作生成dv参数的时间戳以及浏览器信息.
    ## 注意不能调整列表元素顺序.
    info = [
        ( 0,  "flashInfo",   ""                ),  # 空
        ( 1,  "mouseDown",   ""                ),  # 空
        ( 2,  "keyDown",     ""                ),  # 空
        ( 3,  "mouseMove",   ""                ),  # 空
        ( 4,  "version",     25                ),  # 版本号
        ( 5,  "loadTime",    loadTime          ),  # 加载时间
        ( 6,  "browserInfo", get_browserInfo() ),  # 浏览器信息
        ( 7,  "token",       token             ),  # PageToken
        ( 8,  "location" ,   get_Location()    ),  # 网页位置
        ( 9,  "screenInfo",  get_screenInfo()  ),  # 屏幕信息
        (10,  "powAnsw",     ""                ),  # 空
    ]

    return token + '@' + generate_dv(info)

