import requests
import base64
import time
from apscheduler.schedulers.blocking import BlockingScheduler

# 验证码解析参数
verify_code_params = {
    'user': '<your username>',
    'pass': '<your password>',
    'softid': '<your softid>',
    'codetype': 1902,
    'file_base64': ''
}

# 讲座系统请求头
lecture_headers = {
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
  'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
  'Cache-Control': 'max-age=0',
  'Connection': 'keep-alive',
  'Cookie': '<your cookie>',
  'Sec-Fetch-Dest': 'document',
  'Sec-Fetch-Mode': 'navigate',
  'Sec-Fetch-Site': 'none',
  'Sec-Fetch-User': '?1',
  'Upgrade-Insecure-Requests': '1',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
  'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"macOS"'
}

# 验证码解析请求头
verify_code_headers = {
    'Connection': 'Keep-Alive',
    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0)',
}

# 目标讲座关键词，请尽可能指向唯一目标
lecture_keys = ["lecture1", "lecture2"]

def parse_verify_code(img_base64):
    """
    解析验证码

    Args:
        img_base64 (bytes): 验证码图片的base64字节码

    Returns:
        str: 解析的验证码
    """
    
    verify_code_params['file_base64'] = img_base64
    
    r = requests.post(
        url='http://upload.chaojiying.net/Upload/Processing.php', 
        data=verify_code_params, 
        headers=verify_code_headers,
    )
    res = r.json()

    if res['err_no'] == 0:
        return res['pic_str']
    else:
        print(f"解析验证码出错: {res['err_str']}")
        return None

def get_target_lectures(keys):
    """
    获取目标讲座信息

    Args:
        keys (list): 讲座名称关键词列表

    Returns:
        list: 讲座数据列表
    """
    payload = {}

    url = "https://ehall.seu.edu.cn/gsapp/sys/yddjzxxtjappseu/modules/hdyy/queryActivityList.do"

    r = requests.request("GET", url, headers=lecture_headers, data=payload)
    
    if r.status_code != 200 or len(r.text) == 0:
        print("讲座列表接口响应不成功，请检查cookie！")
        return None
    
    res = r.json()  
    lecture_list = res['datas']['hdlbList']
    if lecture_list is None or len(lecture_list) == 0:
        print("当前没有任何讲座可预约！")
        return None
    
    target_list = []
    for key in keys:
        for item in lecture_list:
            if key in item['JZMC']:
                target_list.append(item)
                break
    
    if len(target_list) == 0:
        print("当前关键词没有搜索到任何讲座！")
        return None
    
    return target_list

def get_lecture_verify_code(wid):
    """
   获取指定讲座的验证码

    Args:
        wid (str): 讲座id
        
    Returns:
        bytes: 验证码图片的base64字节码
    """
    url='https://ehall.seu.edu.cn/gsapp/sys/yddjzxxtjappseu/modules/hdyy/vcode.do'
    r = requests.request("GET", url, headers=lecture_headers, params={'_': int(time.time() * 1000)})
    res = r.json()
    
    base64_str = res['datas']
    base64_str = base64_str[(base64_str.index("base64,") + 7):]
    return bytes(base64_str, encoding='utf-8')

def reserve_lecture(wid, verify_code):
    """
   预约指定讲座

    Args:
        wid (str): 讲座id
        verify_code (str): 验证码
    
    Returns:
        bool: 预约结果
    """
    
    params = {
        'wid': wid,
        'vcode': verify_code,
    }
    url='https://ehall.seu.edu.cn/gsapp/sys/yddjzxxtjappseu/modules/hdyy/addReservation.do'
    
    r = requests.request("POST", url, headers=lecture_headers, data=params)

    res = r.json()
    print('预约接口响应数据: ', res)
    
    return res['code'] == 0 and res['datas'] == 1
    
def keep_alive(wid):
    """
    获取指定讲座信息以保活

    Args:
        wid (str): 讲座id
    """
    url='https://ehall.seu.edu.cn/gsapp/sys/yddjzxxtjappseu/modules/hdyy/getActivityDetail.do'
    
    r = requests.request("POST", url, headers=lecture_headers, data={'wid': wid})
    
    res = r.json()
    if res['code'] != 0:
        print('保活失效，请检查cookie！')
    else:
        print('用户身份有效，登录状态保活')
    
def rob(lecture):
    """
    定时抢讲座任务

    Args:
        lecture (dict): 讲座信息
    """
    
    print(f"定时预约任务开始, 讲座: {lecture['JZMC']}, wid: {lecture['WID']}")
    for attempt in range(3):
        # 获取验证码图片
        verify_code_img_base64 = get_lecture_verify_code(lecture['WID'])
        # 解析验证码
        verify_code = parse_verify_code(verify_code_img_base64)
        print("解析验证码成功: ", verify_code)
        # 尝试预约讲座
        res = reserve_lecture(lecture['WID'], verify_code)
        print("预约结果: ", res)
        if res:
            break
        elif attempt == 0:
            print("预约失败，1秒后重试")
            time.sleep(1)
    

if __name__ == "__main__":
    # 获取目标讲座信息
    lectures = get_target_lectures(lecture_keys)
    if lectures is None:
        exit(1)
    
    for lecture in lectures:
        print('搜索到目标讲座: ', lecture['JZMC'])
    
    # 立即检查一次保活
    keep_alive(lectures[0]['WID'])
    
    # 启动定时任务
    scheduler = BlockingScheduler()
    scheduler.add_job(keep_alive, 'interval', seconds=30, args=[lectures[0]['WID']])
    
    # 为每个讲座设置预约任务，间隔0.5秒
    for i, lecture in enumerate(lectures):
        scheduler.add_job(rob, 'cron', hour=19, minute=0, second=i*0.5, args=[lecture])
    
    scheduler.start()
