import spacy
from spacy import displacy
# from grammar_predict import get_m2
# nlp = spacy.load("zh_core_web_sm")
#
# source = "除了这社团，我属于学校外面的棒球队。"
# target = "除了这社团，我还属于学校外面的棒球队。"
# modified_result = "还"
#
# doc_target = nlp(target)
# print(doc_target.text)
#
# for token in doc_target:
#     print(f"Token: {token.text}, POS: {token.pos_}, Dependency: {token.dep_},head:{token.head.text},head tag:{token.head.tag_}")
    
# input_file, output_file, hyp_para_file, hyp_m2_file = get_m2(source, target,granularity='char')


import spacy

# 加载中文语言模型
nlp = spacy.load("zh_core_web_sm")

# 示例句子
source = "除了这社团，我属于学校外面的棒球队。"
target = "除了这社团，我还属于学校外面的棒球队。"
modified_result = "还"  # 要查找的词

# 使用 spaCy 处理目标句子
doc_target = nlp(target)

# 打印目标句子文本
print(f"Processed text: {doc_target.text}")

# 遍历所有词，找到 modified_result 的位置
for token in doc_target:
    if token.text == modified_result:
        print(f"Found token: {token.text}")
        print(f"POS: {token.pos_}, Dependency: {token.dep_}, Head: {token.head.text}, Head tag: {token.head.tag_}")

        # 找到该 token 的所有父节点
        parents = []
        current_token = token
        while current_token.head != current_token:  # 当当前词的父节点不是它自己时
            parents.append(current_token.head.text)
            current_token = current_token.head

        # 打印所有父节点
        print("All parents of the token:", " -> ".join(parents))
