import argparse
from typing import List, Dict

def parse_m2_file(m2_path: str) -> List[Dict]:
    """解析 M2 文件，返回结构化数据"""
    blocks = []
    current_block = None
    
    with open(m2_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # 解析 S 行
            if line.startswith('S '):
                if current_block:
                    blocks.append(current_block)
                current_block = {
                    'S': line[2:].split(),
                    'T0': None,
                    'edits': []
                }
            
            # 解析 T0 行
            elif line.startswith(('T0-A0 ', 'T0 ')):
                parts = line.split(' ', 1)
                current_block['T0'] = parts[1].replace(' ', '')
            
            # 解析 A 行
            elif line.startswith('A '):
                if '|||noop|||' in line:
                    continue
                
                parts = line.split('|||')
                if len(parts) < 3:
                    continue
                
                pos_part = parts[0].split()
                if len(pos_part) != 3 or not pos_part[1].isdigit():
                    continue
                
                start = int(pos_part[1]) - 1
                end = int(pos_part[2]) - 1
                
                replacement = parts[2].strip().split()
                if not replacement:
                    continue
                
                current_block['edits'].append((start, end, replacement))
        
        if current_block:
            blocks.append(current_block)
    
    return blocks

def generate_variants(block: Dict) -> List[str]:
    """生成单个编辑排除的变体"""
    s_words = block['S']
    edits = block['edits']
    
    variants = []
    for i in range(len(edits)):
        temp_words = s_words.copy()
        applied_edits = sorted(
            [edits[j] for j in range(len(edits)) if j != i],
            key=lambda x: x[0], reverse=True
        )
        
        for start, end, repl in applied_edits:
            if start < 0 or end > len(temp_words):
                continue
            if repl != ['-NONE-']:
                temp_words = temp_words[:start] + repl + temp_words[end:]
            else:
                temp_words = temp_words[:start] + temp_words[end:]
        
        variant = ''.join(temp_words)
        variants.append(f'A{i+1} {variant}')
    
    return variants

def write_output(blocks: List[Dict], output_path: str) -> None:
    """将结果写入输出文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for block in blocks:
            s_sentence = ''.join(block['S'])
            f.write(f"S {s_sentence}\nT0 {block['T0']}\n")
            
            variants = generate_variants(block)
            for var in variants:
                f.write(f"{var}\n")
            f.write("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='M2格式文件转换工具：生成排除单个编辑的变体句子',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--input', type=str, required=True,
                      help='输入M2文件路径')
    parser.add_argument('--output', type=str, required=True,
                      help='输出文件路径')
    args = parser.parse_args()

    # 解析和处理数据
    blocks = parse_m2_file(args.input)
    valid_blocks = [b for b in blocks if b['edits']]
    
    # 生成输出文件
    write_output(valid_blocks, args.output)
    
    print(f"成功处理 {len(valid_blocks)} 个有效文本块")
    print(f"结果已保存至: {args.output}")