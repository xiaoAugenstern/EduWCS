from pypinyin import pinyin, Style
from opencc import OpenCC
from hanzi_chaizi import HanziChaizi
import difflib
import re

# 初始化繁简转换工具
opencc = OpenCC('s2t')  # 简体到繁体
opencc_reverse = OpenCC('t2s')  # 繁体到简体



def find_diff_part(str1, str2):
    # 如果str1和str2去掉标点符号
    punctuation_set = set('：；，。？！、~!@#$%^&*()_-+=[]{}|\\:;"\'<>,.?/')
    str1 = ''.join([c for c in str1 if c not in punctuation_set]).strip()
    str2 = ''.join([c for c in str2 if c not in punctuation_set]).strip()
    d = difflib.SequenceMatcher(None, str1, str2)
    diff_parts = []

    for tag, i1, i2, j1, j2 in d.get_opcodes():
        if tag == 'replace':
            for a, b in zip(str1[i1:i2], str2[j1:j2]):
                diff_parts.append((a, b))
        elif tag == 'delete':
            for a in str1[i1:i2]:
                diff_parts.append((a, ''))
        elif tag == 'insert':
            for b in str2[j1:j2]:
                diff_parts.append(('', b))
        elif tag == 'equal':
            continue
    return diff_parts

def split_pinyin(pinyin_with_tone):
    """
    将拼音拆分为声母和韵母（带声调或不带声调）
    """
    vowels = "aeiouü"
    for i, char in enumerate(pinyin_with_tone):
        if char in vowels:  # 第一个元音出现的位置
            return pinyin_with_tone[:i], pinyin_with_tone[i:]
    return pinyin_with_tone, ""  # 如果未找到元音，默认全为声母

def is_traditional_variant(char1, char2):
    """
    判断两个字符是否为繁体/异体关系
    """
    return opencc.convert(char1) == char2 or opencc_reverse.convert(char1) == char2

def is_phonetic_error(char1, char2):
    """
    判断两个字符是否为音近混用或音同混用
    """
    # 获取带声调和不带声调的拼音
    pinyin1_tone = pinyin(char1, style=Style.TONE3)  # 带声调
    pinyin2_tone = pinyin(char2, style=Style.TONE3)
    pinyin1_normal = pinyin(char1, style=Style.NORMAL)  # 不带声调
    pinyin2_normal = pinyin(char2, style=Style.NORMAL)

    # 判断音同混用（完全一致，包括声调）
    if pinyin1_tone == pinyin2_tone:
        return "音同混用"

    # 判断音近混用
    for py1, py2 in zip(pinyin1_normal, pinyin2_normal):
        # 拆分为声母和韵母
        shengmu1, yunmu1 = split_pinyin(py1[0])
        shengmu2, yunmu2 = split_pinyin(py2[0])
        # print('shengmu1',shengmu1,'yunmu1',yunmu1)
        # print('shengmu2',shengmu2,'yunmu2',yunmu2)
        if shengmu1 == shengmu2:  # 声母相同
            return "音近混用"      # 韵母不同/韵母相同，但是声调不同
    # 无音同或音近关系
    return None


def is_component_confusion(source, target):
    print('---is_component_confusion---')
    print('source:', source,'target:', target)
    if not target or not source:
        return False
    hc = HanziChaizi()
    # 拆分目标字和源字
    target_parts = hc.query(target)
    source_parts = hc.query(source)
    if target_parts is None or source_parts is None:
        return False
    else:
        # 打印拆分的部件
        print(f"Target: {target}, Components: {target_parts}")
        print(f"Source: {source}, Components: {source_parts}")
        if source in target_parts or target in source_parts:
            return True
        # 计算部件的交集
        common_parts = set(target_parts) & set(source_parts)
        # 如果有交集，认为可能是部件混淆
        if common_parts:
            return True
    return False

def is_valid_hanzi(char):
    return bool(re.fullmatch(r'[\u4e00-\u9fa5]', char))  # 只匹配单个简体/繁体汉字

def three_error(source, target):
    """
    判断 source 到 target 的具体错误类型
    """
    print('---is_three_error---')
    if not is_valid_hanzi(source) or not is_valid_hanzi(target):
        print(f"source:{source},target:{target}，跳过部件混淆等检测")
        return None, None, False

    variant_error = is_traditional_variant(source, target)
    if variant_error:
        print("繁体/异体")
    else:
        print("没有繁体/异体")

    # 音同混用,音近混用,None
    phonetic_error = is_phonetic_error(source, target)
    if phonetic_error:
        print(phonetic_error)
    else:
        print("无音同或音近关系")

    component_error = is_component_confusion(source, target)
    if component_error:
        print("部件混淆")
    else:
        print("没有部件混淆")
    return variant_error, phonetic_error, component_error


if __name__ == '__main__':
    str1 = "精身"
    str2 = "精神"
    diff = find_diff_part(str1, str2)  #  [('身', '神')]
    print(f"不同部分: {diff}")
    for source, target in diff:
        three_error(source, target)

    str1 = "老若男女"
    str2 = "老弱男女"
    diff = find_diff_part(str1, str2)
    print(f"不同部分: {diff}")

    str1 = '扔圾'
    str2 = '扔垃圾'
    diff = find_diff_part(str1, str2)

    # 示例数据
    examples = [
        ("精神","精身"),
        ("苹","平"),
        ("士", "术"),  # 韵母不同但声母相同，音近混用
        ("標", "标"),  # 繁体/异体
        ("管", "关"),  # 音近混用
        ("管", "馆"),  # 音同混用
        ("海", "每"),  # 结构错误
        ("渡", "度"),  # 音同混用 + 结构错误
    ]

    # 判断每对错误类型
    for target, source in examples:
        print(f"Target: {target}, Source: {source}:")
        three_error(target, source)