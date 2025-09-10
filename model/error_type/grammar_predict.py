import pandas as pd
import os
from log.logger import guohan_correct_error_logger
from model.error_type.utilis import df_to_dict,find_sentence,get_m2,parse_m2_file2
from model.error_type.regex import filter_invalid_matches
from model.error_type.qwen_grammar import qiwen_grammar_prompt,qiwen_error_inference,parse_qiwen_error
from model.error_type.pinyin import three_error,find_diff_part
import re

# 所有的错误类型
all_error_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'all_error.xlsx')
print(f"All error file path: {all_error_path}")
df = pd.read_excel(all_error_path, engine='openpyxl')
error_dict_by_id = {row['id']: row for _, row in df.iterrows()}

class CorrectionError:
    def __init__(self, source, target, modified_result, operation_type, original_result=None):
        self.source = source
        self.target = target
        self.modified_result = modified_result
        self.operation_type = operation_type[0]
        self.original_result = original_result
        self.modified_filtered_dict = []   # modified_result候选列表
        self.modified_filtered_id = []
        self.original_filtered_dict = []   # original_result候选列表
        self.original_filtered_id = []
        self.word_error_dict = []          # word-level候选列表
        self.word_error_id = []
        self.character_error_dict = []     # character-level候选列表
        self.character_error_id = []
        self.all_filtered_dict = {}
        self.all_filtered_dict_unique = [] # 去重后的列表
        self.filtered_error_id = []        # 所有候选语法点的id
        self.predict_error_id = []
        self.fk_error_id = []

    def character_error_classify(self):
        variant_error, phonetic_error, component_error = None, None, None
        if not self.original_result or not self.modified_result:
            return None
        if len(self.original_result) != len(self.modified_result):
            return None
        for schar, tchar in find_diff_part(self.original_result, self.modified_result):
            if schar == '' or tchar == '':
                continue
            variant_error, phonetic_error, component_error = three_error(schar, tchar)
        if variant_error:
            self.character_error_dict.append(df_to_dict(df[df['id'] == 4]))  # 繁体/异体
        if phonetic_error == '音同混用':
            self.character_error_dict.append(df_to_dict(df[df['id'] == 1]))
        elif phonetic_error == '音近混用':
            self.character_error_dict.append(df_to_dict(df[df['id'] == 2]))
        if component_error:
            self.character_error_dict.append(df_to_dict(df[df['id'] == 7]))  # 部件混淆
        self.character_error_id = [dict['id'] for dict in self.character_error_dict]

        if self.character_error_id:
            for error_id in self.character_error_id:
                fk_error_id = df[df['id'] == error_id]['fk_error_id'].values.item()
                self.fk_error_id.append(fk_error_id)
            return self.fk_error_id
        else:
            return None

    def classify(self):
        '''
            根据 modified_result,original_result,word-level进行匹配
        '''

        def match_category(field, pattern_text, context_text):
            if not pattern_text:
                return [], []
            safe_pattern = re.escape(pattern_text)
            matched = df[df[field].fillna('').str.contains(safe_pattern)]
            filtered = filter_invalid_matches(matched, context_text)
            error_dicts = [row.to_dict() for row in filtered]
            error_ids = [d['id'] for d in error_dicts]
            return error_dicts, error_ids

        # 1. 五级分类匹配
        self.modified_filtered_dict, self.modified_filtered_id = match_category('五级分类', self.modified_result,self.target)
        self.original_filtered_dict, self.original_filtered_id = match_category('五级分类', self.original_result,self.source)

        # 2. word-level 匹配
        op = self.operation_type
        if op == 'W':
            self.word_error_dict.append(df_to_dict(df[df['一级分类'] == '语序错误']))
        elif op in ['M', 'add']:
            self.word_error_dict.append(df_to_dict(df[(df['类型'] == 'word') & (df['一级分类'] == '漏用')]))
        elif op in ['R', 'delete']:
            self.word_error_dict.append(df_to_dict(df[(df['类型'] == 'word') & (df['一级分类'] == '多用')]))
        elif op in ['S', 'edit']:
            for eid in [20, 21]:
                row = error_dict_by_id.get(eid)
                if row is None or row.empty:  # 安全判断是否为空
                    continue
                if (self.original_result and re.search(row['pattern'], self.original_result)) or \
                        (self.modified_result and re.search(row['pattern'], self.modified_result)):
                    self.word_error_dict.append(df_to_dict(pd.DataFrame([row])))
            self.word_error_dict.append(df_to_dict(pd.DataFrame([error_dict_by_id[17]])))  # 错词误用
        self.word_error_id = [d['id'] for d in self.word_error_dict]

        # 3. 去重 & 合并
        all_filtered_dict = self.modified_filtered_dict + self.original_filtered_dict + self.word_error_dict
        self.all_filtered_dict = {
            'modified_filtered_dict': self.modified_filtered_dict,
            'original_filtered_dict': self.original_filtered_dict,
            'word_error_dict': self.word_error_dict
        }

        for item in all_filtered_dict:
            if item['id'] not in self.filtered_error_id:
                self.filtered_error_id.append(item['id'])    # 去重的error id
                self.all_filtered_dict_unique.append(item)   # 去重的error id对应的内容
        print('modified_filtered_id:',self.modified_filtered_id,'original_filtered_id:',self.original_filtered_id,'word_error_dict:',self.word_error_id)
        print('filtered_error_id:',self.filtered_error_id) # 这里找的都是表id，最后要表id对应表fk_error_id
        return self.filtered_error_id


    def qwen_grammar(self):
        # 构造prompt
        prompt = qiwen_grammar_prompt(
            source=self.source,
            target=self.target,
            operation=self.operation_type,
            modified_result=self.modified_result,
            filtered_dict=self.all_filtered_dict_unique,
            original_result=self.original_result
        )
        # 大模型从候选中推理筛选
        result = qiwen_error_inference(prompt)
        # 解析大模型的结果，如果大模型生成幻觉，则返回word_error_id
        self.predict_error_id = parse_qiwen_error(result, self.word_error_id,
                                                  self.modified_filtered_id,
                                                  self.original_filtered_id)  # [17],[17,18]
        guohan_correct_error_logger.info(f'parse_qiwen_error:{self.predict_error_id}')

        # predict_error_id转换为fk_error_id
        for error_id in self.predict_error_id:
            row = df[df['id'] == error_id]
            if row.empty:
                print(f"⚠️没有找到 error_id={error_id} 对应的记录")
                continue
            fk_error_id = row['fk_error_id'].values.item()
            print(f'error_id:【{error_id}】 映射为 fk_error_id:【{fk_error_id}】， 匹配内容: {row.iloc[0].to_dict()}"')
            self.fk_error_id.append(fk_error_id)
        return self.fk_error_id


    def get_fk_error_id(self):
        punctuation_set = set('：；，。？！、~!@#$%^&*()_-+=[]{}|\\:;"\'<>,.?/')
        if self.modified_result in punctuation_set:
            # 如果是标点符号，直接 fk_error_id = None
            guohan_correct_error_logger.info(f"{self.modified_result} 是标点符号，predict_error_id 被设置为 None")
            return None
        else:
            character_fk_error_id = self.character_error_classify() # 如果修改的文本不是标点符号，进行匹配 音同混用/音近混用/部件混淆/繁体/异体
            if character_fk_error_id:
                return character_fk_error_id
            else:
                filtered_error_id = self.classify() # 根据 modified_result 和 original_result去匹配 error id
                if len(filtered_error_id) == 1:
                    print('no qwen inference')
                    fk_error_id = df[df['id'] == filtered_error_id[0]]['fk_error_id'].values.item()
                    return [fk_error_id]
                else:
                    print('qwen inference')
                    qwen_fk_error_id = self.qwen_grammar()
                    return qwen_fk_error_id


