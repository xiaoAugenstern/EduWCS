
import os
import pandas as pd

all_error_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'all_error.xlsx')
df = pd.read_excel(all_error_path, engine='openpyxl')


def edits_find_df(edits):
    for edit in edits:
        modified_result = edit['modified_result']
        error_type = edit['error_type']
        type = error_type['type']
        first_classification = error_type['first_classification']
        second_classification = error_type['second_classification']
        third_classification = error_type['third_classification']
        fourth_classification = error_type['fourth_classification']
        fifth_classification = error_type['fifth_classification']
        if type == 'character':
            matched_row = df[
                (df['类型'] == type) &
                (df['一级分类'] == first_classification) &
                (df['二级分类'] == second_classification)
                ]
        elif type == 'word':
            matched_row = df[
                (df['类型'] == type) &
                (df['一级分类'] == first_classification)
                ]
        elif type == 'grammar':
            if first_classification in ['自定义','未完成句','前后语义不搭','不知所云','语序错误']:
                matched_row = df[
                    (df['类型'] == type) &
                    (df['一级分类'] == first_classification)
                    ]
            else:
                matched_row = df[
                    (df['类型'] == type) &
                    (df['一级分类'] == first_classification) &
                    (df['五级分类'] == fifth_classification)
                    ]
        if not matched_row.empty:
            # If a match is found, retrieve the 'id' of the row
            edit['error_id'] = int(matched_row['id'].values[0])
        else:
            # If no match is found, mark as "no match"
            edit['error_id'] = None
            print('----------------------no match edits',edit)


def evaluation(edits, grammar_errors):
    # 初始化计数器
    find_filtered = 0  # 过滤的真正例：filtered_error_id匹配gold_error_id
    find_predict = 0  # 预测的真正例：predict_error_id匹配gold_error_id
    edits_no_character_num = 0  # 去除 "character" 类型的编辑数量
    false_positives_filtered = 0  # 过滤假正例
    false_positives_predict = 0  # 预测假正例
    false_negatives = 0  # 假负例

    # 遍历所有编辑项
    for edit in edits:
        gold_error_id = edit['error_id']  # 真实的错误 ID
        edit_modified = edit['modified_result']  # 修改后的内容

        # 排除字符类型的编辑
        if edit['error_type']['type'] == 'character':
            continue
        else:
            edits_no_character_num += 1  # 记录非character类型的编辑

        matched = False  # 标记是否匹配到了语法错误

        # 遍历语法错误预测结果
        for grammar_error in grammar_errors:
            # 语法修改结果
            if edit['modified_result'] == grammar_error['modified_result']:
                predict_error_id = grammar_error['predict_error_id']  # 预测的错误 ID，可能有多个
                filtered_error_id = grammar_error['filtered_error_id']  # 过滤后的错误 ID

                logging.info(f'{edit_modified} 的真实 error_id: {gold_error_id}')
                logging.info(f'{edit_modified} 的匹配 error_id: {filtered_error_id}')
                logging.info(f'{edit_modified} 的预测 error_id: {predict_error_id}')

                # 检查过滤匹配
                if gold_error_id in filtered_error_id:
                    find_filtered += 1  # 过滤匹配的真正例
                    matched = True
                    break

                # 检查预测匹配
                if gold_error_id in predict_error_id:
                    find_predict += 1  # 预测匹配的真正例
                    matched = True
                    break

        # 如果没有找到匹配的错误
        if not matched:
            false_positives_filtered += 1  # 如果没有匹配到，增加假正例（过滤）
            false_positives_predict += 1  # 如果没有匹配到，增加假正例（预测）

    # 计算假负例：即语法错误中没有任何编辑匹配的情况
    for grammar_error in grammar_errors:
        matched_error = False
        for edit in edits:
            if edit['modified_result'] == grammar_error['modified_result']:
                matched_error = True
                break
        if not matched_error:
            false_negatives += 1  # 如果语法错误没有匹配到任何编辑，增加假负例

    # 计算精确度、召回率和 F0.5 分数
    precision_filtered = find_filtered / (find_filtered + false_positives_filtered) if (find_filtered + false_positives_filtered) > 0 else 0
    recall_filtered = find_filtered / (find_filtered + false_negatives) if (find_filtered + false_negatives) > 0 else 0
    f05_filtered = (1.5 * precision_filtered * recall_filtered) / (0.5 * precision_filtered + recall_filtered) if (precision_filtered + recall_filtered) > 0 else 0

    precision_predict = find_predict / (find_predict + false_positives_predict) if (find_predict + false_positives_predict) > 0 else 0
    recall_predict = find_predict / (find_predict + false_negatives) if (find_predict + false_negatives) > 0 else 0
    f05_predict = (1.5 * precision_predict * recall_predict) / (0.5 * precision_predict + recall_predict) if (precision_predict + recall_predict) > 0 else 0

    # 返回计算结果
    return {
        'precision_filtered': precision_filtered,
        'recall_filtered': recall_filtered,
        'f05_filtered': f05_filtered,
        'precision_predict': precision_predict,
        'recall_predict': recall_predict,
        'f05_predict': f05_predict,
        'find_filtered': find_filtered,
        'find_predict': find_predict,
        'edits_no_character_num': edits_no_character_num
    }
