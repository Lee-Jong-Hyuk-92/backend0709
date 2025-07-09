# app.py
import os
from flask import Flask, jsonify
from flask_cors import CORS

from config import DevelopmentConfig
from models.model import db, MongoDBClient

# Blueprint 모듈
from routes.auth_routes import auth_bp
from routes.image_routes import image_bp
from routes.upload_routes import upload_bp  # ✅ 새로 만든 라우트

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
mongo_client = MongoDBClient(
    uri=app.config['MONGO_URI'],
    db_name=app.config['MONGO_DB_NAME']
)
# 전역 사용 가능하도록 확장에 추가
app.extensions = getattr(app, 'extensions', {})
app.extensions['mongo_client'] = mongo_client

# SQL 테이블 생성
with app.app_context():
    db.create_all()

# 라우트 등록
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(image_bp)  # /upload_image 등
app.register_blueprint(upload_bp,url_prefix='/api')  # /upload_masked_image

@app.route('/')
def index():
    return "Hello from p0707 Backend!"

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "서버 내부 오류 발생", "details": str(error)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)