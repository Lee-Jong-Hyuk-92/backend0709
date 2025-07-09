# C:\Users\sptzk\Desktop\p0707\backend\routes\image_routes.py
import os
from datetime import datetime
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from werkzeug.utils import secure_filename

from ai_model.model import perform_inference # AI 모델 임포트
from models.model import MongoDBClient # MongoDB 클라이언트 임포트

# Blueprint 생성
image_bp = Blueprint('image', __name__)

# MongoDB 클라이언트 인스턴스 (app.py에서 초기화된 것을 사용하도록 변경)
# Blueprint는 앱 컨텍스트가 활성화된 후에만 current_app.config에 접근할 수 있으므로,
# 요청 처리 함수 내에서 current_app.config를 사용하거나,
# app.py에서 초기화된 mongo_client 인스턴스를 전달하는 방법을 고려해야 합니다.
# 여기서는 app.py에서 초기화된 mongo_client를 직접 사용한다고 가정합니다.
# 실제로는 app.py에서 mongo_client를 전역 변수로 선언하고,
# 이 파일에서 from app import mongo_client 와 같이 임포트하는 것이 간단할 수 있습니다.
# 또는 Flask-PyMongo와 같은 확장 기능을 사용하는 것이 더 견고합니다.
# 일단은 app.py에서 mongo_client를 전역으로 사용할 수 있다고 가정합니다.
# (또는 함수 내에서 current_app.mongo_client 등으로 접근하도록 app.py에서 설정)
# 여기서는 설명을 위해 임시로 함수 내에서 MongoDBClient를 생성하는 방식으로 작성합니다.
# 실제 배포 시에는 Singleton 패턴이나 Flask 확장을 사용하는 것이 좋습니다.

# 파일 확장자 확인 (app.py의 함수를 직접 가져오기 어려우므로, 여기에 다시 정의)
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@image_bp.route('/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file part'}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'error': 'No selected image file'}), 400

    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        unique_filename = f"{timestamp}_{filename}"
        original_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        image_file.save(original_path)

        inference_output = perform_inference(original_path, current_app.config['PROCESSED_UPLOAD_FOLDER'])
        if inference_output.get("error"):
            return jsonify({'error': f"Inference failed: {inference_output['error']}"}), 500

        result_json = {
            "prediction": inference_output.get("prediction"),
            "details": inference_output.get("details", [])
        }
        processed_path = inference_output.get("processed_image_path")
        if not processed_path:
            return jsonify({'error': 'Missing processed image path'}), 500

        try:
            # MongoDB 클라이언트를 요청 컨텍스트에서 가져오거나 전역으로 접근
            # 여기서는 app.py에서 초기화된 mongo_client를 직접 임포트했다고 가정
            # from app import mongo_client # 이렇게 임포트하거나
            # 또는 current_app.extensions['mongo_client'] 등으로 접근 (Flask 확장 사용 시)
            # 여기서는 간단히 다시 인스턴스화 (좋은 방법은 아님, 예시를 위해)
            mongo_client_instance = MongoDBClient()
            mongo_client_instance.insert_result({
                'original_image_filename': unique_filename,
                'original_image_path': original_path,
                'processed_image_path': processed_path,
                'inference_result': result_json,
                'timestamp': datetime.now()
            })
        except Exception as e:
            return jsonify({'error': f'MongoDB insert error: {e}'}), 500

        return jsonify({
            'message': 'Image uploaded and processed',
            'image_url': f"/processed_uploads/{os.path.basename(processed_path)}",
            'inference_data': result_json
        }), 200

    return jsonify({'error': 'Invalid file type'}), 400

@image_bp.route('/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@image_bp.route('/processed_uploads/<filename>')
def serve_processed(filename):
    return send_from_directory(current_app.config['PROCESSED_UPLOAD_FOLDER'], filename)