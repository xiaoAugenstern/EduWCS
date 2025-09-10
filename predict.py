from flask import Flask, request, jsonify,send_from_directory
from flask_cors import CORS
from cgec_platform import img_predict
from text_processor import split_predict
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key="0", base_url="http://0.0.0.0:8000/v1")
CORS(app)

@app.route("/get_image/<filename>")
def get_image(filename):
    return send_from_directory('case', filename)

@app.route('/temp_images/<filename>')
def serve_temp_image(filename):
    return send_from_directory('temp_images', filename)

@app.route('/img_correct', methods=['POST'])
def img_correct():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    image_file = request.files['image']
    img_path = './temp_images/temp_uploaded_image.png'
    image_file.save(img_path)
    try:
        source, target,correct_info,guohan_info = img_predict(img_path)
        return jsonify({
            'source': source,
            'target': target,
            'correct_info': correct_info,
            'guohan_info': guohan_info
        }), 200
    except Exception as e:
        print("Error in img_predict:", e)
        return jsonify({'error': str(e)}), 500


@app.route('/correct', methods=['POST'])
def correct_passage():
    data = request.json
    passage = data.get('passage', '')

    if not passage:
        return jsonify({'error': 'No passage provided'}), 400

    prompt_template = (
        """你是一位经验丰富的中文老师，专门纠正学生作文中的语法错误，基于最小编辑原则。请根据以下要求进行修正：
        1. 仅修正句子中的语法和用词错误。
        2. 如果句子没有错误，请不要进行任何修改，保持原句不变。
        3. 不要改变句子的结构或原意。
        4. 请直接返回纠正后的文本内容，不要添加任何额外的提示信息。
        
        例如：
        输入：所以这是要触定计划再走。
        输出：所以这是要确定计划再走。
        
        输入：未来的科技生活才能真正成为人们美好生活的一部分。
        输出：未来的科技生活才能真正成为人们美好生活的一部分。
        """
    )
    index_source_corrected,corrected_passage = split_predict(passage, prompt_template,client)
    return jsonify({
        'corrected_passage': corrected_passage,
        'index_source_corrected': index_source_corrected
    })

if __name__ == '__main__':
    '''
    Post请求
    curl -X POST http://localhost:5000/correct -H "Content-Type: application/json" -d '{"passage": "未来的科技生活才能真正成为人们美好生活的一部分"}'
    
    相应
    corrected_passage = decode_corrected_passage(json_str)
    print(corrected_passage)
    '''

    app.run(host='0.0.0.0', port=5000)