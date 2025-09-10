import re
import json
import requests
import time
import concurrent.futures
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

client = OpenAI(api_key="0", base_url="http://0.0.0.0:8000/v1")

prompt_template = (
    """你是一位经验丰富的中文老师，专门纠正学生作文中的语法错误，基于最小编辑原则。请根据以下要求进行修正：
    1. 仅修正句子中的语法和用词错误。
    2. 如果句子没有错误，请不要进行任何修改，保持原句不变。
    3. 不要改变句子的结构或原意。
    4. 请直接返回纠正后的文本内容，不要添加任何额外的提示信息。

    例如：
    输入：所以这是要触定计划再走。
    输出：所以这是要确定计划再走。

    输入：未来的科技生活才能真正成为人们美好生活的一部分。
    输出：未来的科技生活才能真正成为人们美好生活的一部分。
    """
)


def qwen_predict(source):
    url = "http://localhost:5000/correct"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "passage": source
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    # 解析返回的 JSON 数据
    result = response.json()
    predict = result.get('corrected_passage', '')
    index_source_corrected = result.get('index_source_corrected', [])
    source = replace_punctuation(source)
    print('source:',source)
    print('predict:',predict)
    return source,predict,index_source_corrected

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

def call_qwen_api(sentence: str, prompt_template: str, client, model="qiwen7b-visual-text"):
    """
    调用 Qwen 模型进行纠错，返回纠正后的结果
    """
    if not sentence.strip():
        return sentence

    prompt = prompt_template + f"\n\n输入：{sentence}\n输出："
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": sentence}
    ]
    try:
        answer = client.chat.completions.create(messages=messages, model=model)
        result = answer.choices[0].message.content.strip()
        # 去掉可能的固定前缀
        result = re.sub(r'^纠正后的文本内容[:：]?', '', result).strip()
        print('sentence:',sentence)
        print('result:',result)
        if sentence == result:
            print('没有修改')
        else:
            print('有修改')
        return result
    except Exception as e:
        print(f"[Error] 处理句子失败: {e}")
        return sentence


# --------------- 1. 串行版本 ------------------
def split_predict(passage,prompt_template,client):
    sentences = re.split(r'(?<=[。！？ ?!.])', passage)
    sentences = [replace_punctuation(sentence) for sentence in sentences if sentence.strip()]
    sentences_corrected = []
    print('----------------------------------')
    for i, sentence in enumerate(sentences):
        print(f'分句{i}:', sentence)
    print('------------------------------')
    corrected_sentences = []    # 纠正后的正确句子列表
    start = 0
    for index, sentence in enumerate(sentences):
        result = call_qwen_api(sentence, prompt_template, client)
        sentences_corrected.append({
            'index': index,
            'start': start,
            'sent': sentence,
            'qwen_sent': result
        })
        start += len(sentence)
        corrected_sentences.append(result)

    corrected_passage = ''.join(corrected_sentences).replace('\n', '')  # 拼接起来
    corrected_passage_zh = replace_punctuation(corrected_passage) # 全角半角字符替换
    print('串行:', corrected_passage_zh)
    return sentences_corrected,corrected_passage_zh


# --------------- 2. 并行版本 ------------------
import asyncio
async def async_process_single_sentence(index, sentence, start_pos, prompt_template, client):
    result = await asyncio.to_thread(call_qwen_api, sentence, prompt_template, client)
    return {
        'index': index,
        'start': start_pos,
        'sent': sentence,
        'qwen_sent': result
    }

async def split_predict_parallel_async(passage, prompt_template, client):
    sentences = re.split(r'(?<=[。！？?!])', passage)
    sentences = [replace_punctuation(s) for s in sentences if s.strip()]

    tasks, start = [], 0
    for index, sentence in enumerate(sentences):
        tasks.append(async_process_single_sentence(index, sentence, start, prompt_template, client))
        start += len(sentence)

    sentences_corrected = await asyncio.gather(*tasks)
    sentences_corrected.sort(key=lambda x: x['index'])  # 保持顺序

    corrected_passage = ''.join([item['qwen_sent'] for item in sentences_corrected]).replace('\n', '')
    corrected_passage_zh = replace_punctuation(corrected_passage)
    print('并行:', corrected_passage_zh)
    return sentences_corrected, corrected_passage_zh


