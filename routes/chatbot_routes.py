from flask import Blueprint, request, jsonify, current_app as app # current_app 임포트 추가
# import google.generativeai as genai # 이 줄은 필요 없거나 제거 (app.py에서 전역으로 모델 관리)
from pymongo import MongoClient # 챗봇 API가 직접 DB 접근한다면 필요
import time
import os
import re # 정규표현식 모듈 임포트
from datetime import datetime # datetime 모듈 임포트

chatbot_bp = Blueprint('chatbot', __name__)
# genai.configure(api_key="YOUR_GEMINI_API_KEY") # 이 줄은 app.py에서 처리하므로 주석 처리하거나 제거

# 기존 chatbot_reply 함수 (필요에 따라 유지 또는 삭제)
@chatbot_bp.route('/chatbot', methods=['POST'])
def chatbot_reply():
    start_time = time.time()

    data = request.json
    user_message = data.get('message')
    patient_id = data.get('patient_id')

    # MongoDB에서 해당 환자의 가장 최근 기록 가져오기
    # current_app을 통해 mongo_client 접근
    mongo_client = app.extensions['mongo_client'] 
    db = mongo_client.db # MongoDBClient 인스턴스의 db 속성을 사용
    record = db.inference_results.find_one(
        {"user_id": patient_id},
        sort=[("timestamp", -1)]
    )

    # 환자 기록 요약 문자열
    if not record:
        record_text = "환자 기록 없음"
        image_url = None
    else:
        # 모델별 inference_result가 Map으로 저장되어있다고 가정
        model1_inf = record.get('model1_inference_result', {})
        model2_inf = record.get('model2_inference_result', {})
        model3_inf = record.get('model3_inference_result', {})

        model1_label = model1_inf.get('label', '없음')
        model2_label = model2_inf.get('label', '없음')
        model3_tooth = model3_inf.get('tooth_number_fdi', '없음')

        record_text = f"""
        • 모델1 진단: {model1_label}
        • 모델2 위생 상태: {model2_label}
        • 모델3 치아 번호: {model3_tooth}
        """

        # 웹 접근 가능한 전체 이미지 URL 생성
        base_url = "http://192.168.0.19:5000"
        image_path = record.get("original_image_path", "")
        image_url = f"{base_url}{image_path}"

    # Gemini 모델 호출 (current_app에서 가져옴)
    gemini_model = app.extensions['gemini_model']
    chat = gemini_model.start_chat()

    prompt = f"""
    다음은 환자의 최근 치과 진단 기록입니다:\n{record_text}\n\n
    환자가 다음과 같은 질문을 했습니다:\n"{user_message}"\n
    이 질문에 대해 친절하고 정확하게 답변해주세요.
    """

    response = chat.send_message(prompt)
    reply = response.text

    elapsed_time = round(time.time() - start_time, 2)
    app.logger.info(f"[⏱️ chatbot_reply] 응답 시간: {elapsed_time}초")

    return jsonify({
        'reply': reply,
        'image_url': image_url,
        'elapsed_time': elapsed_time
    })


