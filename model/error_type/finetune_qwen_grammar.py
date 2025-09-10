from utilis import read_json_file,write_to_json
import os
import pandas as pd
from qwen_grammar import qiwen_grammar_prompt

current_dir = os.path.dirname(os.path.abspath(__file__))
all_error_path = os.path.join(current_dir, 'data', 'all_error.xlsx')
print(f"All error file path: {all_error_path}")
df = pd.read_excel(all_error_path, engine='openpyxl')



if __name__ == '__main__':
    viscgec_path = 'data/VisCGEC.json'
    viscgec = read_json_file(viscgec_path)

    id_path = 'data/id.json'
    id = read_json_file(id_path)
    train_id = id['train_id']
    valid_id = id['valid_id']
    test_id = id['test_id']

    grammar_trainset = []   # 微调训练集
    grammar_validset = []
    grammar_testset = []

    for item in viscgec:
        id = item['id']
        source = item['source']
        target = item['target']

        edits = item['edits']
        for edit in edits:
            error_type = edit['error_type']
            type = error_type['type']          # character/grammar/word
            modified_result = edit['modified_result']
            error_id = edit['error_id']
            operation = edit['operation']

            if type == 'character':
                continue

            all_filtered_dict_unique = classify(source,target,modified_result,operation)
            finetune_output = str(error_id)
            finetune_input = source
            finetune_instruction = qiwen_grammar_prompt(source=source,target=target,operation=operation,
                                                        modified_result=modified_result,filtered_dict=all_filtered_dict_unique)
            info = {
                'input': finetune_input,
                'output': finetune_output,
                'instruction': finetune_instruction
            }
            if id in train_id:
                grammar_trainset.append(info)
            elif id in valid_id:
                grammar_validset.append(info)
            elif id in test_id:
                grammar_testset.append(info)

    grammar_trainset_path = '../../LLaMA-Factory/data/Grammar_error/trainset.json'
    write_to_json(grammar_trainset, grammar_trainset_path)

    grammar_testset_path = '../../LLaMA-Factory/data/Grammar_error/testset.json'
    write_to_json(grammar_testset, grammar_testset_path)

    grammar_validset_path = '../../LLaMA-Factory/data/Grammar_error/validset.json'
    write_to_json(grammar_validset, grammar_validset_path)