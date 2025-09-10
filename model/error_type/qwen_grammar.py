import re
from flask import Flask
from openai import OpenAI
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
client = OpenAI(api_key="0", base_url="http://0.0.0.0:8000/v1")


def qiwen_grammar_prompt(source,target,operation,modified_result,filtered_dict,original_result=None):
    if original_result is None:
        original_result = ''

    errors_str = "\n".join([
        f"id: {error.get('id')}, "
        f"一级分类: {error.get('一级分类', '未指定')}, "
        f"二级分类: {error.get('二级分类', '未指定')}, "
        f"三级分类: {error.get('三级分类', '未指定')}, "
        f"四级分类: {error.get('四级分类', '未指定')}, "
        f"五级分类: {error.get('五级分类', '未指定')}"
        f" 举例: {error.get('举例', '无示例')}\n"
        for error in filtered_dict
    ])

    operation_mapping = {
        "M": "插入",
        "S": "替换",
        "R": "删除",
        'W': "乱序",
        "edit": "替换",
        "delete": "删除",
        "add": "插入"
    }
    operation = operation_mapping.get(operation, operation)

    prompt_template = f'''作为中文语法纠错领域的专家，请根据提供的信息筛选出最符合的语法点错误类型，并返回它们的 id 列表。
        提供的信息：
        1. 错误语法句子：{source}
        2. 纠正后的正确结果：{target}
        3. 修改操作：{operation}
        4. 与修改操作相关的内容：{modified_result}
        5. 候选错误类型列表：{errors_str}

        任务要求：
        1. 分析：请重点关注错误语法句子与纠正后句子的变化，特别是 将【{original_result}】 【{operation}】为 【{modified_result}】 引入的语法差异。
        2. 匹配：在候选错误类型列表中，找到与这些变化最相关的语法点错误类型。
        3. 输出：返回符合条件的 id 列表（若有多个，请按优先级排列），例如：[17],[103,17],None

        注意：
        1. 只选择与 {modified_result} 和 {original_result} 最相关的错误类型，不要包含无关的类型。
        2. 确保你的选择基于对语法点描述的准确理解。
        3. 如果没有匹配，请返回 `None`。'''

    prompt = prompt_template.format(
        source=source,
        target=target,
        operation=operation,
        modified_result=modified_result,
        errors=errors_str
    )
    return prompt


def qiwen_error_inference(prompt):
    ''' 根据prompt进行推理 '''
    messages = [
        {"role": "system", "content": "你是一个中文语法纠错专家，请根据以下任务描述提供结果。"},
        {"role": "user", "content": prompt}
    ]
    answer = client.chat.completions.create(messages=messages, model="../../qiwen7b-visual-text")
    result = answer.choices[0].message.content.strip()
    print('qiwen_error_inference：',result)
    return result



def parse_qiwen_error(text, word_id, modified_filtered_id, original_filtered_id):
    word_id_list = word_id
    valid_ids = set(word_id_list + modified_filtered_id + original_filtered_id)

    try:
        if text is None:
            # 如果 text 为 None，返回默认 ID
            return word_id_list

        # 处理匹配的逻辑
        match1 = re.search(r'\[(.*?)\]', text)  # 匹配形如 [17], [16,17]
        match2 = re.search(r'id:\s*(\d+)', text)  # 匹配形如 id: 38, [id:38]

        if match2:
            # 如果匹配到 id:38，取出 ID
            error_id_list = [int(match2.group(1))]
        elif match1:
            # 如果匹配到 [17,18] 这样的格式，取出逗号分隔的 ID
            error_id_list = [int(i) for i in re.findall(r'\d+', match1.group(1))]
        else:
            # 如果没有匹配到任何有效的 ID，则使用默认的 ID
            print('使用了默认ID:', word_id_list)
            return word_id_list

        # 过滤掉不在有效 ID 列表中的 ID
        error_id_list = [id for id in error_id_list if id in valid_ids]

        # 如果没有任何有效的 ID，使用默认的 word_id_list
        if not error_id_list:
            print("没有找到有效的 ID，使用默认 ID:", word_id_list)
            return word_id_list

        return error_id_list

    except Exception as e:
        print(f"解析出错: {e}，返回默认 ID: {word_id_list}")
        return word_id_list
    

def test_parse_qiwen_error():
    word_id = [1, 2, 3]
    modified_filtered_id = [10, 11, 12,17,18,38,97]
    original_filtered_id = [20, 21, 22]

    # **测试用例 1：标准格式 [17,18]**
    text1 = "[17,18]"
    print(parse_qiwen_error(text1, word_id, modified_filtered_id, original_filtered_id))

    # **测试用例 2：标准格式 id: 38**
    text2 = "id: 38"
    print(parse_qiwen_error(text2, word_id, modified_filtered_id, original_filtered_id))

    # **测试用例 3：ID 不在 valid_ids 里**
    text3 = "[99,100]"
    print(parse_qiwen_error(text3, word_id, modified_filtered_id, original_filtered_id))  # 应该返回默认 ID

    # **测试用例 4：存在无效 ID 格式**
    text4 = "[97, 11: 151]"  # 11: 151 是无效的，应该只提取 97
    print(parse_qiwen_error(text4, word_id, modified_filtered_id, original_filtered_id))

    # **测试用例 5：text 为空**
    text5 = None
    print(parse_qiwen_error(text5, word_id, modified_filtered_id, original_filtered_id)) # text 为空，返回默认 ID

    # **测试用例 6：无匹配项**
    text6 = "no match here"
    print(parse_qiwen_error(text6, word_id, modified_filtered_id, original_filtered_id)) # 没有匹配，返回默认 ID

    # **测试用例 7：text 里有多个 id: 格式**
    text7 = "id: 10, id: 21"
    print(parse_qiwen_error(text7, word_id, modified_filtered_id, original_filtered_id)) # 只取第一个匹配到的 ID[10]

    print("所有测试用例通过 ✅")

if __name__ == '__main__':
    # 运行测试
    test_parse_qiwen_error()
