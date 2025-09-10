import subprocess
import os
granularity='char'
source = "阮氏莺225974045D我的假期我在上海读书了半年多了。虽然在这生活了一段不短的时间了，但是紧张的学习让我没有时间做我想做的事。之所以我想利用下个月的假日来好好放松一下自己的身心和完成我以前还没完成的计划。这周就是期中考试的，加上考试完后刚好是放五一的，所以我会好好放松放松。首先，我已经和朋友约好下周会一起去打羽毛球。打完羽毛球后我们会一起去吃夜销。其次，我会去参观一下世纪公园。因为我在小红书看到大家的照，拍的特别好看，公园里面还有一个很大的潮，所以我想去看看。另外里面的花也开得特别好，所以我希望，我去的时候它们还没调谢。最后，我打算到时看情况，如果我不累，我会去上海其他公园。然后到最后放假的一天，我会在宿舍好好体息，预习一下，明天要上课的内容，让自己避免得了假期综合征。这样还可以提高我学习效率。这是我今年五一的计划，希望我能开开心心地度过这个假期。"
predict = "阮氏莺225974045D我的假期我在上海读书了半年多了。虽然在这生活了一段时间了，但是紧张的学习让我没有时间做我想做的事。之所以我想利用下个月的假日来好好放松一下自己的身心和完成我以前还没完成的计划。这周就是期中考试的时候，加上考试完后刚好是五一假期，所以我会好好放松放松。首先，我已经和朋友约好下周会一起去打羽毛球。打完羽毛球后我们会一起去吃夜宵。其次，我会去参观世纪公园。因为我在小红书看到大家的照，拍的特别好看，公园里面还有一个很大的广场，所以我想去看看。另外里面的花也开得特别好，所以我希望，我去的时候它们还没凋谢。最后，我打算到时看情况，如果我不累，我会去上海其他公园。然后到最后放假的一天，我会在宿舍好好休息，预习一下，明天要上课的内容，让自己避免假期综合征。这样还可以提高我学习效率。这是我今年五一的计划，希望我能开开心心地度过这个假期。"
current_path = os.path.join(os.path.dirname(__file__))
cherrant_path = os.path.join(current_path,'model/evaluation/scorers/ChERRANT')
samples_path = os.path.join(cherrant_path,'samples')
parallel_to_m2_path = os.path.join(cherrant_path, 'parallel_to_m2.py')

input_file = os.path.join(samples_path,'platform.input')
output_file = os.path.join(samples_path,'platform.hyp')
hyp_para_file = os.path.join(samples_path,'platform.hyp.para')
hyp_m2_file = os.path.join(samples_path,f'platform.hyp.m2.{granularity}')
with open(input_file, 'w') as f_input, open(output_file, 'w') as f_output:
        f_input.write(source)
        f_output.write(predict)
paste_command = f"paste {input_file} {output_file} | awk '{{print NR\"\\t\"$p}}' > {hyp_para_file}"
subprocess.run(paste_command, shell=True, check=True)
m2_command = f"/home/lishuai/.conda/envs/qwen/bin/python {parallel_to_m2_path} -f {hyp_para_file} -o {hyp_m2_file} -g {granularity}"
subprocess.run(m2_command, shell=True, check=True)
# 在此修改使得************ls输出的platfrom文件顺序改变
    
single_edits_generation_path = "/home/lishuai/EAGCS/EAGCS/single_edit_generation.py"
PPL_calculator_path = "/home/lishuai/EAGCS/EAGCS/platformPPL.py"
variants_txt_path = "/home/lishuai/EAGCS/EAGCS/samples/platformVariantput.txt"
results_txt_path = f"/home/lishuai/EAGCS/EAGCS/samples/platform.txt"
orderedPlatform = f'/home/lishuai/EAGCS/EAGCS/samples/platformOrdered.hyp.m2.{granularity}'

beforeOrderFile = hyp_m2_file # 相当于hype.m2.char
model_path = "/home/lishuai/EAGCS/EAGCS/model/gpt2-Chinese"
single_edit_cmd = f"/home/lishuai/.conda/envs/qwen/bin/python {single_edits_generation_path} --input {beforeOrderFile} --output {variants_txt_path}"
subprocess.run(single_edit_cmd, shell=True, check=True)
ppl_calc_cmd = f"/home/lishuai/.conda/envs/qwen/bin/python {PPL_calculator_path} --input {variants_txt_path} --output {results_txt_path} --model {model_path} "
reorder_annotations(beforeOrderFile, results_txt_path, orderedPlatform)
subprocess.run(ppl_calc_cmd, shell=True, check=True)


def reorder_annotations(input_file, order_file, output_file):
    # 读取顺序文件（w.txt）
    with open(order_file, 'r', encoding='utf-8') as f:
        order_lines = [line.strip() for line in f if line.strip()]

    # 读取输入文件（input.txt）
    with open(input_file, 'r', encoding='utf-8') as f:
        input_lines = [line.strip() for line in f if line.strip()]

    # 初始化
    s_line = ""
    t_line = ""
    a_lines = {}
    a = 1
    for line in input_lines:
        if line.startswith("S "):
            s_line = line
        elif line.startswith("T0-A0"):
            t_line = line
        elif line.startswith("A"):
            
            key = f"A{a}"
            a += 1
            a_lines[key] = line
            

    # 构建输出内容
    output = [s_line, t_line]
 
    for key in order_lines:
        if key in a_lines:
            output.append(a_lines[key])
        else:

            print(f"[Warning] {key} not found in input.")

    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in output:
            f.write(line + '\n')

    print(f"[Info] Done! Output written to {output_file}")