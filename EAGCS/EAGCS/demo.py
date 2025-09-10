"""
GEC评估文件生成工具（支持参数化输入输出）
新增功能：
- 支持自定义输入文件、预测文件和输出前缀
- 自动创建输出目录
- 增强路径校验
"""

import argparse
import subprocess
from pathlib import Path

def validate_file(path: Path):
    """验证输入文件是否存在且可读"""
    if not path.exists():
        raise FileNotFoundError(f"输入文件 {path} 不存在")
    if not path.is_file():
        raise IsADirectoryError(f"{path} 是目录而不是文件")
    return path

def main():
    # 命令行参数配置
    parser = argparse.ArgumentParser(description='生成GEC评估所需的M2格式文件', 
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--input',
                       type=Path,
                       required=True,
                       help='原始输入文件路径（.input格式）')
    parser.add_argument('-p', '--hyp',
                       type=Path,
                       required=True,
                       help='模型预测结果文件路径（.hyp格式）')
    parser.add_argument('-o', '--output',
                       type=Path,
                       required=True,
                       help='输出文件前缀（自动添加扩展名）')
    parser.add_argument('-g', '--granularity',
                       choices=['word', 'char'],
                       default='word',
                       help='评估粒度级别')

    args = parser.parse_args()

    # 输入文件校验
    validate_file(args.input)
    validate_file(args.hyp)

    # 生成中间文件路径
    para_path = args.output.with_suffix('.para')  # 如：/path/to/output.para
    m2_path = args.output.with_suffix(f'.m2.{args.granularity}')  # 如：/path/to/output.m2.word

    # 确保输出目录存在
    para_path.parent.mkdir(parents=True, exist_ok=True)
    m2_path.parent.mkdir(parents=True, exist_ok=True)

    # 生成平行文件（.para）
    print(f"生成平行文件中：{para_path}")
    with open(args.input, 'r', encoding='utf-8') as f_in, \
         open(args.hyp, 'r', encoding='utf-8') as f_out, \
         open(para_path, 'w', encoding='utf-8') as f_para:

        for line_num, (src, tgt) in enumerate(zip(f_in, f_out), start=1):
            f_para.write(f"{line_num}\t{src.strip()}\t{tgt.strip()}\n")

    # 调用外部脚本生成M2文件
    print(f"生成{args.granularity}级别M2文件中：{m2_path}")
    subprocess.run([
        'python',
        'parallel_to_m2.py',
        '-f', str(para_path),
        '-o', str(m2_path),
        '-g', args.granularity
    ], check=True)

if __name__ == "__main__":
    main()