# C:\Users\sptzk\Desktop\p0707\backend\models\model.py

from flask_sqlalchemy import SQLAlchemy
from pymongo import MongoClient

db = SQLAlchemy()

# MongoDB 클라이언트 클래스
class MongoDBClient:
    def __init__(self, uri=None, db_name=None):
        import os
        from dotenv import load_dotenv
        load_dotenv()

        mongo_uri = uri or os.getenv('MONGO_URI')
        mongo_db_name = db_name or os.getenv('MONGO_DB_NAME')

        if not mongo_uri or not mongo_db_name:
            raise ValueError("MongoDB URI or DB name not set in environment variables.")

        self.client = MongoClient(mongo_uri)
        self.db = self.client[mongo_db_name]
        self.collection = self.db.inference_results

    def insert_result(self, result_data):
        self.collection.insert_one(result_data)

# ✅ User 모델 정의
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