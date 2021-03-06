
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

'''
这个模块主要是用于从百度服务器取得cookie/token授权.
'''

import base64
import json
import os
import random
import re
import traceback
import urllib.request
from urllib import parse

from bcloud import const
from bcloud import encoder
from bcloud.log import logger
from bcloud import net
from bcloud.RequestCookie import RequestCookie
from bcloud import util

def get_ppui_logintime():
    '''ppui_logintime 这个字段, 是一个随机数.'''
    return str(random.randint(52000, 58535))

def get_BAIDUID():
    '''获取一个cookie - BAIDUID.

    这里, 我们访问百度首页, 返回的response header里面有我们需要的cookie
    '''
    url = ''.join([
        const.PASSPORT_URL,
        '?getapi&tpl=netdisk&subpro=netdisk_web&apiver=v3',
        '&tt=', util.timestamp(),
        '&class=login&logintype=basicLogin',
    ])
    req = net.urlopen(url, headers={'Referer': ''})
    if req:
        return req.headers.get_all('Set-Cookie')
    else:
        return None

def get_token(cookie):
    '''获取一个页面访问的token, 这里需要之前得到的BAIDUID 这个cookie值

    这个token的有效期还不确定.
    返回的数据如下:
    {"errInfo":{"no": "0"},
     "data": {
         "rememberedUserName" : "",
         "codeString" : "",
         "token" : "xxxxx",
         "cookie" : "1",
         "usernametype":"2",
         "spLogin" : "rate",
         "disable":"",
         "loginrecord":{ 'email':[ ], 'phone':[]}
    }}
    '''
    url = ''.join([
        const.PASSPORT_URL,
        '?getapi&tpl=netdisk&subpro=netdisk_web&apiver=v3',
        '&tt=', util.timestamp(),
        '&class=login&logintype=basicLogin',
    ])
    headers={
        'Cookie': cookie.header_output(),
        'Accept': const.ACCEPT_HTML,
        'Cache-control': 'max-age=0',
    }
    req = net.urlopen(url, headers=headers)
    if req:
        cookie = req.headers.get_all('Set-Cookie')
        content_obj = util.json_loads_single(req.data.decode())
        if content_obj:
            return cookie, content_obj['data']['token']
    return None

def get_UBI(cookie, tokens):
    '''检查登录历史, 可以获得一个Cookie - UBI.
    返回的信息类似于: 
    {"errInfo":{ "no": "0" }, "data": {'displayname':['xxx@163.com']}}
    '''
    url = ''.join([
        const.PASSPORT_URL,
        '?loginhistory',
        '&token=', tokens['token'],
        '&tpl=netdisk&subpro=netdisk_web&apiver=v3',
        '&tt=', util.timestamp(),
    ])
    headers={
        'Cookie': cookie.header_output(),
        'Referer': const.REFERER,
    }
    req = net.urlopen(url, headers=headers)
    if req:
        return req.headers.get_all('Set-Cookie')
    else:
        return None

def check_login(cookie, tokens, username, dv=''):
    '''进行登录验证, 主要是在服务器上验证这个帐户的状态.

    如果帐户不存在, 或者帐户异常, 就不需要再进行最后一步的登录操作了.
    这一步有可能需要输入验证码.
    返回的信息如下:
    {"errInfo":{ "no": "0" }, "data": { "codeString" : "", "vcodetype" : "" }}
    '''
    url = ''.join([
        const.PASSPORT_URL,
        '?logincheck',
        '&token=', tokens['token'],
        '&tpl=netdisk&subpro=netdisk_web&apiver=v3&sub_source=leadsetpwd',
        '&tt=', util.timestamp(),
        '&username=', encoder.encode_uri_component(username),
        '&isphone=false',
        '&dv=', dv,
    ])
    headers={
        'Cookie': cookie.header_output(),
        'Referer': const.REFERER,
    }
    req = net.urlopen(url, headers=headers)
    if req:
        ubi = req.headers.get_all('Set-Cookie')
        return ubi, json.loads(req.data.decode())
    else:
        return None

def get_signin_vcode(cookie, codeString):
    '''获取登录时的验证码图片.

    codeString - 调用check_login()时返回的codeString.
    '''
    url = ''.join([
        const.PASSPORT_BASE,
        'cgi-bin/genimage?',
        codeString,
    ])
    headers={
        'Cookie': cookie.header_output(),
        'Referer': const.REFERER,
    }
    req = net.urlopen(url, headers=headers)
    if req:
        return req.data
    else:
        return None