# def process_single_sentence(args):
#     index, sentence, start_pos, prompt_template, client = args
#     result = call_qwen_api(sentence, prompt_template, client)
#     return {
#         'index': index,
#         'start': start_pos,
#         'sent': sentence,
#         'qwen_sent': result
#     }
#

def split_predict_parallel(passage, prompt_template, client, max_workers=5):
    """
    对输入文本进行分句，并行调用大模型进行纠错。

    Args:
        passage (str): 待纠错的文本
        prompt_template (str): 提示词模板，用于构建 prompt
        client (OpenAI): OpenAI API client
        max_workers (int): 并行线程数，默认 5

    Returns:
        sentences_corrected (list[dict]): 每句的纠错结果（包含 index, start, 原句, 修改后句子）
        corrected_passage_zh (str): 拼接后的最终纠正文本（带全角标点）
    """
    # 使用正则分句，匹配句号、问号、感叹号等作为分割点
    sentences = re.split(r'(?<=[。！？?!])', passage)
    # 过滤空字符串，并将英文标点替换为中文全角标点
    sentences = [replace_punctuation(s) for s in sentences if s.strip()]

    # 构建任务列表，每个任务包含 (句子索引, 句子文本, 起始位置, prompt 模板, client)
    tasks, start = [], 0
    for index, sentence in enumerate(sentences):
        tasks.append((index, sentence, start, prompt_template, client))
        start += len(sentence)  # 记录每个句子的起始位置（用于后续标注）

    # 存放纠错结果的容器，按句子顺序存储
    sentences_corrected = [None] * len(sentences)

    # 使用线程池并行处理句子
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务，并记录 future -> 句子索引 的映射
        future_to_index = {executor.submit(process_single_sentence, task): task[0] for task in tasks}
        # 按任务完成的顺序收集结果（无序完成，但有索引可以恢复顺序）
        for future in concurrent.futures.as_completed(future_to_index):
            result = future.result()
            sentences_corrected[result['index']] = result  # 按 index 放回正确位置

    # 拼接所有纠正后的句子，去掉换行，
    corrected_passage = ''.join([item['qwen_sent'] for item in sentences_corrected]).replace('\n', '')
    corrected_passage_zh = replace_punctuation(corrected_passage)
    print('并行:', corrected_passage_zh)
    return sentences_corrected, corrected_passage_zh


def no_split_predict(passage, prompt_template, client):
    result = call_qwen_api(passage, prompt_template, client)
    return result


def test_performance():
    passage = '''
    姓名文元榮韩国学号12212720407愉快旅行我比较赖不怎么喜欢外出,因此我旅游的记忆很少。但是我也拥有着一个难忘的旅行经历。那年我还小,大既七岁,八岁没有多少记忆,但有那么几天的记忆是无法忘记的。当时。因为工作需要我的父亲要去中国出差,而且留给我们的时间不多,只有那么几天。因此我们的父亲带着我与妹妹游了我们的家乡济洲道一圈。那时的我还小,并不记得多少记忆。但是游时的我的感受却无法忘记。那种开心又悲的感情伤是七,八岁的我可是没有感受过的。虽然没有多少对这时旅游时的记忆,但这时的旅游就是我最愉快,最难忘的旅行。
    '''

    # print("===== 串行分句纠错 =====")
    # t1 = time.time()
    # _, corrected_serial = split_predict(passage, prompt_template, client)
    # t2 = time.time()
    # print("耗时: {:.2f} 秒".format(t2 - t1))
    # print("结果:", corrected_serial)

    print("\n===== 并行分句纠错 =====")
    t3 = time.time()
    _, corrected_parallel = split_predict_parallel(passage, prompt_template, client, max_workers=5)
    t4 = time.time()
    print("耗时: {:.2f} 秒".format(t4 - t3))
    print("结果:", corrected_parallel)

    # print("\n===== 整段直接纠错 =====")
    # t5 = time.time()
    # corrected_whole = no_split_predict(passage, prompt_template, client)
    # t6 = time.time()
    # print("耗时: {:.2f} 秒".format(t6 - t5))
    # print("结果:", corrected_whole)


if __name__ == '__main__':
    test_performance()
