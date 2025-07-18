import sys
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import DevelopmentConfig
from models.model import db, MongoDBClient

# Blueprint 라우트 임포트
from routes.auth_routes import auth_bp
from routes.image_routes import image_bp
from routes.upload_routes import upload_bp
from routes.inference_routes import inference_bp
from routes.static_routes import static_bp
from routes.application_routes import application_bp
from routes.consult_routes import consult_bp
# from routes.chatbot_routes import chatbot_bp # 챗봇 기능이 app.py에 직접 구현되므로 이 블루프린트는 임포트하지 않음 (삭제하거나 주석 처리)

# ✅ Gemini API 관련 임포트
from google.generativeai import configure, GenerativeModel, list_models # list_models 임포트 추가

# ✅ 환경 변수에서 API 키 로드
from dotenv import load_dotenv
load_dotenv()
'''
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini API 키 확인
if not GEMINI_API_KEY:
    raise ValueError("Gemini API 키가 환경 변수에 설정되지 않았습니다. .env 파일을 확인하세요.")

# ✅ Gemini 구성 및 모델 초기화
configure(api_key=GEMINI_API_KEY)

# 🌟 중요: 'models/gemini-pro'는 list_models() 결과에 따라 다를 수 있습니다.
#    아래 명령어를 실행하여 정확히 어떤 모델 이름을 사용해야 하는지 확인하세요.
#    `python -c "import os; from google.generativeai import configure, list_models; from dotenv import load_dotenv; load_dotenv(); configure(api_key=os.getenv('GEMINI_API_KEY')); [print(f'- {m.name} (Supports generateContent)') for m in list_models() if 'generateContent' in m.supported_generation_methods];"`
try:
    # 대부분의 경우 'models/gemini-pro'가 올바르지만, 확인된 이름으로 변경해야 합니다.
    # 예: gemini_model = GenerativeModel('models/gemini-1.5-flash-latest')
    gemini_model = GenerativeModel('models/gemini-2.5-pro')

    # 모델이 generateContent 메서드를 지원하는지 확인 (선택 사항이지만 안정성 높임)
    supported = False
    for m in list_models():
        if m.name == 'models/gemini-2.5-pro' and 'generateContent' in m.supported_generation_methods:
            supported = True
            break
    if not supported:
        raise ValueError(f"선택된 Gemini 모델 ('models/gemini-2.5-pro')이 'generateContent' 메서드를 지원하지 않거나 존재하지 않습니다.")

except Exception as e:
    # 모델 초기화 또는 지원 여부 확인 실패 시 서버 시작을 중단
    print(f"ERROR: Gemini 모델 초기화 또는 지원 확인 오류: {e}", file=sys.stderr)
    sys.exit(1) # 서버 시작 중단'''

# Flask 앱 초기화
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

print(f"✅ 연결된 DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

# 디렉토리 생성
os.makedirs(app.config['UPLOAD_FOLDER_ORIGINAL'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER_MODEL1'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER_MODEL2'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER_MODEL3'], exist_ok=True)

# CORS 설정
CORS(app)

# DB 초기화
db.init_app(app)

# MongoDB 클라이언트 등록
mongo_client = MongoDBClient(
    uri=app.config['MONGO_URI'],
    db_name=app.config['MONGO_DB_NAME']
)
app.extensions = getattr(app, 'extensions', {})
app.extensions['mongo_client'] = mongo_client

# SQL 테이블 생성 (애플리케이션 컨텍스트 내에서 실행)
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
# app.register_blueprint(chatbot_bp, url_prefix='/chatbot') # chatbot_routes.py를 사용하지 않으므로 이 줄은 주석 처리 또는 삭제합니다.

# 기본 엔드포인트
@app.route('/')
def index():
    return "Hello from MediTooth Backend!"

# ✅ Gemini 챗봇 API
'''@app.route("/api/chat", methods=["POST"])
def chat_with_gemini():
    data = request.json
    user_id = data.get("user_id")
    message = data.get("message")

    # 로그: Flutter 앱에서 받은 user_id와 message 확인
    app.logger.info(f"Received chat request: user_id='{user_id}', message='{message}'")

    if not user_id or not message:
        app.logger.warning("user_id 또는 message가 누락되었습니다.")
        return jsonify({"error": "user_id와 message는 필수입니다."}), 400

    try:
        records = mongo_client.db['inference_results']
        record = records.find_one({"user_id": user_id})

        system_instruction = ""
        if record:
            app.logger.info(f"MongoDB record FOUND for user_id: '{user_id}'")
            # 기록 요약
            summary = f"""
            환자 ID: {user_id}
            진단일: {record.get('timestamp')}
            AI 진단 결과: {record.get('inference_result', {}).get('message', '없음')}
            병변 정보: {record.get('inference_result', {}).get('lesion_points', [])}
            의사 코멘트: {record.get('doctor_comment', '없음')}
            """
            system_instruction = f"당신은 치과 관련 챗봇입니다. 다음 환자의 진료 기록을 참고하여 사용자의 질문에 답변해주세요. 기록에 없는 내용은 일반적인 정보를 제공하되, 진단이나 처방은 할 수 없다고 명확히 알려주세요.\n\n환자 진단 기록:\n{summary}"
        else:
            app.logger.info(f"No MongoDB record FOUND for user_id: '{user_id}'")
            # 환자 기록이 없을 때 특정 질문(예: '마지막 진료')에 대한 특별 응답
            if "마지막 진료" in message or "진료 기록" in message:
                 app.logger.info("Specific query for patient record without record, returning 'not found' message.")
                 return jsonify({"response": "해당 환자 기록을 찾을 수 없습니다. 정확한 진료를 위해 진료 기록을 먼저 등록해주세요."})
            
            # 그 외의 질문은 기록 없이 일반적인 치과 챗봇 대화를 진행
            system_instruction = "당신은 치과 관련 챗봇입니다. 환자 기록이 없으므로 일반적인 치과 관련 질문에 답변해 드릴 수 있습니다. 진단이나 처방은 할 수 없습니다."

        # Gemini 채팅 시작 및 메시지 전송
        # history에 시스템 지시를 먼저 전달하여 챗봇의 역할을 명확히 합니다.
        chat = gemini_model.start_chat(history=[
            {"role": "user", "parts": [system_instruction]}
        ])
        response = chat.send_message(message) # 사용자의 실제 메시지 전송

        if not response:
            app.logger.error("Gemini에서 응답을 받지 못했습니다.")
            return jsonify({"error": "Gemini에서 응답을 받지 못했습니다."}), 500

        app.logger.info(f"Gemini response received: {response.text}")
        return jsonify({"response": response.text})

    except Exception as e:
        app.logger.error(f"Gemini 처리 중 예외 발생: {str(e)}", exc_info=True) # exc_info=True로 스택 트레이스 출력
        return jsonify({"error": f"Gemini 처리 오류: {str(e)}"}), 500

# 오류 핸들링
@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"서버 내부 오류 발생: {str(error)}", exc_info=True) # exc_info=True로 스택 트레이스 출력
    return jsonify({"error": "서버 내부 오류", "details": "서버 로그를 확인하세요."}), 500'''

# 서버 실행
if __name__ == '__main__':
    # 디버그 모드에서 개발용으로만 사용하고, 프로덕션에서는 Gunicorn 등 WSGI 서버를 사용 권장
    app.run(debug=True, host='0.0.0.0', port=5000)