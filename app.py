import sys
import os
from flask import Flask, jsonify
from flask_cors import CORS

from config import DevelopmentConfig
from models.model import db, MongoDBClient  # ✅ 기존 유지

# Blueprint 모듈 임포트
from routes.auth_routes import auth_bp
from routes.image_routes import image_bp
from routes.upload_routes import upload_bp
from routes.inference_routes import inference_bp   # ✅ 유지
from routes.static_routes import static_bp         # ✅ 유지
from routes.application_routes import application_bp

# ✅ consult_routes 추가 임포트
from routes.consult_routes import consult_bp

# Flask 애플리케이션 초기화
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

print(f"✅ 연결된 DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

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
mongo_client = MongoDBClient(
    uri=app.config['MONGO_URI'],
    db_name=app.config['MONGO_DB_NAME']
)
app.extensions = getattr(app, 'extensions', {})
app.extensions['mongo_client'] = mongo_client

# SQL 테이블 생성 (앱 컨텍스트 내에서 실행)
with app.app_context():
    db.create_all()

# 라우트 등록
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(image_bp)
app.register_blueprint(upload_bp, url_prefix='/api')
app.register_blueprint(inference_bp, url_prefix='/api')
app.register_blueprint(static_bp)
app.register_blueprint(application_bp, url_prefix='/api')

# ✅ consult_bp 라우트 등록
app.register_blueprint(consult_bp, url_prefix='/api/consult')

@app.route('/')
def index():
    return "Hello from p0707 Backend!"

@app.errorhandler(500)
def internal_error(error):
    print(f"서버 내부 오류 발생: {str(error)}")
    return jsonify({"error": "서버 내부 오류 발생", "details": "자세한 내용은 서버 로그를 확인해주세요."}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)