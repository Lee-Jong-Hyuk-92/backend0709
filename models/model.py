# C:\Users\sptzk\Desktop\backend0709-1\models\model.py
from flask_sqlalchemy import SQLAlchemy
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# .env 파일 로드 (MongoDB URI와 DB 이름을 가져오기 위함)
load_dotenv()

db = SQLAlchemy()

# MongoDB 클라이언트 클래스
class MongoDBClient:
    def __init__(self, uri=None, db_name=None):
        # app.py에서 초기화 시 uri와 db_name을 받도록 변경
        # 또는 함수 내에서 current_app.config를 사용하여 동적으로 가져오기
        mongo_uri = uri or os.getenv('MONGO_URI')
        mongo_db_name = db_name or os.getenv('MONGO_DB_NAME')

        if not mongo_uri or not mongo_db_name:
            raise ValueError("MongoDB URI or DB name not set in environment variables or config.")

        self.client = MongoClient(mongo_uri)
        self.db = self.client[mongo_db_name]
        # 기존 inference_results 컬렉션은 유지
        self.inference_results_collection = self.db.inference_results

    def insert_result(self, result_data):
        """
        기존에 'inference_results' 컬렉션에 데이터를 삽입하던 메서드.
        """
        try:
            self.inference_results_collection.insert_one(result_data)
            print(f"MongoDB 'inference_results'에 문서 삽입 성공.")
        except Exception as e:
            print(f"MongoDB 'inference_results' 문서 삽입 실패: {e}")
            raise # 예외를 다시 발생시켜 상위 호출자에게 알림

    def insert_into_collection(self, collection_name, document):
        """
        지정된 컬렉션에 문서를 삽입하는 새로운 범용 메서드.
        """
        try:
            collection = self.db[collection_name]
            result = collection.insert_one(document)
            print(f"MongoDB '{collection_name}' 컬렉션에 문서 삽입 성공: {result.inserted_id}")
            return result.inserted_id
        except Exception as e:
            print(f"MongoDB '{collection_name}' 문서 삽입 실패: {e}")
            raise # 예외를 다시 발생시켜 상위 호출자에게 알림

    def get_collection(self, collection_name):
        """
        특정 컬렉션 객체를 반환하는 메서드.
        """
        return self.db[collection_name]

    def close(self):
        """
        MongoDB 클라이언트 연결을 닫는 메서드.
        """
        self.client.close()

# ✅ User 모델 정의 (기존과 동일)
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    # ✅ 로그인 응답에서 참조되는 추가 필드들
    name = db.Column(db.String(100))
    gender = db.Column(db.String(10))
    birth = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))

    def __repr__(self):
        return f'<User {self.username}>'