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


# 示例调用
if __name__ == "__main__":

    input = '/home/lishuai/Qwen-GEC/model/evaluation/scorers/ChERRANT/samples/platform.hyp.m2.char'
    w = '/home/lishuai/EAGCS/EAGCS/samples/platform.txt'
    output = '/home/lishuai/EAGCS/EAGCS/samples/2.txt'
    reorder_annotations(input, w, output)
