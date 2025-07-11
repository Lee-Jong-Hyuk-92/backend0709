import bcrypt
from flask import Blueprint, request, jsonify
from models.model import db, User, Doctor
# import time # ✅ time 모듈 임포트 제거 (더 이상 필요 없음)

auth_bp = Blueprint('auth', __name__)

# ✅ 아이디 중복 체크 (의사/환자 통합 검사)
@auth_bp.route('/check-username', methods=['GET'])
def check_username_duplicate():
    register_id = request.args.get('username')

    if not register_id:
        return jsonify({"message": "Username parameter is required"}), 400

    # User 테이블에서 register_id 중복 확인
    user_exists = User.query.filter_by(register_id=register_id).first()
    # Doctor 테이블에서 register_id 중복 확인
    doctor_exists = Doctor.query.filter_by(register_id=register_id).first()

    if user_exists or doctor_exists:
        return jsonify({"exists": True, "message": "이미 사용 중인 아이디입니다."}), 200
    return jsonify({"exists": False, "message": "사용 가능한 아이디입니다."}), 200


# ✅ 회원가입 (통합 아이디 중복 검사 및 DB 자동 ID 생성)
@auth_bp.route('/register', methods=['POST'])
def signup():
    data = request.get_json()
    role = data.get('role', 'P')

    register_id = data.get('username')
    password = data.get('password')
    name = data.get('name')
    gender = data.get('gender')
    birth = data.get('birth')
    phone = data.get('phone')

    if not all([register_id, password, name, gender, birth, phone]):
        return jsonify({"message": "모든 필드를 입력해야 합니다."}), 400

    # User 테이블과 Doctor 테이블 모두에서 register_id 중복 확인
    user_exists = User.query.filter_by(register_id=register_id).first()
    doctor_exists = Doctor.query.filter_by(register_id=register_id).first()

    if user_exists or doctor_exists:
        return jsonify({"message": "이미 사용 중인 아이디입니다. 다른 아이디를 사용해주세요."}), 409

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # ✅ 수동 ID 생성 로직 제거, DB의 AUTO_INCREMENT에 맡김
    if role == 'D':
        new_user = Doctor(
            # doctor_id는 DB에서 자동 생성
            register_id=register_id,
            password=hashed_pw.decode('utf-8'),
            name=name,
            gender=gender,
            birth=birth,
            phone=phone,
            role=role
        )
    else: # role == 'P'
        new_user = User(
            # user_id는 DB에서 자동 생성
            register_id=register_id,
            password=hashed_pw.decode('utf-8'),
            name=name,
            gender=gender,
            birth=birth,
            phone=phone,
            role=role
        )

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error registering user", "error": str(e)}), 500


# ✅ 로그인
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    role = data.get('role', 'P')
    register_id = data.get('register_id')
    password = data.get('password')

    Model = Doctor if role == 'D' else User
    user = Model.query.filter_by(register_id=register_id).first()

    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        user_id_to_return = user.doctor_id if role == 'D' else user.user_id
        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user_id_to_return,
                "register_id": user.register_id,
                "name": user.name,
                "gender": user.gender,
                "birth": user.birth,
                "phone": user.phone,
                "role": user.role
            }
        }), 200

    return jsonify({"message": "Invalid credentials"}), 401


# ✅ 회원 탈퇴
@auth_bp.route('/delete_account', methods=['DELETE'])
def delete_account():
    data = request.get_json()
    role = data.get('role', 'P')
    register_id = data.get('username')
    password = data.get('password')

    if not register_id or not password:
        return jsonify({"message": "아이디와 비밀번호를 모두 입력해주세요."}), 400

    Model = Doctor if role == 'D' else User
    user = Model.query.filter_by(register_id=register_id).first()

    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({"message": "아이디 또는 비밀번호가 잘못되었습니다."}), 401

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "회원 탈퇴가 완료되었습니다."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "회원 탈퇴 중 오류가 발생했습니다.", "error": str(e)}), 500
