from ultralytics import YOLO
import cv2
import numpy as np
import json
import requests
import os
import matplotlib.pyplot as plt
from paddleocr import PaddleOCR
from PIL import Image, ImageDraw, ImageFont
import subprocess
from model.YOLOv8.visualization import visualize
from model.YOLOv8.utilis import write_to_json,read_json_file,calculate_iou,draw_text_with_pil,get_baidu_bbox
# from .visualization import visualize
# from .utilis import write_to_json,read_json_file,calculate_iou,draw_text_with_pil,get_baidu_bbox,qwen_predict


# Paddleocr目前支持中英文、英文、法语、德语、韩语、日语，可以通过修改lang参数进行切换
# 参数依次为`ch`, `en`, `french`, `german`, `korean`, `japan`
ocr = PaddleOCR(use_angle_cls=True, lang="ch")
base_dir = os.path.dirname(os.path.abspath(__file__))
model_dir = os.path.dirname(base_dir)
project_dir = os.path.dirname(model_dir)
yolo_checkpoint = os.path.join(project_dir, 'checkpoint', 'yolov8_best.pt')
yolo_model = YOLO(yolo_checkpoint)



def yolo_detect_and_draw(img_path, output_path,output_bbox_path,withocr=False):
    '''
         only detect and draw bounding box
    '''
    results = yolo_model([img_path, ])
    img = cv2.imread(img_path)
    boxes = results[0].boxes
    colors = {0: (0, 255, 0), 1: (0, 0, 255)}

    bboxes = []
    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        class_id = int(box.cls)
        color = colors.get(class_id, (0, 255, 255))
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

        # 选择是否在yolo定位的图像上面进行ocr识别
        if withocr == True:
            cropped_img = img[y1:y2, x1:x2]
            cropped_np_img = np.array(cropped_img)
            result = ocr.ocr(cropped_np_img, cls=True)
            print('result:', result)
            if result and result[0]:
                char = result[0][0][1][0]
            else:
                char = None
            info = {
                'char':char,
                'bbox':[x1, y1, x2, y2]
            }
            bboxes.append(info)
            if result and result[0]:
                for line in result[0]:
                    text = line[-1][0]
                    text_position = (x1, y1 - 10)
                    img = draw_text_with_pil(img, text, text_position, (0, 0, 255))

    if output_path is not None:
        cv2.imwrite(output_path, img)
        print('Saved image to {}'.format(output_path))
    else:
        plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        plt.axis('off')
        plt.show()

    sorted_bboxes = sorted(bboxes, key=lambda x: (x['bbox'][1], x['bbox'][0]))
    write_to_json(sorted_bboxes, output_bbox_path)

def get_location(json_path):
    data = read_json_file(json_path)
    location = data['location']
    location = json.loads(location)
    words_result = location['words_result']
    chars_location = [char_info for word in words_result for char_info in word['chars']]
    return chars_location



def baidu_detect(img_path,json_path,out_path,output_bbox_path):
    img = Image.open(img_path)
    draw = ImageDraw.Draw(img)
    chars_location = get_location(json_path)
    bboxes = get_baidu_bbox(chars_location)
    for item in bboxes:
        bbox = item['bbox']
        draw.rectangle([bbox[0], bbox[1], bbox[2], bbox[3]], outline="red")

    img.save(out_path)
    print('Saved image to {}'.format(out_path))
    write_to_json(bboxes, output_bbox_path)




def update_baidu_bbox_with_yolo(baidu_bbox, yolo_bbox, threshold=0.5):
    for yolo_item in yolo_bbox:
        yolo_bbox = yolo_item['bbox']
        for baidu_item in baidu_bbox:
            if calculate_iou(baidu_item['bbox'], yolo_item['bbox']) > threshold:
                baidu_item['new_bbox'] = yolo_bbox
    print('------ Update_baidu_bbox_with_yolo')
    return baidu_bbox


def redraw(img_path,baidu_bbox_path,out_path):
    img = Image.open(img_path)
    draw = ImageDraw.Draw(img)

    with open(baidu_bbox_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    for item in data:
        if item.get('new_bbox'):
            new_bbox = item['new_bbox']
            draw.rectangle([new_bbox[0], new_bbox[1], new_bbox[2], new_bbox[3]], outline="blue")
    img.save(out_path)
    print('Saved image to {}'.format(out_path))


def get_m2(source,predict):
    input_file = '../evaluation/scorers/ChERRANT/samples/yolo.input'
    output_file = '../evaluation/scorers/ChERRANT/samples/yolo.hyp'
    hyp_para_file = '../evaluation/scorers/ChERRANT/samples/yolo.hyp.para'
    hyp_m2_file = '../evaluation/scorers/ChERRANT/samples/yolo.hyp.m2.char'

    with open(input_file, 'w') as f_input, open(output_file, 'w') as f_output:
        f_input.write(source)
        f_output.write(predict)
    paste_command = f"paste {input_file} {output_file} | awk '{{print NR\"\\t\"$p}}' > {hyp_para_file}"
    subprocess.run(paste_command, shell=True, check=True)

    m2_command = f"python ../evaluation/scorers/ChERRANT/parallel_to_m2.py -f {hyp_para_file} -o {hyp_m2_file} -g char"
    subprocess.run(m2_command, shell=True, check=True)
    print('m2格式成功')

if __name__ == '__main__':
    id = 509
    img_path = f'../../img/{id}.jpg'
    json_path = f'../../img/{id}.json'

    out_yolo_img_path = f'./detect_result/{id}_yolo_detect.png'
    out_yolo_bbox_path = f'./detect_result/{id}_yolo_bbox.json'

    out_baidu_img_path = f'./detect_result/{id}_baidu_detect.png'
    out_baidu_bbox_path = f'./detect_result/{id}_baidu_bbox.json'

    ''' yolo detect '''
    # yolo_detect_and_draw(img_path=img_path,output_path=out_yolo_img_path,output_bbox_path=out_yolo_bbox_path,withocr=True)
    yolo_detect_and_draw(img_path=img_path,output_path=out_yolo_img_path,output_bbox_path=out_yolo_bbox_path,withocr=False)

    ''' baidu ocr '''
    baidu_detect(img_path=img_path,json_path=json_path,out_path=out_baidu_img_path,output_bbox_path=out_baidu_bbox_path)

    ''' update'''
    baidu_bbox = read_json_file(out_baidu_bbox_path)
    yolo_bbox = read_json_file(out_yolo_bbox_path)
    baidu_new_bbox = update_baidu_bbox_with_yolo(baidu_bbox,yolo_bbox)
    write_to_json(baidu_new_bbox, out_baidu_bbox_path)

    ''' re-draw-baidu'''
    redraw_outpath = f'./detect_result/{id}_baidu_redraw.png'
    redraw(img_path=out_baidu_img_path,baidu_bbox_path=out_baidu_bbox_path,out_path=redraw_outpath)

    ''' Qwen纠错 '''
    chars_location = get_location(json_path)
    source_text = ''.join([c['char'] for c in chars_location])
    source,predict = qwen_predict(source_text)

    ''' m2 '''
    get_m2(source, predict)

    ''' visualization '''
    visualize(id=id)