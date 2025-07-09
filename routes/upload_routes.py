# ✅ 수정된 upload_routes.py 전체 코드

import os
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from PIL import Image

from ai_model.predictor import predict_overlayed_image  # 🔁 AI 추론 함수
from models.model import MongoDBClient  # ✅ MongoDB 저장용

upload_bp = Blueprint('upload', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@upload_bp.route('/upload_masked_image', methods=['POST'])
def upload_masked_image():
    print("📅 [요청 수신] /upload_masked_image")

    if 'file' not in request.files:
        print("❌ [에러] 파일 누른")
        return jsonify({'error': '이미지 파일이 필요합니다.'}), 400

    file = request.files['file']
    user_id = request.form.get('user_id', 'anonymous')

    if file.filename == '':
        print("❌ [에러] 파일명 없음")
        return jsonify({'error': '파일명이 비어 있습니다.'}), 400
    if not allowed_file(file.filename):
        print(f"❌ [에러] 허용되지 않은 파일 확장자: {file.filename}")
        return jsonify({'error': '허용되지 않는 파일 형식입니다.'}), 400

    try:
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'camera')
        processed_dir = os.path.join(current_app.config['PROCESSED_UPLOAD_FOLDER'], 'camera')
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
        print(f"📁 [디렉토리 확인] 원본: {upload_dir}, 마스크: {processed_dir}")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        original_filename = secure_filename(file.filename)
        base_name = f"{user_id}_{timestamp}_{original_filename}"
        original_path = os.path.join(upload_dir, base_name)

        print(f"📂 [원본 저장 중] {original_path}")
        file.save(original_path)
        print(f"✅ [원본 저장 완료]")

        print(f"🖼️ [이미지 열기] {original_path}")
        image = Image.open(original_path).convert("RGB")

        print("🧠 [AI 추론 시작]")
        masked_image, lesion_points = predict_overlayed_image(image)  # ✅ 변경: 두 값 반환
        print("✅ [AI 추론 완료]")

        masked_path = os.path.join(processed_dir, base_name)
        print(f"📂 [마스크 저장 중] {masked_path}")
        masked_image.save(masked_path)
        print(f"✅ [마스크 저장 완료]")

        mask_url = f"/processed_uploads/camera/{base_name}"

        print("📜 [MongoDB 저장 중]")
        mongo_client = MongoDBClient()
        mongo_client.insert_result({
            'user_id': user_id,
            'original_image_filename': original_filename,
            'original_image_path': original_path,
            'processed_image_path': masked_path,
            'inference_result': {
                'message': '마스크 생성 완료',
                'lesion_points': lesion_points  # ✅ 병변 좌표도 함께 저장
            },
            'timestamp': datetime.now()
        })
        print("✅ [MongoDB 저장 완료]")

        return jsonify({
            'message': '이미지 업로드 및 마스킹 성공',
            'original_image_path': original_path,
            'masked_image_path': masked_path,
            'mask_url': mask_url,
            'inference_result': {
                'message': '마스크 이미지가 성공적으로 생성되었습니다.',
                'lesion_points': lesion_points  # ✅ 프론트에도 반환 가능
            }
        }), 200

    except Exception as e:
        print(f"❌ [서버 처리 중 예외] {str(e)}")
        return jsonify({'error': f'서버 처리 중 오류 발생: {str(e)}'}), 500
