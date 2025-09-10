# EAGCS: Editing Adjustable Grammar Correction System 编辑可调控语法纠错系统

语法纠错任务旨在给定一个错误的句子，通过纠正得到一个正确的句子。已有的语法纠错工作通常只能生成一个或者多个语法正确的句子。然而，它们面临着修改之后的句子可能**过度纠正**或者**欠纠正**的问题，当我们把语法纠错系统用在实际场景中时，适当的纠正是至关重要的。目前的语法纠错系统对于纠正的编辑错误是无法调控的，基于此，我们尝试搭建一个**可调控的语法纠错系统**，**以错误编辑为单位**对模型输出进行调试。

我们将一个错误的句子表示为 $ S=(w_1, w_2, ..., w_k) $ 的字符序列，经过一个语法纠错模型，该错误句子将被转换为正确的字符序列 $ T=(v_1, v_2, ..., v_l) $ 其中 k 不一定等于 l。从 $S \rightarrow T$，我们能够得到一系列的编辑 $ e=(w_1, w_2)  \rightarrow (v_1, v_2, v_3) $ , 我们要设计一个打分函数$ s(e) $对编辑集合进行打分，通过对分数的排序可以体现错误编辑的优先排序，从而进行可调控的语法纠错。

对编辑进行评分的评级指标：
$$ s(e) = PPL(T) - PPL(T\backslash e) $$
其中，$ PPL(T) $代表修改后句子的PPL值，$ PPL(T\backslash e) $代表不实施e修改而其他修改全部实施的句子的PPL。$ s(e) $能够衡量编辑e对句子通畅的必要性，$ s(e) $越大意味着$ \Delta PPL$越大，也意味着对应的编辑e越重要。

## 框架结构
```
.
|-- data # 相关数据
|-- model # model抽象类及已经集成的模型
   |-- gpt2-Chinese # PPL计算使用的分词模型
   |-- small # ltp_small，产生m2.word文件使用的分词模型
   |-- ...
|-- module # 可复用的组件
|-- samples # 存放输入输出以及中间文件，初始状态下应至少存在.input和.hyp文件
|-- utils # 使用到的其它代码
|-- demo.sh # demo.py的命令集合
|-- demo.py # 将输入.input和.hyp文件输出为m2文件
|-- parallel_to_m2.py # 将.para文件转为m2文件
|-- PPL_calculator.py # PPL计算
|-- requirements.txt # 相关依赖
|-- single_edit_generation.py # 从m2文件中提取单个编辑不实施的句子
```

## 使用方法

#### 准备工作
保证 samples 文件夹下存有**两个输入文件** .input（修改之前的句子集合）和 .hyp（修改之后的句子集合），格式参考 demo.input 和 demo.hyp。

#### 生成m2文件
从提前加载到 samples 文件夹中的 .input 和 .hyp 文件中提取编辑并转化成 m2 格式文件。
在终端中运行：
```
python demo.py -i $INPUT_FILE -p $HYP_FILE -o {name of output} -g {word/char}
```
具体参数细节请查看 demo.sh 脚本。

#### 生成中间句
从 m2 格式文件中提取编辑并生成所有单个编辑不实施的句子。（每个初始句子句子一个块）
在终端中运行
```
python single_edits_generation.py --input $M2_FILE --output $OUTPUT_TXT
```
具体参数细节通过运行以下命令查看：
```
python single_edits_generation.py -h
```

#### 计算PPL并降序排列
将上一步得到的文本文件中的句子计算PPL并按照降序排序。
在终端中运行
```
python PPL_calculator.py --input $VARIANTS_TXT --output $RESULTS_TXT --model $MODEL_NAME
```
具体参数细节通过运行以下命令查看：
```
python PPL_calculator -h
```

最终得到的RESULTS_TXT即为已经按照编辑PPL降序排列的文本。

## 参考文献
```
@inproceedings{zhang-etal-2022-mucgec,
    title = "{MuCGEC}: a Multi-Reference Multi-Source Evaluation Dataset for Chinese Grammatical Error Correction",
    author = "Zhang, Yue and Li, Zhenghua and Bao, Zuyi and Li, Jiacheng and Zhang, Bo and Li, Chen and Huang, Fei and Zhang, Min",
    booktitle = "Proceedings of NAACL-HLT",
    year = "2022",
    address = "Online",
    publisher = "Association for Computational Linguistics"
```