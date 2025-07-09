# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class DevelopmentConfig:
    DEBUG = True

    # MySQL
    MYSQL_USER = os.getenv('MYSQL_USER')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
    MYSQL_DB = os.getenv('MYSQL_DB')
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@localhost/{MYSQL_DB}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # MongoDB
    MONGO_URI = os.getenv('MONGO_URI')
    MONGO_DB_NAME = os.getenv('MONGO_DB_NAME')

    # 보안 키
    SECRET_KEY = os.getenv('SECRET_KEY') or 'default_fallback_key'

    # 이미지 업로드 경로
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    PROCESSED_UPLOAD_FOLDER = os.path.join(os.getcwd(), 'processed_uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}