import json
import os
import subprocess

def find_sentence(sent_starts, position):
    # 遍历句子起始位置列表，找到给定位置所属的句子
    for i, start in enumerate(sent_starts):
        if position < sent_starts[i+1] if i+1 < len(sent_starts) else float('inf'):
            return i
    return None


def find_all_positions(template, char):
    positions = [i for i, c in enumerate(template) if c == char]
    return positions

def recognize(result):
    words_result = result['words_result']
    chars_location = [char_info for word in words_result for char_info in word['chars']]
    original_text = ''.join([c['char'] for c in chars_location])
    return original_text,chars_location

def write_to_json(data, out_path):
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


def df_to_dict(result):
    for _, row in result.iterrows():
        # 示例：将每一行转为字典
        error_info = row.to_dict()
    return error_info


def get_char_position_in_source(word_positions, source_list, start, end):
    """
    将source_list中的索引转换为在source中的字符位置
    :param source_list: 列表，分割后的单词列表
    :param start: 在source_list中的起始位置
    :param end: 在source_list中的结束位置
    :return: 在source字符串中的起始和结束位置
    """
    # 在source的最后一个字后面添加
    if start >= len(word_positions) or end > len(word_positions) or start < 0 or end < start:
        start_position = word_positions[-1] + len(source_list[-1])
        end_position = start_position
    else:
        # 计算start和end在source中的字符位置
        start_position = word_positions[start]
        end_position = word_positions[end - 1] + len(source_list[end - 1])  # end是开放的，因此需要加上单词的长度
    return start_position, end_position


def parse_m2_file2(m2_path, granularity='char'):
    with open(m2_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    corrections = []
    source, target, start, end, operation_type, original_result, modified_result = None, None, None, None, None, None, None
    print('m2_lines')
    for line in lines:
        print(line)
        if line.startswith('S'):
            source_list = line.strip().split(' ')[1:]  # 去掉\n，按照空格分割,去掉开头的S，
            source = ''.join(source_list)
            print('source:', source)
            current_position = 0
            word_positions = []  # 存储每个单词在source中的起始位置
            for word in source_list:
                word_positions.append(current_position)
                current_position += len(word)  # 更新当前位置

        elif line.startswith('T'):
            target_list = line.strip().split(' ')
            target = ''.join(target_list[1:])
            print('target:', target)

        elif line.startswith("A"):
            parts = line.split("|||")
            start, end = map(int, parts[0].split()[1:3])
            operation_type = parts[1]
            if operation_type[0] == 'R':
                modified_result = ''
            else:
                modified_result = parts[2].replace(' ', '')

            if operation_type[0] == 'M':  # missing
                original_result = None
            elif operation_type[0] in ['S', 'W', 'R']:  # substitute/word-order/redundant
                original_result = ''.join(source_list[start:end])

            if granularity == 'word':
                start, end = get_char_position_in_source(word_positions, source_list, start, end)

            corrections.append({
                'start': start,
                'end': end,       # 不包含
                "operation_type": operation_type,
                "modified_result": modified_result,
                'original_result': original_result
            })
    return corrections


def get_m2(source, predict, granularity='char'):
    cherrant_path = '/home/xiaoman/project/Qwen-GEC/model/evaluation/scorers/ChERRANT'
    input_file = os.path.join(cherrant_path, 'samples', f'{granularity}_error_type.input')
    output_file = os.path.join(cherrant_path, 'samples', f'{granularity}_error_type.hyp')
    hyp_para_file = os.path.join(cherrant_path, 'samples', f'{granularity}_error_type.hyp.para')
    hyp_m2_file = os.path.join(cherrant_path, 'samples', f'{granularity}_error_type.hyp.m2.char')

    with open(input_file, 'w') as f_input, open(output_file, 'w') as f_output:
        f_input.write(source)
        f_output.write(predict)

    # Run the paste and awk command
    paste_command = f"paste {input_file} {output_file} | awk '{{print NR\"\\t\"$p}}' > {hyp_para_file}"
    subprocess.run(paste_command, shell=True, check=True)

    # Run the parallel_to_m2.py script for char-level evaluation
    parallel_path = os.path.join(cherrant_path, 'parallel_to_m2.py')
    m2_command = f"/home/xiaoman/anaconda3/envs/cherrant/bin/python {parallel_path} -f {hyp_para_file} -o {hyp_m2_file} -g {granularity}"
    subprocess.run(m2_command, shell=True, check=True)
    return hyp_m2_file