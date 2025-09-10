import spacy
import sys
from spacy.matcher import DependencyMatcher


# Usage: python batch_modify_m2.py input.m2
# 直接打印匹配 ADP <-case NOUN <-nmod:prep VERB 结构的 A 行

if len(sys.argv) != 2:
    print("Usage: python batch_modify_m2.py input.m2")
    sys.exit(1)

m2_path = sys.argv[1]

# 加载 spaCy 中文模型
nlp = spacy.load("zh_core_web_sm")

# 定义依存模式：ADP <-case NOUN <-nmod:prep VERB
pattern = [
    {"RIGHT_ID": "verb", "RIGHT_ATTRS": {"POS": "VERB"}},
    {"LEFT_ID": "verb", "REL_OP": ">", "RIGHT_ID": "noun", "RIGHT_ATTRS": {"DEP": "nmod"}},
    {"LEFT_ID": "noun", "REL_OP": ">", "RIGHT_ID": "adp", "RIGHT_ATTRS": {"DEP": "case", "POS": "ADP"}},
]
matcher = DependencyMatcher(nlp.vocab)
matcher.add("ADP_CASE_NMOD_PREP_VERB", [pattern])

with open(m2_path, 'r', encoding='utf-8') as f:
    source = None
    annotations = []
    for line in f:
        line = line.rstrip("\n")
        if line.startswith('S '):
            # 处理上一句
            if source is not None:
                doc = nlp(source)
                matches = matcher(doc)
                if matches:
                    # 打印所有匹配的 A 行
                    for ann in annotations:
                        # 只要在该句中存在结构匹配，就输出所有 A 行
                        print(ann['raw'])
            # 新句初始化
            source = line[2:]
            annotations = []
        elif line.startswith('A '):
            parts = line.split('|||')
            spans = parts[0].split()
            start = int(spans[1])
            end = int(spans[2])
            annotations.append({'raw': line, 'start': start, 'end': end})
        # 空行跳过
    # 处理最后一句
    if source is not None:
        doc = nlp(source)
        matches = matcher(doc)
        if matches:
            for ann in annotations:
                print(ann['raw'])
    print(1)