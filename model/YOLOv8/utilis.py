import json
from PIL import Image
import cv2
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from ultralytics import YOLO
import subprocess
import requests
font_path = "/home/xiaoman/packages/chinese-font/Alibaba_PuHuiTi_2.0_45_Light_45_Light.ttf"



def replace_punctuation(text):
    punctuation_mapping = {
        ',': '，',
        # '.': '。',
        '?': '？',
        '!': '！',
        ";":'；',
        ":":'：'
    }
    for en, zh in punctuation_mapping.items():
        text = text.replace(en, zh)
    return text

def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

def write_to_json(data, out_path):
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False,indent=4)

def decode_corrected_passage(json_str):
    decoded_response = json.loads(json_str)
    corrected_passage = decoded_response.get('data', '')
    return corrected_passage

def calculate_iou(bbox1, bbox2):
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])
    if x2 < x1 or y2 < y1:
        return 0
    intersection_area = (x2 - x1) * (y2 - y1)
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    min_area = min(area1, area2)
    iou = intersection_area / min_area
    return iou

def draw_text_with_pil(img, text, position, color,height=None):
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)

    font_size = 10
    font = ImageFont.truetype(font_path, font_size)

    draw.text(position, text, fill=color, font=font)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

def get_baidu_bbox(chars_location):
    bboxes = []
    for index, char_info in enumerate(chars_location):
        char_name = char_info['char']
        location = char_info['location']
        x1 = location['left']
        y1 = location['top']
        x2 = location['left'] + location['width']
        y2 = location['top'] + location['height']
        info = {
            'id': index,
            'char': char_name,
            'bbox': [x1, y1, x2, y2],
        }
        bboxes.append(info)
    return bboxes

