# 最小化参数调用
python demo.py -i input.txt -p predictions.hyp -o output

# 完整参数调用
python demo.py \
  -i ./samples/test.input \
  -p ./samples/test.hyp \
  -o ./samples/test \
  -g word/char

# -i: 输入的.input文件
# -p: 输入的.hyp文件
# -o: 输出的文件名（自动填充.m2.word/.m2.char)
# -g: 粒度word/char

# 生成文件：
# - ./samples/test.para
# - ./samples/test.m2.word