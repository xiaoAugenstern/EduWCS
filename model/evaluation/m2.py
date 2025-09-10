import subprocess
from model.error_type.grammar_predict import parse_m2_file


# Define file paths
input_file = 'scorers/ChERRANT/samples/yolo.input'
output_file = 'scorers/ChERRANT/samples/yolo.hyp'
hyp_para_file = 'scorers/ChERRANT/samples/yolo.hyp.para'
hyp_m2_file = 'scorers/ChERRANT/samples/yolo.hyp.m2.char'

# Source and predicted text to write into files
# source = '阮氏莺225974045D我的假期我在上海读书了半年多了。虽然在这生活了一段不短的时间了,但是紧张的学习让我没有时间做我想做的事。之所以我想利用下个月的假日来好好放松一下自己的身心和完成我以前还没完成的计划。这周就是期中考试的,加上考试完后刚好是放五一的,所以我会好好放松放松。首先,我已经和朋友约好下周会一起去打羽毛球。打完羽毛球后我们会一起去吃夜销。其次,我会去参观一下世纪公园。因为我在小红书看到大家的照,拍的特别好看,公园里面还有一个很大的潮,所以我想去看看。另外里面的花也开得特别好,所以我希望,我去的时候它们还没调谢。最后,我打算到时看情况,如果我不累,我会去上海其他公园。然后到最后放假的一天,我会在宿舍好好体息,预习一下,明天要上课的内容,让自己避免得了假期综合征。这样还可以提高我学习效率。这是我今年五一的计划,希望我能开开心心地度过这个假期。'
# source = replace_punctuation(source)
# predict = '阮氏莺225974045D，我的假期我在上海读书已经半年多了。虽然在这生活了一了段不短的时间，但是紧张的学习让我没有时间做我想做的事。之所以我想利用下个月的假期来好好放松自己的身心，并完成之前未完成的计划。这周就是期中考试时间，加上考试完后刚好是放五一假期，所以我会好好放松一下。首先，我已经和朋友约好下周一起去打羽毛球。打完羽毛球后我们会一起去吃夜宵。其次，我会去参观一下世纪公园。因为我在小红书上看到大家的照片，拍得特别好看，公园里面还有一个很大的潮玩区域，所以我想去看看。另外里面的花也开得特别好，所以我希望，我去的时候它们还没凋谢。最后，我打算到时候看情况，如果我不累，我会去上海的其他公园。然后到最后放假的一天，我会在宿舍好好休息，预习一下，明天要上课的内容，让自己避免得了假期综合征。这样还可以提升我的学习效率。这是我今年五一的计划，希望我能开开心心地度过这个假期。'

# source = '我在上海读书了半年多了。'
# predict = '我在上海读书已经半年多了。'

source = '因为，在地上的话，我跑的速度很限制，'
predict = "因为，在地上的话，我跑的速度很有限，"

with open(input_file, 'w') as f_input, open(output_file, 'w') as f_output:
    f_input.write(source)
    f_output.write(predict)

# Run the paste and awk command
paste_command = f"paste {input_file} {output_file} | awk '{{print NR\"\\t\"$p}}' > {hyp_para_file}"
subprocess.run(paste_command, shell=True, check=True)

# Run the parallel_to_m2.py script for char-level evaluation
m2_command = f"python ./scorers/ChERRANT/parallel_to_m2.py -f {hyp_para_file} -o {hyp_m2_file} -g word"
subprocess.run(m2_command, shell=True, check=True)

parse_m2_file(hyp_m2_file)