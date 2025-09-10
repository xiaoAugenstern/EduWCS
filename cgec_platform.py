import base64
import requests
from io import BytesIO
import subprocess
import cv2
import json
from PIL import Image
import os
import time
from ultralytics import YOLO
from model.YOLOv8.utilis import get_baidu_bbox
from model.YOLOv8.visualization import parse_m2_file,apply_corrections_to_image,process_correct_info
from model.YOLOv8.yolo_detect import update_baidu_bbox_with_yolo

from text_processor import qwen_predict

yolo_checkpoint = os.path.join(os.path.dirname(os.path.abspath(__file__)),'checkpoint/yolov8_best.pt')
font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'Alibaba_PuHuiTi_2.0_45_Light_45_Light.ttf')
cherrant_env_path = '/root/miniconda3/envs/cherrant/bin/python'

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
    return access_token


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
        print("没有网络")
    except requests.RequestException as e:
        # 其他任何请求异常处理
        print(f"请求遇到问题: {e}")
        return None

def recognize(result):
    words_result = result['words_result']
    chars_location = [char_info for word in words_result for char_info in word['chars']]
    original_text = ''.join([c['char'] for c in chars_location])
    return original_text,chars_location


def reorder_annotations(input_file, order_file, output_file):
    # 读取顺序文件（w.txt）
    with open(order_file, 'r', encoding='utf-8') as f:
        order_lines = [line.strip() for line in f if line.strip()]
    # 读取输入文件（input.txt）
    with open(input_file, 'r', encoding='utf-8') as f:
        input_lines = [line.strip() for line in f if line.strip()]
    # 初始化
    s_line = ""
    t_line = ""
    a_lines = {}
    a = 1
    for line in input_lines:
        if line.startswith("S "):
            s_line = line
        elif line.startswith("T0-A0"):
            t_line = line
        elif line.startswith("A"):

            key = f"A{a}"
            a += 1
            a_lines[key] = line
    # 构建输出内容
    output = [s_line, t_line]
    for key in order_lines:
        if key in a_lines:
            output.append(a_lines[key])
        else:
            print(f"[Warning] {key} not found in input.")
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in output:
            f.write(line + '\n')
    print(f"[Info] Done! Output written to {output_file}")


def get_m2(source,predict,granularity='char'):
    current_path = os.path.join(os.path.dirname(__file__))
    cherrant_path = os.path.join(current_path,'model/evaluation/scorers/ChERRANT')
    samples_path = os.path.join(cherrant_path,'samples')
    parallel_to_m2_path = os.path.join(cherrant_path, 'parallel_to_m2.py')

    input_file = os.path.join(samples_path,'platform.input')
    output_file = os.path.join(samples_path,'platform.hyp')
    hyp_para_file = os.path.join(samples_path,'platform.hyp.para')
    hyp_m2_file = os.path.join(samples_path,f'platform.hyp.m2.{granularity}')

    with open(input_file, 'w') as f_input, open(output_file, 'w') as f_output:
        f_input.write(source)
        f_output.write(predict)
    paste_command = f"paste {input_file} {output_file} | awk '{{print NR\"\\t\"$p}}' > {hyp_para_file}"
    subprocess.run(paste_command, shell=True, check=True)

    m2_command = f"{cherrant_env_path} {parallel_to_m2_path} -f {hyp_para_file} -o {hyp_m2_file} -g {granularity}"
    subprocess.run(m2_command, shell=True, check=True)

    # 在此修改使得************ls输出的platfrom文件顺序改变
    single_edits_generation_path = os.path.join(current_path,'EAGCS/EAGCS/single_edit_generation.py')
    PPL_calculator_path = os.path.join(current_path,'EAGCS/EAGCS/platformPPL.py')

    variants_txt_path = os.path.join(samples_path,'platformVariantput.txt')
    results_txt_path = os.path.join(samples_path,'platform.txt')
    orderedPlatform = os.path.join(samples_path,f'platformOrdered.hyp.m2.{granularity}')

    beforeOrderFile = hyp_m2_file  # 相当于hype.m2.char
    model_path = os.path.join(current_path,'EAGCS/EAGCS/model/gpt2-Chinese')
    single_edit_cmd = f"{cherrant_env_path} {single_edits_generation_path} --input {beforeOrderFile} --output {variants_txt_path}"
    subprocess.run(single_edit_cmd, shell=True, check=True)
    
    ppl_calc_cmd = f"{cherrant_env_path} {PPL_calculator_path} --input {variants_txt_path} --output {results_txt_path} --model {model_path} "
    subprocess.run(ppl_calc_cmd, shell=True, check=True)
    reorder_annotations(beforeOrderFile, results_txt_path, orderedPlatform)
    return orderedPlatform


def get_yolo_bbox(img_path):
    yolo_model = YOLO(yolo_checkpoint)
    results = yolo_model([img_path, ])
    boxes = results[0].boxes
    bboxes = []
    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        info = {
            'bbox': [x1, y1, x2, y2]
        }
        bboxes.append(info)
    sorted_bboxes = sorted(bboxes, key=lambda x: (x['bbox'][1], x['bbox'][0]))
    return sorted_bboxes


def img_predict(img_path):
    '''
        小兰平台接口
        input：img_path 图片路径
        output: source, target, correct_info, guohan_info
    '''
    # 调用baidu ocr的api获得单字定位，确保服务器联网，不然OCR接口connect error
    print('============= Img_predict =================')
    start_time = time.time()
    access_token = get_access_token()
    ocr_result = get_baidocr_result(img_path, access_token)

    # 作文原始文本，chars_location
    original_text, chars_location = recognize(ocr_result)

    # qiwen大模型纠错
    source, target,_ = qwen_predict(original_text)

    # m2格式
    hyp_m2_file = get_m2(source, target)
    corrections = parse_m2_file(m2_path=hyp_m2_file)
    # yolo detect
    yolo_bbox = get_yolo_bbox(img_path)
    # baidu bbox
    baidu_bbox = get_baidu_bbox(chars_location)
    # update baidu_new_bbox
    baidu_new_bbox = update_baidu_bbox_with_yolo(baidu_bbox, yolo_bbox)
    print('Update baidu_new_bbox!!')

    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"----- Failed to load image from {img_path}")

    correct_info = apply_corrections_to_image(baidu_new_bbox, corrections)
    guohan_info = process_correct_info(correct_info)
    end_time = time.time()   # ⏱ 结束计时
    elapsed_time = end_time - start_time
    print(f"处理时间: {elapsed_time:.2f} 秒")

    return source, target,correct_info,guohan_info


if __name__ == '__main__':

    ''' img predict'''
    # img_path = './img/2195.png'
    # img_predict(img_path)

    ''' guohan predict'''
    data_path = 'test_platform/test.json'
    with open(data_path,'r',encoding='utf-8') as f:
        data = json.load(f)
    ocr_result = data['ocr_result']
    original_text, chars_location = recognize(ocr_result)
    img_base = data['img_base64']
    print('original text:', original_text)
