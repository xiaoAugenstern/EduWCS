import cv2
import json
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from model.YOLOv8.utilis import read_json_file, draw_text_with_pil
import matplotlib.pyplot as plt


def find_split_position(source, word_ordered):
    for i in range(1, len(source)):
        part1 = source[:i]
        part2 = source[i:]
        if part2 + part1 == word_ordered:
            return i
    return -1

def get_xy(bbox):
    x1 = bbox[0]
    y1 = bbox[1]
    x2 = bbox[2]
    y2 = bbox[3]
    width = abs(x2 - x1)
    height = abs(y2-y1)
    return x1, y1, x2, y2, width, height

def get_start_end(bbox):
    x1 = bbox['start_x']
    y1 = bbox['start_y']
    x2 = bbox['end_x']
    y2 = bbox['end_y']
    width = abs(x2 - x1)
    height = abs(y2 - y1)
    return x1, y1, x2, y2, width, height

def parse_m2_file(m2_path):
    with open(m2_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    corrections = []
    for line in lines:
        if line.startswith('S'):
            print(line)
        if line.startswith('T'):
            print(line)
        if line.startswith("A"):
            parts = line.split("|||")
            start, end = map(int, parts[0].split()[1:3])
            operation_type = parts[1]
            correction = parts[2]
            corrections.append({
                "start": start,
                "end": end,
                "operation_type": operation_type,
                "modified_result": correction
            })
    return corrections


def check_line_breaks(start, end, char_locations):
    """
    检查从 start 到 end 之间的字符是否有换行，返回每行的字符索引范围。
    """
    line_breaks = []
    line_start = start

    for i in range(start, end):
        info = char_locations[i]
        info_bbox = info.get('new_bbox', info.get('bbox'))
        x1, y1, x2, y2 = info_bbox
        width = x2 - x1

        # 检查下一个字符是否换行
        if i + 1 < end:
            next_info = char_locations[i + 1]
            next_bbox = next_info.get('new_bbox', next_info.get('bbox'))
            next_x1 = next_bbox[0]

            if abs(next_x1 - x1) > 3 * width:            # 如果字符间距超过3倍宽度，认为换行
                line_breaks.append((line_start, i + 1))  # 记录当前行的范围
                line_start = i + 1                       # 更新下一行的起点

    line_breaks.append((line_start, end))  # 最后一行,end不能算
    return line_breaks

def draw_on_img(img,correct_info):
    ''' img = cv2.imread(img_path) '''
    for correction in correct_info:
        correct_id = correction['correct_id']
        img_mark_type = correction['img_mark_type']
        img_box = correction['img_box']
        modified_result = correction['modified_result']

        if img_mark_type == 'add':
            start_x, start_y, end_x, end_y,width,height = get_start_end(img_box[0])
            text_position = (start_x, start_y - height // 2)
            cv2.arrowedLine(img, (start_x,start_y), (end_x,end_y), (0, 0, 255), 2, tipLength=0.3)
            img = draw_text_with_pil(img=img, text=modified_result, position=text_position, color=(255, 0, 0), height=height)

        elif img_mark_type == 'delete':
            for box in img_box:
                method1 = box['method1']
                delete_line = method1['delete_line']
                start_x, start_y, end_x, end_y, width, height = get_start_end(delete_line)
                cv2.line(img, (start_x, start_y), (end_x, end_y), (0, 0, 255), 2)

        elif img_mark_type == 'edit':
            for index,box in enumerate(img_box):
                start_x, start_y, end_x, end_y, width, height = get_start_end(box)
                # 画框
                cv2.rectangle(img, (start_x, start_y), (end_x, end_y), (0, 0, 255), 2)
                # 在每行的矩形框上方写入 corrected_text（只在第一行上方写）
                if index == 0:
                    position = (start_x, start_y - height // 1.8)
                    img = draw_text_with_pil(img=img, text=modified_result, position=position, color=(255, 0, 0),height=height)

        elif img_mark_type == 'word-order':
            for box in img_box:
                method1 = box['method1']
                line_top = method1['top']
                line_right = method1['right']
                line_bottom = method1['bottom']
                cv2.line(img, (line_right['x1'],line_right['y1']), (line_right['x2'],line_right['y2']), (0, 0, 255), 2)
                cv2.line(img, (line_top['x1'],line_top['y1']),(line_top['x2'],line_top['y2']), (0, 0, 255), 2)
                cv2.line(img, (line_bottom['x1'],line_bottom['y1']),(line_bottom['x2'],line_bottom['y2']), (0, 0, 255), 2)
    return img

def draw_insertion(start,char_locations):
    if start == len(char_locations):
        end_info = char_locations[-1]
        bbox = end_info.get('new_bbox', end_info['bbox'])
        x1, y1, x2, y2, width, height = get_xy(bbox)
        # 在最后一个字符之后绘制箭头
        arrow_start = (x2 + width // 5, y1)
        arrow_end = (x2 + width // 5, y2)
    else:
        start_info = char_locations[start]
        bbox = start_info.get('new_bbox', start_info['bbox'])
        x1, y1, x2, y2, width, height = get_xy(bbox)
        arrow_start = (x1 - width // 5, y1)
        arrow_end = (x1 - width // 5, y2)
    img_box = [{'start_x':arrow_start[0], 'start_y':arrow_start[1], 'end_x':arrow_end[0], 'end_y':arrow_end[1]}]
    return img_box


def draw_delete(start,end,char_locations):
    line_breaks = check_line_breaks(start, end, char_locations)
    img_box = []
    for line_start, line_end in line_breaks:
        start_info = char_locations[line_start]
        end_info = char_locations[line_end - 1]  # 因为 line_end 是排除性区间

        start_bbox = start_info.get('new_bbox', start_info['bbox'])
        end_bbox = end_info.get('new_bbox', end_info['bbox'])

        start_x1,start_y1,start_x2,start_y2,start_width,start_height = get_xy(start_bbox)
        end_x1,end_y1,end_x2,end_y2,end_width,end_height = get_xy(end_bbox)

        line_y = (start_y1 + start_y2) // 2

        info = {
            'method1':{'delete_line':{'start_x':start_x1,'start_y':line_y,'end_x':end_x2,'end_y':line_y}},    # 国汉删除返回框
            'method2':{'delete_box':{'start_x':start_x1,'start_y':start_y1,'end_x':end_x2,'end_y':end_y2}}  # 返回直线
        }

        # delete_box = {'start_x':start_x1,'start_y':line_y,'end_x':end_x2,'end_y':line_y}
        # img_box.append(delete_box)
        img_box.append(info)
    return img_box


def draw_substitute(start, end, char_locations):
    line_breaks = check_line_breaks(start, end, char_locations)
    img_box = []
    for line_start, line_end in line_breaks:
        start_info = char_locations[line_start]
        end_info = char_locations[line_end - 1]

        start_bbox = start_info.get('new_bbox', start_info['bbox'])
        end_bbox = end_info.get('new_bbox', end_info['bbox'])

        start_x1, start_y1, start_x2, start_y2, start_width, start_height = get_xy(start_bbox)
        end_x1, end_y1, end_x2, end_y2, end_width, end_height = get_xy(end_bbox)

        img_box.append({'start_x':start_x1, 'start_y':start_y1, 'end_x':end_x2, 'end_y':end_y2})
    return img_box

def draw_word_order(start, end, corrected_text, char_locations):
    line_breaks = check_line_breaks(start, end, char_locations)
    original = ''.join(char_locations[i]['char'] for i in range(start, end))
    corrected = corrected_text.replace(' ', '')
    position = find_split_position(original, corrected) - 1
    # original：的变化 、corrected：变化的、 position=0
    add_text = original[position+1:]
    img_box = []
    for line_start, line_end in line_breaks:
        start_info = char_locations[line_start]
        break_info = char_locations[line_start+position]
        end_info = char_locations[line_end - 1]

        start_bbox = start_info.get('new_bbox', start_info['bbox'])
        break_bbox = break_info.get('new_bbox', break_info.get('bbox'))
        end_bbox = end_info.get('new_bbox', end_info['bbox'])

        start_x1, start_y1, start_x2, start_y2, start_width, start_height = get_xy(start_bbox)
        break_x1, break_y1, break_x2, break_y2, break_width, break_height = get_xy(break_bbox)
        end_x1, end_y1, end_x2, end_y2, end_width, end_height = get_xy(end_bbox)

        line_top = [(start_x1,start_y1), (break_x2,start_y1)]
        line_right = [(break_x2,break_y1),(break_x2,break_y2)]
        line_bottom = [(break_x2,break_y2),(end_x2,end_y2)]

        line_bottom_center = [(break_x2,(break_y1+break_y2)//2),(end_x2,(end_y1+end_y2)//2)]  # line_bottom变到中间，
        add_arrow = [(start_x1 - start_width//5,start_y1),(start_x1 - start_width//5,start_y2)] # line_top前面加

        info = {
            'method1':{
                'top': {'x1': line_top[0][0], 'y1': line_top[0][1], 'x2': line_top[1][0], 'y2': line_top[1][1]},
                'right': {'x1': line_right[0][0], 'y1': line_right[0][1], 'x2': line_right[1][0], 'y2': line_right[1][1]},
                'bottom': {'x1': line_bottom[0][0], 'y1': line_bottom[0][1], 'x2': line_bottom[1][0], 'y2': line_bottom[1][1]},
            },
            'method2':{
                'add':{'x1':add_arrow[0][0],'y1':add_arrow[0][1],'x2':add_arrow[1][0],'y2':add_arrow[1][1],'modified_result':add_text},
                'delete':{'x1':line_bottom_center[0][0],'y1':line_bottom_center[0][1],'x2':line_bottom_center[1][0],'y2':line_bottom_center[1][1],'modified_result':''},
            }

        }
        img_box.append(info)
    return img_box



def apply_corrections_to_image(char_locations, corrections):
    correct_info = []
    img_mark_type = None
    img_box = None
    for index,correction in enumerate(corrections):
        start = correction["start"]
        end = correction["end"]
        operation_type = correction["operation_type"][0]
        corrected_text = correction["modified_result"]
        fk_error_id = correction.get("fk_error_id", None)  # 如果没有 fk_error_id，则设置为 None
        print(f'correction {index}:', start,end,operation_type,corrected_text)

        if operation_type == 'M':     # Insertion
            img_mark_type = 'add'
            img_box = draw_insertion(start,char_locations)
        elif operation_type == 'R':   # delete
            img_mark_type = 'delete'
            img_box = draw_delete(start, end, char_locations)
        elif operation_type == 'S':   # substitute
            img_mark_type = 'edit'
            img_box = draw_substitute(start, end, char_locations)
        elif operation_type == 'W':   # word-order
            img_mark_type = 'word-order'
            img_box = draw_word_order(start, end, corrected_text,char_locations)
        info = {
            'correct_id':index,
            'img_box':img_box,
            'modified_result':corrected_text.replace(' ',''),
            'img_mark_type':img_mark_type,
            'fk_error_id':fk_error_id
        }
        correct_info.append(info)
    return correct_info


def img_show(img):
    # 将 BGR 转换为 RGB 以便使用 plt 显示
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    plt.figure(figsize=(10, 10))  # 设置图片显示大小
    plt.imshow(img_rgb)
    plt.axis('off')  # 隐藏坐标轴
    plt.show()



def visualize(id):
    img_path = f'../../img/{id}.jpg'
    out_baidu_bbox_path = f'./detect_result/{id}_baidu_bbox.json'
    m2_path = '../evaluation/scorers/ChERRANT/samples/yolo.hyp.m2.char'
    output_path = f'./detect_result/{id}_m2.png'

    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"----- Failed to load image from {img_path}")

    # 解析m2文件
    corrections = parse_m2_file(m2_path=m2_path)
    # 更新后的百度云坐标
    char_locations = read_json_file(out_baidu_bbox_path)
    # apply corrections to image
    correct_info = apply_corrections_to_image(char_locations, corrections)
    # 给国汉返回的
    guohan_info = process_correct_info(correct_info)
    # 画新图
    new_img = draw_on_img(img, correct_info)
    img_show(new_img)

    cv2.imwrite(output_path, new_img)
    print('----- Write image to {}'.format(output_path))
    print('correct_info',correct_info)
    print('guphan_info',guohan_info)


def make_info(start_x,start_y,end_x,end_y,modified_result,img_mark_type,fk_error_id):
    info = {
        'start_x':start_x,
        'start_y':start_y,
        'end_x':end_x,
        'end_y':end_y,
        'modified_result':modified_result,
        'img_mark_type':img_mark_type,
        'fk_error_id':fk_error_id
    }
    return info

def process_correct_info(correct_info):
    process_info = []
    for info in correct_info:
        img_mark_type = info['img_mark_type']
        modified_result = info['modified_result']
        img_box = info['img_box']
        fk_error_id = info['fk_error_id']
        punctuation_set = set('：；，。？！、~!@#$%^&*()_-+=[]{}|\\:;"\'<>,.?/')
        if modified_result in punctuation_set:
            continue
        if img_mark_type == 'delete':
            modified_result = ''
        # 乱序操作
        if img_mark_type == 'word-order':
            method2 = img_box[0]['method2']
            add = method2['add']
            delete = method2['delete']
            # add信息
            add_info = make_info(add['x1'],add['y1'],add['x2'],add['y2'],add['modified_result'],'add',fk_error_id)
            process_info.append(add_info)
            # delete信息
            if abs(delete['y2']-delete['y1']) > 19:  # 防止平台选不中
                delete_info = make_info(delete['x1'],delete['y1'],delete['x2'],delete['y2'],'','delete',fk_error_id)
                process_info.append(delete_info)

        # 删除操作
        elif img_mark_type == 'delete':
            for box in img_box:
                method2 = box['method2']
                delete_box = method2['delete_box']
                if abs(delete_box['end_y']-delete_box['start_y']) > 19:
                    delete_info = make_info(delete_box['start_x'],delete_box['start_y'],delete_box['end_x'],delete_box['end_y'],'','delete',fk_error_id)
                    process_info.append(delete_info)
        else:
            for id,box in enumerate(img_box):
                if id == 0:
                    fk_info = make_info(box['start_x'],box['start_y'],box['end_x'],box['end_y'],modified_result,img_mark_type,fk_error_id)
                    process_info.append(fk_info)
                else:
                    # substitue 只在第一个modified_result有结果
                    fk_info = make_info(box['start_x'], box['start_y'], box['end_x'], box['end_y'],'', img_mark_type,fk_error_id)
                    process_info.append(fk_info)
    return process_info


if __name__ == "__main__":
    id = 509
    visualize(id=id)

