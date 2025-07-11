import os
from flask import Blueprint, send_from_directory, current_app

static_bp = Blueprint('static', __name__)

# 원본 이미지 제공
@static_bp.route('/uploads/camera/<filename>')
def uploaded_camera_image(filename):
    return send_from_directory(
        os.path.join(current_app.config['UPLOAD_FOLDER'], 'camera'),
        filename
    )

# 마스크 이미지 제공
@static_bp.route('/processed_uploads/camera/<filename>')
def processed_camera_image(filename):
    return send_from_directory(
        os.path.join(current_app.config['PROCESSED_UPLOAD_FOLDER'], 'camera'),
        filename
    )