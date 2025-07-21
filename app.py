import sys
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import DevelopmentConfig
from models.model import db, MongoDBClient
from google.generativeai import configure, GenerativeModel, list_models
from dotenv import load_dotenv

# Blueprint 라우트 임포트
from routes.auth_routes import auth_bp
from routes.image_routes import image_bp
from routes.upload_routes import upload_bp
from routes.inference_routes import inference_bp
from routes.static_routes import static_bp
from routes.application_routes import application_bp
from routes.consult_routes import consult_bp
from routes.chatbot_routes import chatbot_bp # chatbot_bp 임포트는 유지

# dotenv로 API 키 불러오기
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Gemini API 키가 없습니다. .env 확인")
configure(api_key=GEMINI_API_KEY)

# Gemini 모델 준비
model_name = 'models/gemini-2.5-flash'
if not any(m.name == model_name and 'generateContent' in m.supported_generation_methods for m in list_models()):
    raise ValueError(f"모델 {model_name}은 generateContent 미지원")

# app.py에서는 직접 gemini_model을 전역으로 생성하지 않고, 필요하다면 chatbot_routes에서 접근하거나,
# app context에 저장하여 사용할 수 있습니다. 여기서는 gemini_model 변수 선언은 유지합니다.
gemini_model = GenerativeModel(model_name)

# Flask 앱 설정
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
CORS(app)

print(f"✅ 연결된 DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

os.makedirs(app.config['UPLOAD_FOLDER_ORIGINAL'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER_MODEL1'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER_MODEL2'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER_MODEL3'], exist_ok=True)

db.init_app(app)
mongo_client = MongoDBClient(uri=app.config['MONGO_URI'], db_name=app.config['MONGO_DB_NAME'])
app.extensions = getattr(app, 'extensions', {})
app.extensions['mongo_client'] = mongo_client
# ✅ Gemini 모델 객체를 app.extensions에 저장하여 다른 Blueprint에서 접근 가능하게 합니다.
app.extensions['gemini_model'] = gemini_model 

with app.app_context():
    db.create_all()

# 라우트 등록
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(image_bp)
app.register_blueprint(upload_bp, url_prefix='/api')
app.register_blueprint(inference_bp, url_prefix='/api')
app.register_blueprint(static_bp)
app.register_blueprint(application_bp, url_prefix='/api')
app.register_blueprint(consult_bp, url_prefix='/api/consult')
app.register_blueprint(chatbot_bp) # 챗봇 블루프린트 등록은 유지

# 기본 엔드포인트
@app.route('/')
def index():
    return "Hello from MediTooth Backend!"

# 기존 /api/chat 엔드포인트 (chat_with_gemini 함수)는 여기에서 제거됩니다.

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "서버 내부 오류"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)