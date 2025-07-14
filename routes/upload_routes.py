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


@upload_bp.route('/upload', methods=['POST'])  # ✅ Flutter가 요청하는 경로 추가
def upload_plain_image():
    """
    Flutter 앱이 이미지만 보내는 경우 처리하는 엔드포인트.
    내부적으로 /upload_masked_image 로직 재사용.
    """
    return upload_masked_image()  # 동일 처리


@upload_bp.route('/upload_masked_image', methods=['POST'])
def upload_masked_image():
    print("📅 [요청 수신] /upload_masked_image")

    if 'file' not in request.files:
        print("❌ [에러] 파일 누락")
        return jsonify({'error': '이미지 파일이 필요합니다.'}), 400

    file = request.files['file']
    user_id = request.form.get('user_id', 'anonymous')

    # ✅ YOLO 결과 JSON (선택사항)
    yolo_results_json_str = request.form.get('yolo_results_json')
    yolo_inference_data = []

    if yolo_results_json_str:
        try:
            yolo_inference_data = json.loads(yolo_results_json_str)
            print(f"✅ YOLO 결과 수신: {len(yolo_inference_data)}개 감지")
        except json.JSONDecodeError as e:
            print(f"❌ [에러] YOLO 결과 JSON 파싱 오류: {e}")
            return jsonify({'error': f'YOLO 결과 JSON 형식이 올바르지 않습니다: {e}'}), 400
    else:
        print("ℹ️ YOLO 결과 없이 진행")

    if file.filename == '':
        return jsonify({'error': '파일명이 비어 있습니다.'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': '허용되지 않는 파일 형식입니다.'}), 400

    try:
        # 디렉토리 준비
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'camera')
        processed_dir = os.path.join(current_app.config['PROCESSED_UPLOAD_FOLDER'], 'camera')
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)

        # 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        original_filename = secure_filename(file.filename)
        base_name = f"{user_id}_{timestamp}_{original_filename}"
        original_path = os.path.join(upload_dir, base_name)
        file.save(original_path)
        print(f"✅ 원본 이미지 저장 완료: {original_path}")

        # AI 추론
        image = Image.open(original_path).convert("RGB")
        print("🧠 [AI 추론 시작]")
        masked_image, lesion_points, backend_model_confidence, backend_model_name = predict_overlayed_image(image)
        print("✅ [AI 추론 완료] 모델:", backend_model_name)

        # 결과 저장
        masked_path = os.path.join(processed_dir, base_name)
        masked_image.save(masked_path)
        print(f"✅ 마스크 이미지 저장 완료: {masked_path}")

        # MongoDB 저장
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
        print("✅ [MongoDB 저장 완료]")

        return jsonify({
            'message': '이미지 업로드 및 마스킹 성공',
            'original_image_path': f"/uploads/camera/{base_name}",
            'processed_image_path': f"/processed_uploads/camera/{base_name}",
            'mask_url': f"/processed_uploads/camera/{base_name}",
            'inference_result': {
                'message': '마스크 이미지가 성공적으로 생성되었습니다.',
                'lesion_points': lesion_points,
                'backend_model_confidence': backend_model_confidence,
                'yolo_detections': yolo_inference_data,
                'model_used': backend_model_name
            }
        }), 200

    except Exception as e:
        print(f"❌ [서버 처리 중 예외] {str(e)}")
        return jsonify({'error': f'서버 처리 중 오류 발생: {str(e)}'}), 500
