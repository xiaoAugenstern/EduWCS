import torch
import argparse
from transformers import AutoModelForCausalLM, AutoTokenizer

def calculate_ppl(sentence, model, tokenizer):
    inputs = tokenizer(sentence, return_tensors="pt")
    input_ids = inputs["input_ids"]
    with torch.no_grad():
        outputs = model(input_ids, labels=input_ids)
    loss = outputs.loss
    ppl = torch.exp(loss).item()
    return ppl

def parse_formatted_file(input_file):
    """
    解析格式化文件为块结构
    """
    blocks = []
    current_block = {"S": None, "T0": None, "A": []}
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("S "):
                if current_block["S"] is not None:  # 遇到新块，保存当前块
                    blocks.append(current_block)
                    current_block = {"S": None, "T0": None, "A": []}
                current_block["S"] = line[2:]  # 去除前缀 "S "
            elif line.startswith("T0 "):
                current_block["T0"] = line[3:]  # 去除前缀 "T0 "
            elif line.startswith("A"):
                parts = line.split(" ", 1)
                current_block["A"].append((parts[0], parts[1]))  # (A编号, 句子)
        if current_block["S"] is not None:  # 添加最后一个块
            blocks.append(current_block)
    return blocks

def process_blocks(blocks, model, tokenizer, output_file):
    """
    处理块并计算 PPL 及差值，并按 Δ 值降序排列 A 变体
    """
    with open(output_file, "w", encoding="utf-8") as f_out:
        for block in blocks:
            s_sentence = block["S"]
            t0_sentence = block["T0"]
            a_sentences = block["A"]

            # 计算 S 和 T0 的 PPL
            s_ppl = calculate_ppl(s_sentence, model, tokenizer)
            t0_ppl = calculate_ppl(t0_sentence, model, tokenizer)

            # 写入 S 和 T0 结果
            f_out.write(f"S Sentence: {s_sentence}\nS PPL: {s_ppl:.2f}\n\n")
            f_out.write(f"T0 Sentence: {t0_sentence}\nT0 PPL: {t0_ppl:.2f}\n\n")

            # 收集所有 A 变体的 PPL 和 Δ 值
            a_entries = []
            for a_id, a_sentence in a_sentences:
                a_ppl = calculate_ppl(a_sentence, model, tokenizer)
                delta = a_ppl - t0_ppl
                a_entries.append((delta, a_id, a_sentence, a_ppl))

            # 按 Δ 值降序排序
            a_entries.sort(key=lambda x: x[0], reverse=True)

            # 写入排序后的结果
            for delta, a_id, a_sentence, a_ppl in a_entries:
                f_out.write(f"{a_id} Sentence: {a_sentence}\n")
                f_out.write(f"{a_id} PPL: {a_ppl:.2f} (Δ: {delta:+.2f})\n\n")

            f_out.write("-" * 50 + "\n\n")

if __name__ == "__main__":
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="计算句子的PPL及其差值")
    parser.add_argument("--input", type=str, required=True, help="输入文件路径")
    parser.add_argument("--output", type=str, required=True, help="输出文件路径")
    parser.add_argument("--model", type=str, default="./model/gpt2-Chinese", 
                      help="模型路径（默认为'./model/gpt2-Chinese'）")
    args = parser.parse_args()

    # 加载模型和分词器
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model)
    model.eval()

    # 解析格式化文件
    blocks = parse_formatted_file(args.input)
    # 处理块并计算
    process_blocks(blocks, model, tokenizer, args.output)

    print(f"计算完成！结果保存至 {args.output}")



''' # 对输入句子每一个token都进行ppl预测的debug函数
    def debug_ppl(sentence, model_name="uer/gpt2-chinese-cluecorpussmall"):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    model.eval()

    inputs = tokenizer(sentence, return_tensors="pt")
    input_ids = inputs["input_ids"][0]  # 取第一个句子的token ID列表

    with torch.no_grad():
        outputs = model(input_ids.unsqueeze(0))  # 添加 batch 维度
        logits = outputs.logits

    probs = torch.softmax(logits, dim=-1)
    tokens = tokenizer.convert_ids_to_tokens(input_ids)

    # 仅遍历前 n-1 个 token 的预测
    for i in range(len(input_ids) - 1):
        current_token = tokens[i]
        true_next_token_id = input_ids[i + 1].item()  # 下一个 token 的真实 ID
        predicted_probs = probs[0, i, :]  # 第 i 个位置对下一个 token 的预测概率
        token_prob = predicted_probs[true_next_token_id].item()

        print(f"Position {i}: Token '{current_token}' → Next token '{tokens[i+1]}' | P = {token_prob:.4f}")
## debug_ppl("我去商店买东西了了，商店的人好多了的，买完东西我就回家了的了。")
'''
