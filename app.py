import sys
import os
from flask import Flask, jsonify
from flask_cors import CORS

from config import DevelopmentConfig
from models.model import db, MongoDBClient # MongoDBClient 임포트 확인

# Blueprint 모듈 임포트
from routes.auth_routes import auth_bp
from routes.image_routes import image_bp
from routes.upload_routes import upload_bp
from routes.inference_routes import inference_bp   # ✅ 추가
from routes.static_routes import static_bp  # ✅ 추가

# Flask 애플리케이션 초기화
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

# 디렉토리 생성
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'camera'), exist_ok=True)
os.makedirs(os.path.join(app.config['PROCESSED_UPLOAD_FOLDER'], 'camera'), exist_ok=True)

# CORS 활성화
CORS(app)

# DB 초기화
db.init_app(app)

# MongoDB 클라이언트 인스턴스를 앱 컨텍스트에 등록
# app.config에서 MONGO_URI와 MONGO_DB_NAME을 가져와서 초기화합니다.
mongo_client = MongoDBClient(
    uri=app.config['MONGO_URI'],
    db_name=app.config['MONGO_DB_NAME']
)
# 전역 사용 가능하도록 확장에 추가
app.extensions = getattr(app, 'extensions', {})
app.extensions['mongo_client'] = mongo_client

# SQL 테이블 생성 (앱 컨텍스트 내에서 실행)
with app.app_context():
    db.create_all()

# 라우트 등록
# auth_bp에 정의된 모든 라우트는 '/api/auth' 접두사를 가집니다.
app.register_blueprint(auth_bp, url_prefix='/api/auth')
# image_bp는 별도의 접두사 없이 등록됩니다.
app.register_blueprint(image_bp)
# upload_bp에 정의된 모든 라우트는 '/api' 접두사를 가집니다.
app.register_blueprint(upload_bp, url_prefix='/api')

app.register_blueprint(inference_bp, url_prefix='/api')

app.register_blueprint(static_bp)  # ✅ 정적 이미지 라우트 등록

@app.route('/')
def index():
    return "Hello from p0707 Backend!"

@app.errorhandler(500)
def internal_error(error):
    # 에러 발생 시 디테일한 정보를 로깅하고 사용자에게는 일반적인 메시지 전달
    print(f"서버 내부 오류 발생: {str(error)}")
    return jsonify({"error": "서버 내부 오류 발생", "details": "자세한 내용은 서버 로그를 확인해주세요."}), 500

if __name__ == '__main__':
    # debug=True는 개발 환경에서만 사용하고, 배포 시에는 False로 설정하세요.
    # host='0.0.0.0'은 외부 IP에서의 접속을 허용합니다.
    app.run(debug=True, host='0.0.0.0', port=5000)