def guohan_error_predict(corrections,index_source_corrected):
    sent_starts = [item['start'] for item in index_source_corrected]  # 每个分句的第一个字的起始位置
    print('sent_starts:',sent_starts)
    for index,correction in enumerate(corrections):
        correction_start = correction['start']
        correction_end = correction['end']

        sent_number = find_sentence(sent_starts, correction_start)
        source = index_source_corrected[sent_number]['sent']
        predict = index_source_corrected[sent_number]['qwen_sent']

        operation_type = correction['operation_type']
        modified_result = correction['modified_result']
        original_result = correction['original_result']

        correction_error = CorrectionError(
            source=source,
            target=predict,
            modified_result=modified_result,
            operation_type=operation_type,
            original_result=original_result
        )
        correction['fk_error_id'] = correction_error.get_fk_error_id()
        guohan_correct_error_logger.info(f'======= correction index {index}:')
        guohan_correct_error_logger.info(f"操作是{operation_type}、original_result是【{original_result}】、modified_result是【{modified_result}】")
        guohan_correct_error_logger.info(f'source:{source}')
        guohan_correct_error_logger.info(f'predict:{predict}')
        guohan_correct_error_logger.info(f"'{modified_result}' 的fk_error_id 为{correction['fk_error_id']}")

    print('corrections:',corrections)
    return corrections





if __name__ == '__main__':
    ''' 测试 '''

    source = "而且跑步带来给我挺多好处，对身体有益，对精身有益。"
    target = "而且跑步给我带来挺多好处，对身体有益，对精神有益。"
    edits = [
        {
            "operation": "edit",
            "relative_start_index": 22,
            "relative_end_index": 24,
            "modified_result": "神",
            "error_type": {
                "type": "character",
                "detail": "",
                "fk_mark_id": 8362,
                "fk_error_id": 2,
                "first_classification": "整字",
                "second_classification": "音近混用"
            },
            "error_id": 2
        },
        {
            "operation": "edit",
            "relative_start_index": 2,
            "relative_end_index": 12,
            "modified_result": "跑步给我带来挺多好处",
            "error_id": 28
        }
    ]
    # source = "第三，不分老若男女。"
    # target = "第三，不分老弱男女。"
    #
    # source =  "有利于眼睛健康，可以降低近视的机率，"
    # target = "有利于眼睛健康，可以降低近视的几率，"

    source = '这种人认为他们的行动对环境没有影响，所以☰们地自然的随便浪费资源。'
    target = '这种人认为他们的行动对环境没有影响，所以他们地自然地随便浪费资源。'

    # m2格式(granularity=word/char)
    hyp_m2_file = get_m2(source, target,granularity='word')
    # 获得句子的所有修改记录
    corrections = parse_m2_file2(hyp_m2_file)
    for index,correction in enumerate(corrections):
        print('----- Process correction index--------',index)
        print('correction:',correction)
        operation_type = correction['operation_type']
        modified_result = correction['modified_result']
        original_result = correction['original_result']
        correction_error = CorrectionError(
            source=source,
            target=target,
            modified_result=modified_result,
            operation_type=operation_type,
            original_result=original_result
        )
        correction['fk_error_id'] = correction_error.get_fk_error_id()
        print('////// correction fk_error_id ',correction['fk_error_id'],' ////////// \n')






