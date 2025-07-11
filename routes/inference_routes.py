# routes/inference_routes.py

from flask import Blueprint, jsonify, current_app

inference_bp = Blueprint('inference', __name__)

@inference_bp.route('/inference-results', methods=['GET'])
def get_inference_results():
    try:
        mongo_client = current_app.extensions.get('mongo_client')
        if not mongo_client:
            return jsonify({"error": "MongoDB 클라이언트가 초기화되지 않았습니다."}), 500

        # inference_results 컬렉션에서 모든 문서 조회
        collection = mongo_client.get_collection("inference_results")
        documents = list(collection.find())

        # ObjectId를 문자열로 변환
        for doc in documents:
            doc["_id"] = str(doc["_id"])

        return jsonify(documents), 200

    except Exception as e:
        print(f"❌ MongoDB 조회 오류: {e}")
        return jsonify({"error": "MongoDB 조회 중 오류 발생"}), 500