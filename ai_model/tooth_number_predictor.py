import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from torchvision import transforms
from segmentation_models_pytorch import FPN
import os

# ✅ 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 0703back 경로
MODEL_PATH = os.path.join(BASE_DIR, "model", "tooth_number_saved_weight.pt")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ✅ 모델 정의 및 로드
model = FPN(
    encoder_name="efficientnet-b7",
    encoder_weights=None,
    in_channels=3,
    classes=33
)
model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
model.to(DEVICE)
model.eval()

# ✅ 전처리
def preprocess(pil_img, size=(224, 224)):
    transform = transforms.Compose([
        transforms.Resize(size),
        transforms.ToTensor(),
    ])
    return transform(pil_img).unsqueeze(0)  # shape: [1, 3, H, W]

# ✅ 후처리 (배경은 투명)
def postprocess(output_tensor, target_size=(224, 224)):
    pred = torch.argmax(output_tensor.squeeze(0), dim=0).cpu().numpy()  # [H, W]

    # RGBA 팔레트: 0번 클래스는 투명
    PALETTE = {
        0: (0, 0, 0, 0),
        1: (255, 0, 0, 128),
        2: (0, 255, 0, 128),
        3: (0, 0, 255, 128),
        4: (255, 255, 0, 128),
        5: (255, 0, 255, 128),
        6: (0, 255, 255, 128),
        7: (128, 0, 128, 128),
        8: (255, 165, 0, 128),
        9: (128, 128, 128, 128),
        10: (0, 128, 0, 128),
        11: (0, 0, 128, 128),
        12: (139, 0, 0, 128),
        13: (0, 139, 139, 128),
        14: (75, 0, 130, 128),
        15: (220, 20, 60, 128),
        16: (154, 205, 50, 128),
        17: (255, 215, 0, 128),
        18: (0, 191, 255, 128),
        19: (255, 105, 180, 128),
        20: (70, 130, 180, 128),
        21: (160, 82, 45, 128),
        22: (60, 179, 113, 128),
        23: (255, 20, 147, 128),
        24: (47, 79, 79, 128),
        25: (218, 165, 32, 128),
        26: (255, 160, 122, 128),
        27: (199, 21, 133, 128),
        28: (32, 178, 170, 128),
        29: (46, 139, 87, 128),
        30: (123, 104, 238, 128),
        31: (127, 255, 0, 128),
        32: (255, 99, 71, 128)
    }

    h, w = pred.shape
    color_mask = np.zeros((h, w, 4), dtype=np.uint8)
    for class_id, color in PALETTE.items():
        color_mask[pred == class_id] = color

    return Image.fromarray(color_mask, mode="RGBA").resize(target_size)

# ✅ 예측 함수
def predict_mask_and_overlay_only(pil_img, overlay_save_path):
    input_tensor = preprocess(pil_img).to(DEVICE)
    with torch.no_grad():
        output = model(input_tensor)
        output = F.softmax(output, dim=1)

    mask_img = postprocess(output)
    mask_img.save(overlay_save_path)
    return mask_img