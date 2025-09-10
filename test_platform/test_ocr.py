import requests
import base64


def get_baidocr_result(img_path,access_token):
    request_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/handwriting"
    # 二进制方式打开图片文件
    f = open(img_path, 'rb')
    img = base64.b64encode(f.read())
    params = {
        "image": img,  # 这里应该放置编码后的图像数据
        "recognize_granularity": 'small'
    }
    request_url = request_url + "?access_token=" + access_token
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    try:
        # 设置timeout为30秒
        response = requests.post(request_url, data=params, headers=headers, timeout=30)
        if response:
            result = response.json()
            return result
    except requests.Timeout:
        # 请求超时处理
        print("连接校园网: cd /home/xiaoman/ ./ecnu")
    except requests.RequestException as e:
        # 其他任何请求异常处理
        print(f"请求遇到问题: {e}")
        return None

def get_access_token():
    api_key = 'Qv8UmUUha0P5gv6ZHLjAW58d'
    secret_key = 'fyDphQt6Fq8hO92axA5Fj754CWkSUNev'

    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    payload = ""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    response = requests.request ("POST", url, headers=headers, data=payload)
    access_token = response.json()['access_token']
    # print("response.text:",response.text)
    # print("access_token:",access_token)
    return access_token


if __name__ == '__main__':
    access_token = get_access_token()
    print('access_token:',access_token)
    img_path = '../img/509.jpg'
    ocr_result = get_baidocr_result(img_path, access_token)
    print(ocr_result)