'''from flask import Blueprint, request, jsonify, current_app as app
import google.generativeai as genai
from pymongo import MongoClient
import time
import logging

# 블루프린트 정의
chatbot_bp = Blueprint('chatbot', __name__)

# Gemini API 키 설정 (보통 환경 변수에서 가져오는 게 좋습니다)
genai.configure(api_key="")

# 라우트 정의
@chatbot_bp.route('/chatbot', methods=['POST'])
def chatbot_reply():
    start_time = time.time()  # ✅ 시간 측정 시작

    data = request.json
    user_message = data.get('message')
    patient_id = data.get('patient_id')

    # ✅ MongoDB에서 환자 진료 기록 조회
    client = MongoClient("mongodb://localhost:27017")
    db = client.medicaldb
    record = db.inference_results.find_one({"user_id": patient_id})

    record_text = f"환자 기록: {record}" if record else "환자 기록 없음"

    # ✅ Gemini 모델 초기화 및 대화 시작
    model = genai.GenerativeModel("models/gemini-2.5-pro")
    chat = model.start_chat()

    prompt = f"""
    환자 기록은 다음과 같습니다:\n{record_text}\n\n
    환자가 다음과 같은 질문을 했습니다:\n"{user_message}"\n
    이에 대해 친절하게 설명해주세요.
    """

    response = chat.send_message(prompt)
    reply = response.text

    # ✅ 시간 측정 종료
    elapsed_time = round(time.time() - start_time, 2)

    # ✅ 로그 출력 (Flask logger와 콘솔)
    app.logger.info(f"[⏱️ chatbot_reply] 응답 시간: {elapsed_time}초")
    print(f"[⏱️ chatbot_reply] 응답 시간: {elapsed_time}초")

    return jsonify({'reply': reply, 'elapsed_time': elapsed_time})'''