# ✅ /api/chat 엔드포인트를 여기로 이동 및 수정
@chatbot_bp.route("/api/chat", methods=["POST"])
def chat_with_gemini_moved(): # 함수 이름 충돌 방지를 위해 변경
    data = request.json
    user_id = data.get("user_id")
    message = data.get("message")

    if not user_id or not message:
        return jsonify({"error": "user_id와 message는 필수입니다."}), 400

    try:
        mongo_client = app.extensions['mongo_client']
        db = mongo_client.db

        # 모든 기록을 최신순으로 가져옴
        records_cursor = db['inference_results'].find({"user_id": user_id}).sort("timestamp", -1)
        records = list(records_cursor)

        system_instruction = ""
        response_image_url = None # 챗봇 응답에 포함될 이미지 URL

        # 1. 사용자 메시지에서 특정 날짜 또는 파일명 파싱
        target_date_match = re.search(r'(\d{4}[년\s.-]?\d{1,2}[월\s.-]?\d{1,2}[일])', message)
        target_filename_match = re.search(r'(\d{14}_web_image\.png|\d{14}_web_image\.jpg)', message)
        
        # 2. 특정 기록을 찾기 위한 변수
        found_specific_record = None
        
        if target_date_match:
            date_str = target_date_match.group(1)
            date_str = date_str.replace('년', '').replace('월', '').replace('일', '').replace(' ', '').replace('.', '-')
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                for record in records:
                    record_timestamp_str = record.get('timestamp')
                    if record_timestamp_str:
                        record_date = datetime.fromisoformat(record_timestamp_str.replace('Z', '+00:00')).date()
                        if record_date == target_date:
                            found_specific_record = record
                            break
            except ValueError:
                pass 
        elif target_filename_match:
            target_filename = target_filename_match.group(1)
            for record in records:
                original_image_filename = os.path.basename(record.get('original_image_path', ''))
                if original_image_filename == target_filename:
                    found_specific_record = record
                    break
        
        # 특정 기록이 발견되면 해당 기록의 이미지 사용
        if found_specific_record:
            image_path_from_db = found_specific_record.get('original_image_path', '')
            if image_path_from_db:
                response_image_url = f"http://192.168.0.19:5000{image_path_from_db}"
            
            # 특정 기록에 대한 상세 요약
            model1_inf = found_specific_record.get('model1_inference_result', {})
            model2_inf = found_specific_record.get('model2_inference_result', {})
            model3_inf = found_specific_record.get('model3_inference_result', {})

            model1_label = model1_inf.get('label', '감지되지 않음')
            model1_confidence = model1_inf.get('confidence', 0.0)
            model2_label = model2_inf.get('label', '감지되지 않음')
            model2_confidence = model2_inf.get('confidence', 0.0)
            model3_tooth = model3_inf.get('tooth_number_fdi', '감지되지 않음')
            model3_confidence = model3_inf.get('confidence', 0.0)

            system_instruction = f"""
            당신은 치과 챗봇입니다. 환자가 요청한 특정 진료 기록 ({found_specific_record.get('timestamp')})에 대한 정보입니다:
            AI 진단 결과:
            - 모델1 (질병): {model1_label} (확신도: {model1_confidence:.1%})
            - 모델2 (위생): {model2_label} (확신도: {model2_confidence:.1%})
            - 모델3 (치아번호): {model3_tooth} (확신도: {model3_confidence:.1%})
            의사 코멘트: {found_specific_record.get('doctor_comment', '없음')}
            이 기록을 바탕으로 환자의 질문에 답변하세요.
            """
            
        elif records:
            # 모든 기록에 대한 요약 생성
            all_records_summary = []
            for i, record in enumerate(records):
                model1_inf = record.get('model1_inference_result', {})
                model2_inf = record.get('model2_inference_result', {})
                model3_inf = record.get('model3_inference_result', {})

                model1_label = model1_inf.get('label', '감지되지 않음')
                model1_confidence = model1_inf.get('confidence', 0.0)

                model2_label = model2_inf.get('label', '감지되지 않음')
                model2_confidence = model2_inf.get('confidence', 0.0)

                model3_tooth = model3_inf.get('tooth_number_fdi', '감지되지 않음')
                model3_confidence = model3_inf.get('confidence', 0.0)
                
                record_summary = f"""
                --- 진단 기록 #{len(records) - i} (날짜: {record.get('timestamp')}) ---
                AI 진단 결과:
                - 모델1 (질병): {model1_label} (확신도: {model1_confidence:.1%})
                - 모델2 (위생): {model2_label} (확신도: {model2_confidence:.1%})
                - 모델3 (치아번호): {model3_tooth} (확신도: {model3_confidence:.1%})
                의사 코멘트: {record.get('doctor_comment', '없음')}
                """
                all_records_summary.append(record_summary)

            # 특정 요청이 없으면 가장 최신 기록의 이미지 URL 사용
            latest_record = records[0]
            image_path_from_db = latest_record.get('original_image_path', '')
            if image_path_from_db:
                response_image_url = f"http://192.168.0.19:5000{image_path_from_db}"

            system_instruction = f"""
            당신은 치과 챗봇입니다. 아래 환자의 총 {len(records)}건의 진료 기록을 바탕으로 질문에 답변하세요.
            제공된 기록은 최신순입니다. 필요하다면 모든 기록을 참조하여 답변하세요.
            총 진료 기록:
            {"\n".join(all_records_summary)}
            """
        else:
            if "진료" in message:
                return jsonify({"response": "진료 기록이 없습니다. 먼저 등록해 주세요."})
            system_instruction = "당신은 치과 챗봇입니다. 일반적인 정보만 제공하며 진단은 하지 않습니다."

        # Gemini 모델 호출 (current_app에서 가져옴)
        gemini_model = app.extensions['gemini_model']
        chat = gemini_model.start_chat(history=[
            {"role": "user", "parts": [system_instruction]}
        ])
        response = chat.send_message(message)
        response_text = response.text

        return jsonify({"response": response_text, "image_url": response_image_url})

    except Exception as e:
        app.logger.error(f"Gemini 오류: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500