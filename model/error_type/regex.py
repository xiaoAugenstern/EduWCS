import re

def generate_MN_XY(s1,s2,template,regex_pattern):
    positions_ellipsis = [i for i in range(len(template)) if template.startswith('……', i)]
    positions_s1 = [i for i, c in enumerate(template) if c == s1]
    positions_s2 = [i for i, c in enumerate(template) if c == s2]
    if s1 == 'M' and s2 == 'N':
        rule = '([\u4e00-\u9fa5]+)'
    elif s1 == 'X' and s2 == 'Y':
        rule = '([\u4e00-\u9fa5])'
    else:
        rule = '([\u4e00-\u9fa5]+)'

    s1_count = template.count(s1)
    s2_count = template.count(s2)

    if s1_count >= 2:
        if s2 in template and '……' in template:
            if s2_count == 1:
                regex_pattern = regex_pattern.replace(s2, rule)
            elif s2_count == 2:
                if positions_s1[1] < positions_s2[0] and positions_ellipsis[0] < positions_s2[0]:
                    # 'X也X不……，Y也Y不……'
                    regex_pattern = regex_pattern.replace(s1, rule, 1)
                    regex_pattern = regex_pattern.replace(s1, r"\1")
                    regex_pattern = regex_pattern.replace(s2, rule, 1)
                    regex_pattern = regex_pattern.replace(s2, r"\3")

        elif s2 in template and '……' not in template:
            if s2_count == 1:
                regex_pattern = regex_pattern.replace(s2, rule)
            elif s2_count == 2:
                if positions_s1[1] < positions_s2[0]:  # XXYY
                    regex_pattern = regex_pattern.replace(s1, rule, 1)
                    regex_pattern = regex_pattern.replace(s1, r"\1")
                    regex_pattern = regex_pattern.replace(s2, rule, 1)
                    regex_pattern = regex_pattern.replace(s2, r"\2")
                elif positions_s1[1] > positions_s2[1]:  # XYYX
                    regex_pattern = regex_pattern.replace(s1, rule, 1)
                    regex_pattern = regex_pattern.replace(s2, rule, 1)
                    regex_pattern = regex_pattern.replace(s2, r"\2")
                    regex_pattern = regex_pattern.replace(s1, r"\1")
                elif positions_s1[1] > positions_s2[0] and positions_s1[1] < positions_s2[1]:  # XYXY
                    regex_pattern = regex_pattern.replace(s1, rule, 1)
                    regex_pattern = regex_pattern.replace(s2, rule, 1)
                    regex_pattern = regex_pattern.replace(s1, r"\1")
                    regex_pattern = regex_pattern.replace(s2, r"\2")
        else:  # 没有Y和……
            regex_pattern = regex_pattern.replace(s1, rule, 1)
            regex_pattern = regex_pattern.replace(s1, r"\1")
    elif s1_count == 1:
        regex_pattern = regex_pattern.replace(s1, rule)
        regex_pattern = regex_pattern.replace(s2, rule)
    return regex_pattern


def generate_regex(template):
    """
    根据输入模板自动生成正则表达式
    :param template: 模式字符串
    :return: 对应的正则表达式
    """
    escaped_template = re.escape(template)      # 转义固定字符，防止特殊字符干扰
    regex_pattern = escaped_template

    if "……" in template:
        # （1） "……"，"首先……，然后……"
        regex_pattern = escaped_template.replace(re.escape("……"), "(.*?)")
    if 'M' in template:
        regex_pattern = generate_MN_XY('M','N',template,regex_pattern)
    if 'X' in template:
        regex_pattern = generate_MN_XY('X','Y',template,regex_pattern)
    return regex_pattern

def match_pattern(sentence, pattern):
    """
    辅助函数：判断句子是否匹配单个模式
    :param sentence: 待检查的句子
    :param pattern: 单个模式字符串
    :return: 是否匹配规则 (True/False)
    """
    regex = generate_regex(pattern)
    match = re.search(regex, sentence)  # 执行匹配
    if match:
        # print(f"{regex} 匹配成功: {sentence}")
        return True
    else:
        # print(f"{regex} 未匹配: {sentence}")
        return False

def check_sentence_against_rule(sentence,pattern):
    pos = False
    pattern = str(pattern)
    if pattern != 'nan':
        # 如果 pattern 包含多个子模式，用 "；" 分隔
        if '；' in pattern:
            sub_patterns = pattern.split('；')
            for sub_pattern in sub_patterns:
                if match_pattern(sentence, sub_pattern):
                    pos = True
                    break
        else:
            # 单一模式匹配
            if match_pattern(sentence, pattern):
                pos = True
    else:
        # 如果 pattern 为 "nan"，认为匹配成功
        pos = True
    return pos


def filter_invalid_matches(matched_result, sentence):
    valid_results = []
    # 对匹配到的五级分类进行进一步过滤
    for _, row in matched_result.iterrows():
        fifth = row['五级分类']
        pattern = row['pattern']
        if check_sentence_against_rule(sentence,pattern):
            valid_results.append(row)
    return valid_results