from contextlib import nullcontext
from http import cookiejar
from tracemalloc import start
from types import MethodDescriptorType
from urllib.request import Request
from weakref import proxy
from wsgiref import headers
from zlib import DEF_BUF_SIZE
import requests
import re
import zhenzismsclient as smsclient
import time
import os
import configparser
from urllib.parse import urlencode
import datetime
from threading import Timer

proxies = {
    
}
session = requests.session()
myDict = {}

def getCookies(username,password):
    """
    session自动实现重定向
    手动实现跳转,获取登陆cookie
    """
    # 1. 登陆页面发送POST请求
    session.cookies.clear()
    
    url = 'http://login.cuit.edu.cn/Login/xLogin/Login.asp'
    data = {
        'txtId':username,
        'txtMM':password,
        'verifycode':'%B2%BB%B7%D6%B4%F3%D0%A1%D0%B4',
        # 后台未对验证码是否合法进行校验
        'codeKey':'00000',
        'Login':'Check'
    }
    
    headers = {
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0',
        'Referer':'http://login.cuit.edu.cn/Login/xLogin/Login.asp'
    }
    
    res = session.post(url=url,headers=headers,data=data,proxies=proxies)
    
    # 第一次非重定向跳转
    pattern1 = '(URL=)(.*?)(\">)'
    urlJump1 = re.search(pattern1,res.text)
    url2 = urlJump1.group(2)
    res = session.get(url=url2,proxies=proxies)
    
    # 第二次非重定向跳转
    pattern2 = '(URL=)(.*?)(\">)'
    urlJump2 = re.search(pattern2,res.text)
    url3 = urlJump2.group(2)
    res = session.get(url=url3,proxies=proxies)
    
    # 第三次非重定向跳转，获取填写出校申请的URL
    pattern3 = '(href=)(.{10,})(target=_self)'
    urlJump3 = re.search(pattern3,res.text)
    url3 = 'http://jszx-jxpt.cuit.edu.cn/Jxgl/Xs/netks/'+urlJump3.group(2)
    res = session.get(url=url3,proxies=proxies)
    targetURL = res.url
    return session.cookies.get_dict(),targetURL

def application(myCookies,myURL,postURL):
    """
    提交出校申请表单,并获取提交成功后的正则匹配对象
    """
    pattern = r'(&Id=)(\d{5})'
    reRes = re.search(pattern,myURL)
    id = reRes.group(2)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0',
        'Referer': 'http://jszx-jxpt.cuit.edu.cn/Jxgl/Xs/netks/editSjRs.asp',
        'Origin': 'http://jszx-jxpt.cuit.edu.cn',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data={
        'RsNum':'3',
        'Id':id,
        'Tx':'33_1',
        'canTj':'1',
        'isNeedAns':'0',
        'UTp':'Xs',
        'ObjId':myDict['username'],
        'th_1':'21650',
        'wtOR_1': '100000\|/' + myDict['province'] + '\|/' + myDict['city'] + '\|/' + myDict['country'] + '\|/1\|/1\|/1\|/1\|/1\|/',
        'sF21650_1':'1',
        'sF21650_2':myDict['province'],
        'sF21650_3':myDict['city'],
        'sF21650_4':myDict['country'],
        'sF21650_5':'1',
        'sF21650_6':'1',
        'sF21650_7':'1',
        'sF21650_8':'1',
        'sF21650_9':'1',
        'sF21650_10':'',
        'sF21650_N': '10',
        'th_2': '21912',
        'wtOR_2': myDict['destination'] + '\|/' + myDict['reason'] + '\|/'+ myDict['startDay']+'\|/\|/\|/',
        'sF21912_1': myDict['destination'],
        'sF21912_2': myDict['reason'],
        'sF21912_3': myDict['startDay'],
        'sF21912_4': myDict['startTime'],
        'sF21912_5': myDict['endDay'],
        'sF21912_6': myDict['endTime'],
        'sF21912_N': '6',
        'th_3':'21648',
        'wtOR_3':'N\|/\|/N\|/\|/N\|/',
        'sF21648_1':'N',
        'sF21648_2':'',
        'sF21648_3':'N',
        'sF21648_4':'',
        'sF21648_5':'N',
        'sF21648_6':'',
        'sF21648_N': '6',
        'zw1':'',
        'cxStYt':'A',
        'zw2':'',
        'B2':'提交打卡'
        }
    data_gb2312 = urlencode(data, encoding='gb2312')
    
    res = session.post(url=postURL,cookies=myCookies,headers=headers,data=data_gb2312,proxies=proxies)
    res.encoding = res.apparent_encoding
    #print(res.text)
    pattern = '(待审批\/可改，急则请联系班主任\/辅导员)|(可改)'
    resCode1 = re.search(pattern,res.text)
    if resCode1:
        print("已提交成功")
        # sleep 阻塞900秒，提交申请后，要经过15分钟的锁定
        # 才可以判断是否提交成功
        time.sleep(900)
        res2 = session.get(url=myURL)
        res2.encoding = res2.apparent_encoding
        pattern = '已通过/禁改，请按报备的时间进出学校'
        resCode2 = re.search(pattern,res2.text)
    else:
        print("申请未提交成功,请手动检查!")
        resCode2 = None
    return resCode2
    
def check(resCode):
    """
    检查出校申请是否通过,并用短信通知收件人
    """
    client = smsclient.ZhenziSmsClient('https://sms_developer.zhenzikj.com',appId=myDict['appId'],appSecret=myDict['appSecret'])
    params={}
    params['number']=myDict['sendNumber']
    params['templateId']=myDict['sendTemp']
    # params['templateParams'] = myDict['sendContent']
    if resCode:
        print('打卡成功')
        params['templateParams'] = ['成功']
        resCode = client.send(params)
        print(resCode)
    else:
        print('打卡失败')
        # myDict['username'][-6:] 榛子云的参数只能容纳8个字符
        params['templateParams'] = [myDict['username'][-6:],'失败',myDict['startDay'],myDict['startTime'],
                                    myDict['endDay'],myDict['endTime']]
        resCode = client.send(params)
        print(resCode)

def getConfig(filename,section,option):
    """
    配置文件,读取指定变量名的值
    """
    proDir = os.path.split(os.path.realpath(__file__))[0]
    configPath = os.path.join(proDir, filename)
    conf = configparser.ConfigParser()
    conf.read(configPath,encoding ='UTF-8')
    config = conf.get(section, option)
    return config

def getVar():
    """
    将所有变量都存储到全局字典中
    """
    mainDict = {}
    varName = ['username','password','province','city','country','destination','reason',
               'startDay','startTime','endDay','endTime','appId','appSecret','sendNumber','sendTemp','sendContent']
    for item in varName:
        key = item
        value = getConfig('myConfig.conf','myInfo',key)
        mainDict[key] = value
    return mainDict

def timeLoop():
    """
    控制执行的间隔时间，24小时执行一次
    """
    nowTime = time.asctime(time.localtime(time.time()))
    print(nowTime)
    t = Timer(86400,main())
    t.start()
     
def main():
    myCookies,myURL = getCookies(myDict['username'],myDict['password'])
    postURL = 'http://jszx-jxpt.cuit.edu.cn/Jxgl/Xs/netks/editSjRs.asp'
    resCode = application(myCookies,myURL,postURL)
    check(resCode)
    
if __name__ == '__main__':
    myDict = getVar()
    flag = 1
    while True:
        print(flag)
        timeLoop()
        flag += 1
        