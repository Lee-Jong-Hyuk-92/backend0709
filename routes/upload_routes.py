import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from PIL import Image

from ai_model.predictor import predict_overlayed_image
from models.model import MongoDBClient

upload_bp = Blueprint('upload', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@upload_bp.route('/upload_image', methods=['POST'])
def upload_image_from_flutter():
    return upload_masked_image()

@upload_bp.route('/upload', methods=['POST'])
def upload_plain_image():
    return upload_masked_image()


@upload_bp.route('/upload_masked_image', methods=['POST'])
def upload_masked_image():

    if 'file' not in request.files:
        print("❌ [에러] 파일 누락: 'file' 필드가 없습니다.")
        return jsonify({'error': '이미지 파일이 필요합니다.'}), 400

    file = request.files['file']
    user_id = request.form.get('user_id', 'anonymous')

    yolo_results_json_str = request.form.get('yolo_results_json')
    yolo_inference_data = []

    if yolo_results_json_str:
        try:
            yolo_inference_data = json.loads(yolo_results_json_str)
        except json.JSONDecodeError as e:
            return jsonify({'error': f'YOLO 결과 JSON 형식이 올바르지 않습니다: {e}'}), 400
    else:
        print("ℹ️ YOLO 결과 없이 진행")

    if file.filename == '':
        return jsonify({'error': '파일명이 비어 있습니다.'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': '허용되지 않는 파일 형식입니다.'}), 400

    try:
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'camera')
        processed_dir = os.path.join(current_app.config['PROCESSED_UPLOAD_FOLDER'], 'camera')
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        original_filename = secure_filename(file.filename)
        base_name = f"processed_{timestamp}_{user_id}_{original_filename}"
        original_path = os.path.join(upload_dir, base_name)
        file.save(original_path)

        image = Image.open(original_path).convert("RGB")
        masked_image, lesion_points, backend_model_confidence, backend_model_name = predict_overlayed_image(image)
        masked_path = os.path.join(processed_dir, base_name)
        masked_image.save(masked_path)

        mongo_client = MongoDBClient()
        mongo_client.insert_result({
            'user_id': user_id,
            'original_image_filename': original_filename,
            'original_image_path': f"/uploads/camera/{base_name}",
            'processed_image_path': f"/processed_uploads/camera/{base_name}",
            'inference_result': {
                'message': '마스크 생성 완료',
                'lesion_points': lesion_points,
                'backend_model_confidence': backend_model_confidence,
                'yolo_detections': yolo_inference_data,
                'model_used': backend_model_name
            },
            'timestamp': datetime.now()
        })

        return jsonify({
            'message': '이미지 업로드 및 마스킹 성공',
            'image_url': f"/processed_uploads/camera/{base_name}",
            'original_image_path': f"/uploads/camera/{base_name}",  # ✅ 이 줄 추가!
            'inference_data': {
                'details': lesion_points,
                'prediction': 'Objects detected',
                'backend_model_confidence': backend_model_confidence,
                'model_used': backend_model_name,
                'yolo_detections': yolo_inference_data
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'서버 처리 중 오류 발생: {str(e)}'}), 500