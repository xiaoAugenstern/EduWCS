# 如果遇到报错：
model/error_type/grammar_predict.py

输入：source、target 进行调试


# 国汉平台启动
1. 导入qianwen模型（8000端口用于进行语法纠错）

conda activate llama_factory

cd /home/xiaoman/project/Qwen-GEC/LLaMA-Factory/
cd /root/project/EduWSC/LLaMA-Factory


/root/project/LLMs/Qwen2.5-7B-Instruct/

API_PORT=8000 CUDA_VISIBLE_DEVICES=0 llamafactory-cli api examples/inference/qwen2_5vl.yaml

2. cgec platform（其他功能的接口）

conda activate llama_factory

cd /home/xiaoman/project/Qwen-GEC/

python predict.py

