import bcrypt
from flask import Blueprint, request, jsonify
from models.model import db, User, Doctor

auth_bp = Blueprint('auth', __name__)

# ✅ 아이디 중복 체크 (의사/환자 분리)
@auth_bp.route('/check-username', methods=['GET'])
def check_username_duplicate():
    username = request.args.get('username')
    role = request.args.get('role', 'P')  # 기본값: 환자

    if not username:
        return jsonify({"message": "Username parameter is required"}), 400

    if role == 'D':
        user = Doctor.query.filter_by(username=username).first()
    else:
        user = User.query.filter_by(username=username).first()

    if user:
        return jsonify({"exists": True, "message": "이미 사용 중인 아이디입니다."}), 200
    return jsonify({"exists": False, "message": "사용 가능한 아이디입니다."}), 200


# ✅ 회원가입
@auth_bp.route('/register', methods=['POST'])
def signup():
    data = request.get_json()
    role = data.get('role', 'P')  # 기본값: 환자

    username = data.get('username')
    password = data.get('password')
    name = data.get('name')
    gender = data.get('gender')
    birth = data.get('birth')
    phone = data.get('phone')
    address = data.get('address', '')

    if not all([username, password, name, gender, birth, phone]):
        return jsonify({"message": "모든 필드를 입력해야 합니다."}), 400

    Model = Doctor if role == 'D' else User
    existing_user = Model.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"message": "이미 사용 중인 아이디입니다."}), 409

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    new_user = Model(
        username=username,
        password=hashed_pw.decode('utf-8'),
        name=name,
        gender=gender,
        birth=birth,
        phone=phone,
        address=address,
        role=role  # 'P' 또는 'D'
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error registering user", "error": str(e)}), 500


# ✅ 로그인 (role 기반 분기 + 응답에 role 포함)
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    role = data.get('role', 'P')
    username = data.get('username')
    password = data.get('password')

    Model = Doctor if role == 'D' else User
    user = Model.query.filter_by(username=username).first()

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
                "address": user.address,
                "role": user.role  # ✅ Flutter 분기용
            }
        }), 200

    return jsonify({"message": "Invalid credentials"}), 401


# ✅ 회원 탈퇴
@auth_bp.route('/delete_account', methods=['DELETE'])
def delete_account():
    data = request.get_json()
    role = data.get('role', 'P')
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "아이디와 비밀번호를 모두 입력해주세요."}), 400

    Model = Doctor if role == 'D' else User
    user = Model.query.filter_by(username=username).first()

    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({"message": "아이디 또는 비밀번호가 잘못되었습니다."}), 401

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "회원 탈퇴가 완료되었습니다."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "회원 탈퇴 중 오류가 발생했습니다.", "error": str(e)}), 500
