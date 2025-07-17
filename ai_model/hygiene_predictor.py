import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from torchvision import transforms
from segmentation_models_pytorch import UnetPlusPlus
import os

# ✅ 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 0703back 경로
MODEL_PATH = os.path.join(BASE_DIR, "model", "hygiene_model_saved_weight.pt")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ✅ 모델 정의 및 로드
model = UnetPlusPlus(
    encoder_name="efficientnet-b7",
    encoder_weights=None,
    in_channels=3,
    classes=10
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
    return transform(pil_img).unsqueeze(0)  # [1, 3, H, W]

# ✅ 후처리 (클래스 → RGBA 컬러맵)
def postprocess(output_tensor, target_size=(224, 224)):
    pred = torch.argmax(output_tensor.squeeze(0), dim=0).cpu().numpy()

    PALETTE = {
        0: (0, 0, 0, 0),            # background - 투명
        1: (255, 182, 193, 128),    # am - light pink
        2: (0, 255, 127, 128),      # cecr - spring green
        3: (30, 144, 255, 128),     # gcr - dodger blue
        4: (255, 255, 0, 128),      # mcr - yellow
        5: (255, 140, 0, 128),      # ortho - dark orange
        6: (128, 0, 128, 128),      # tar1 - purple
        7: (255, 105, 180, 128),    # tar2 - hot pink
        8: (0, 206, 209, 128),      # tar3 - dark turquoise
        9: (105, 105, 105, 128),    # zircr - dim gray
    }

    h, w = pred.shape
    color_mask = np.zeros((h, w, 4), dtype=np.uint8)  # ✅ RGBA

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