def refresh_signin_vcode(cookie, tokens, vcodetype):
    '''刷新验证码.

    vcodetype - 在调用check_login()时返回的vcodetype.
    '''
    url = ''.join([
        const.PASSPORT_BASE,
        'v2/?reggetcodestr',
        '&token=', tokens['token'],
        '&tpl=netdisk&subpro=netdisk_web&apiver=v3',
        '&tt=', util.timestamp(),
        '&fr=login',
        '&vcodetype=', encoder.encode_uri(vcodetype),
    ])
    headers={
        'Cookie': cookie.header_output(),
        'Referer': const.REFERER,
    }
    logger.debug('refresh vcode url: %s' % url)
    req = net.urlopen(url, headers=headers)
    if req:
        try:
            data = req.data.decode('gbk')
            logger.debug('refresh vcode: %s' % data)
            return json.loads(data)
        except ValueError:
            logger.error(traceback.format_exc())
    return None

def check_signin_vcode(cookie, tokens, verifycode, codeString):
    '''检查验证码是否正确.'''
    url = ''.join([
        const.PASSPORT_BASE,
        'v2/?checkvcode',
        '&token=', tokens['token'],
        '&tpl=netdisk&subpro=netdisk_web&apiver=v3',
        '&tt=', util.timestamp(),
        '&verifycode=', encoder.encode_uri_component(verifycode),
        '&codestring=', codeString,
        ])
    headers={
        'Cookie': cookie.header_output(),
        'Referer': const.REFERER,
    }
    req = net.urlopen(url, headers=headers)
    if req:
        content = req.data.decode()
        query = json.loads(content)
        return query['errInfo']
    else:
        return None

def get_public_key(cookie, tokens):
    '''获取RSA公钥, 这个用于加密用户的密码
    
    返回的数据如下:
    {"errno":'0',"msg":'',"pubkey":'-----BEGIN PUBLIC KEY-----\nMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDk\/ufXg3IBW8+h5i8L8NoXUzcN\nMeKrh4zEupGBkyrURIPUXKDFLWjrv4n2j3RpMZ8GQn\/ETcfoIHGBoCUKJWcfcvmi\nG+OkYeqT6zyJasF0OlKesKfz0fGogMtdCQ6Kqq7X2vrzBPL+4SNU2wgU31g\/tVZl\n3zy5qAsBFkC70vs5FQIDAQAB\n-----END PUBLIC KEY-----\n',"key":'lwCISJnvs7HRNCTxpX7vi25bV9YslF2J'}
    '''
    url = ''.join([
        const.PASSPORT_BASE, 'v2/getpublickey',
        '?token=', tokens['token'],
        '&tpl=netdisk&subpro=netdisk_web&apiver=v3&tt=', util.timestamp(),
    ])
    headers={
        'Cookie': cookie.header_output(),
        'Referer': const.REFERER,
    }
    req = net.urlopen(url, headers=headers)
    if req:
        data = req.data
        return util.json_loads_single(req.data.decode())
    return None

