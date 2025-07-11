import os
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from PIL import Image
import json # JSON 처리를 위해 추가

from ai_model.predictor import predict_overlayed_image  # 🔁 AI 추론 함수
from models.model import MongoDBClient  # ✅ MongoDB 저장용

upload_bp = Blueprint('upload', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@upload_bp.route('/upload_masked_image', methods=['POST'])
def upload_masked_image():
    print("📅 [요청 수신] /upload_masked_image")

    if 'file' not in request.files:
        print("❌ [에러] 파일 누락")
        return jsonify({'error': '이미지 파일이 필요합니다.'}), 400

    file = request.files['file']
    user_id = request.form.get('user_id', 'anonymous')
    
    # ✅ YOLO 추론 결과 JSON 데이터 받기 (클라이언트에서 전송)
    yolo_results_json_str = request.form.get('yolo_results_json')
    yolo_inference_data = []
    if yolo_results_json_str:
        try:
            yolo_inference_data = json.loads(yolo_results_json_str)
            print(f"✅ YOLO 결과 수신: {len(yolo_inference_data)}개 감지")
        except json.JSONDecodeError as e:
            print(f"❌ [에러] YOLO 결과 JSON 파싱 오류: {e}")
            return jsonify({'error': f'YOLO 결과 JSON 형식이 올바르지 않습니다: {e}'}), 400

    # 클라이언트에서 전송하는 model_used는 이제 사용하지 않습니다.
    # 백엔드 모델의 이름은 predict_overlayed_image에서 직접 가져옵니다.
    # model_used_from_client = request.form.get('model_used')
    # if model_used_from_client:
    #     print(f"✅ 클라이언트에서 전송된 모델: {model_used_from_client}")


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

        # ✅ predict_overlayed_image 함수가 4개의 값을 반환하도록 수정
        print("🧠 [AI 추론 시작]")
        masked_image, lesion_points, backend_model_confidence, backend_model_name = predict_overlayed_image(image)
        print("✅ [AI 추론 완료]")
        print(f"✅ 백엔드 모델 이름: {backend_model_name}") # 확인용 출력

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
                'lesion_points': lesion_points,  # 기존 병변 좌표
                'backend_model_confidence': backend_model_confidence, # ✅ 백엔드 모델 신뢰도 추가
                'yolo_detections': yolo_inference_data, # ✅ YOLO 감지 결과 (클라이언트에서 전송)
                'model_used': backend_model_name # ✅ MongoDB에 백엔드 모델 이름 저장
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
                'lesion_points': lesion_points,  # 기존 병변 좌표
                'backend_model_confidence': backend_model_confidence, # ✅ 프론트에도 반환 가능
                'yolo_detections': yolo_inference_data, # ✅ 프론트에도 반환 가능
                'model_used': backend_model_name # ✅ 프론트에도 백엔드 모델 이름 반환
            }
        }), 200

    except Exception as e:
        print(f"❌ [서버 처리 중 예외] {str(e)}")
        return jsonify({'error': f'서버 처리 중 오류 발생: {str(e)}'}), 500