import bcrypt
from flask import Blueprint, request, jsonify
from models.model import db, User # db와 User 모델 임포트

# Blueprint 생성
auth_bp = Blueprint('auth', __name__)

# 아이디 중복 확인 라우트
@auth_bp.route('/check-username', methods=['GET'])
def check_username_duplicate():
    username = request.args.get('username')
    if not username:
        return jsonify({"message": "Username parameter is required"}), 400

    user = User.query.filter_by(username=username).first()
    if user:
        return jsonify({"exists": True, "message": "이미 사용 중인 아이디입니다."}), 200
    else:
        return jsonify({"exists": False, "message": "사용 가능한 아이디입니다."}), 200

# 회원가입 라우트
@auth_bp.route('/register', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    name = data.get('name')
    gender = data.get('gender')
    birth = data.get('birth')
    phone = data.get('phone')
    address = data.get('address', '')  # 없으면 빈 문자열로 기본값

    print(f"DEBUG: Signup request received for username: {username}")

    if not all([username, password, name, gender, birth, phone]):
        return jsonify({"message": "모든 필드를 입력해야 합니다."}), 400

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"message": "이미 사용 중인 아이디입니다."}), 409

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    new_user = User(
        username=username,
        password=hashed_pw.decode('utf-8'),
        name=name,
        gender=gender,
        birth=birth,
        phone=phone,
        address=address,
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        print(f"DEBUG: User '{username}' registered successfully.")
        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Error registering user '{username}': {str(e)}")
        return jsonify({"message": "Error registering user", "error": str(e)}), 500


# 로그인 라우트
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "gender": user.gender,
                "birth": user.birth,
                "phone": user.phone,
                "address": user.address
            }
        }), 200
    return jsonify({"message": "Invalid credentials"}), 401

# 회원 탈퇴 라우트
@auth_bp.route('/delete_account', methods=['DELETE'])
def delete_account():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "아이디와 비밀번호를 모두 입력해주세요."}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({"message": "아이디 또는 비밀번호가 잘못되었습니다."}), 401

    try:
        db.session.delete(user)
        db.session.commit()
        print(f"✅ 탈퇴 완료: {username}")
        return jsonify({"message": "회원 탈퇴가 완료되었습니다."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"❌ 탈퇴 실패: {e}")
        return jsonify({"message": "회원 탈퇴 중 오류가 발생했습니다.", "error": str(e)}), 500