def post_login(cookie, tokens, username, password, rsakey, verifycode='',
               codestring='', dv=''):
    '''登录验证.
    password   - 使用RSA加密后的base64字符串
    rsakey     - 与public_key相匹配的rsakey
    verifycode - 验证码, 默认为空
    dv         - 根据时间戳和浏览器信息生成的随机字符串，目前还不支持。
                 如果登录时需要输入验证码，该参数为空可能会导致登录失败，
                 返回"err_no":6，即验证码错误。

    @return (status, info). 其中, status表示返回的状态:
      0 - 正常, 这里, info里面存放的是auth_cookie
     -1 - 未知异常
      4 - 密码错误
    257 - 需要输入验证码, 此时info里面存放着(vcodetype, codeString))
    '''
    url = const.PASSPORT_LOGIN
    data = ''.join([
        'staticpage=https%3A%2F%2Fpan.baidu.com%2Fres%2Fstatic%2Fthirdparty%2Fpass_v3_jump.html',
        '&tpl=netdisk&detect=1&foreignusername=&countrycode=',
        '&subpro=netdisk_web',
        '&charset=utf-8',
        '&token=', tokens['token'],
        '&apiver=v3',
        '&tt=', util.timestamp(),
        '&codestring=', codestring,
        '&safeflg=0&u=https%3A%2F%2Fpan.baidu.com%2Fdisk%2Fhome',
        '&isPhone=',
        '&quick_user=0&logintype=basicLogin&logLoginType=pc_loginBasic&idc=',
        '&loginmerge=true',
        '&username=', encoder.encode_uri_component(username),
        '&password=', encoder.encode_uri_component(password),
        '&verifycode=', encoder.encode_uri_component(verifycode),
        '&mem_pass=on',
        '&rsakey=', rsakey,
        '&crypttype=12',
        '&ppui_logintime=', get_ppui_logintime(),
        '&dv=', dv,
        '&callback=parent.bd__pcbs__28g1kg',
    ])
    headers={
        'Accept': const.ACCEPT_HTML,
        'Cookie': cookie.sub_output('BAIDUID','HOSUPPORT', 'UBI'),
        'Referer': const.REFERER,
        'Connection': 'Keep-Alive',
    }
    req = net.urlopen(url, headers=headers, data=data.encode())
    if req:
        content= req.data.decode()
        match = re.search('"(err_no[^"]+)"', content)
        if not match:
            return (-1, None)
        query = dict(urllib.parse.parse_qsl(match.group(1)))
        query['err_no'] = int(query['err_no'])
        err_no = query['err_no']
        auth_cookie = req.headers.get_all('Set-Cookie')

        if err_no == 0:
            return (0, auth_cookie)
        # 需要手机号验证
        elif err_no == 18:
            return (err_no, query)
        # 要输入验证码
        elif err_no == 257:
            return (err_no, query)
        # 需要短信验证
        elif err_no == 400031:
            return (err_no, query)
        else:
            return (err_no, None)
    else:
        return (-1, None)
    return (-1, None)

def get_auth_cookie(cookie):
    '''通过重定向获得授权cookie
    
    重定向的链接开头为:
    http://pan.baidu.com/disk/home?errno=0&errmsg=Auth%20Login%20Sucess&stoken=xxx
    '''
    url = ''.join([
        const.PASSPORT_LOGIN_V3,
        'auth/?return_type=5',
        '&tpl=netdisk&u=https%3A%2F%2Fpan.baidu.com%2Fdisk%2Fhome'
    ])
    headers={
        'Cookie': cookie.header_output(),
        'Referer': const.PAN_REFERER,
    }
    req = net.urlopen_without_redirect(url, headers=headers)
    if req and req.headers.get("Location"):
        redirect_url = req.headers.get("Location")
        redirect_req = net.urlopen_without_redirect(redirect_url, headers={'Cookie': cookie.header_output()})
        if redirect_req:
            return redirect_req.headers.get_all('Set-Cookie')
        else:
            return None
    else:
        return None

def parse_bdstoken(content):
    '''从页面中解析出bdstoken等信息.
    
    这些信息都位于页面底部的<script>, 只有在授权后的页面中才出现.
    这里, 为了保证兼容性, 就不再使用cssselect模块解析了.

    @return 返回bdstoken
    '''
    bdstoken = ''
    bds_re = re.compile('"bdstoken"\s*:\s*"([^"]+)"', re.IGNORECASE)
    bds_match = bds_re.search(content)
    if bds_match:
        bdstoken = bds_match.group(1)
    return bdstoken

def get_bdstoken(cookie):
    '''从/disk/home页面获取bdstoken等token信息

    这些token对于之后的请求非常重要.
    '''
    url = const.PAN_REFERER
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        return parse_bdstoken(req.data.decode())
    else:
        return None

def get_sign_and_timestamp(cookie):
    '''获得部分API需要的timestamp和sign参数.'''
    req = net.urlopen(const.PAN_URL, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data.decode()
        sign1_match = re.findall('"sign1":"(.+)","sign2"', content)
        sign3_match = re.findall('"sign3":"(.+)","timestamp"', content)
        timestamp_match = re.findall(',"timestamp":(\d+)', content)
        if len(sign1_match) == 1 and len(sign3_match) == 1 and len(timestamp_match) == 1:
            timestamp = int(timestamp_match[0])
            sign1 = sign1_match[0]
            sign3 = sign3_match[0]
            sign = util.RC4_encrypt(sign3, sign1)
            if sign:
                return sign, timestamp
    return None, None
