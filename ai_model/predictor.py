import os
import torch
import torchvision.transforms as T
from PIL import Image
import numpy as np
import segmentation_models_pytorch as smp
import matplotlib.pyplot as plt
from typing import Tuple, List

# 디바이스 설정
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 모델 구성
n_labels = 10
model = smp.UnetPlusPlus(
    encoder_name='efficientnet-b7',
    encoder_weights='imagenet',
    classes=n_labels,
    activation=None
)
model_path = os.path.join(os.path.dirname(__file__), 'disease_model_saved_weight.pt')
model.load_state_dict(torch.load(model_path, map_location=device))
model.to(device)
model.eval()

# 이미지 전처리
transform = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
])

# 클래스 ID → RGB 컬러 매핑
PALETTE = {
    0: (0, 0, 0),           # background - black
    1: (255, 0, 0),         # red
    2: (0, 255, 0),         # green
    3: (0, 0, 255),         # blue
    4: (255, 255, 0),       # yellow
    5: (255, 0, 255),       # magenta
    6: (0, 255, 255),       # cyan
    7: (255, 165, 0),       # orange
    8: (128, 0, 128),       # purple
    9: (128, 128, 128),     # gray
}

def predict_overlayed_image(pil_img: Image.Image) -> Tuple[Image.Image, List[List[int]]]:
    """
    PIL 이미지를 받아서 예측된 마스크와 병변 좌표를 반환
    :param pil_img: 원본 이미지 (PIL.Image)
    :return: (덧씌운 이미지, 병변 좌표 리스트)
    """
    original_img = pil_img.resize((224, 224)).convert('RGB')  # 원본 보존용
    input_tensor = transform(pil_img).unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(input_tensor)[0].cpu().numpy()
        pred_mask = np.argmax(output, axis=0)
        print("예측된 마스크 고유값:", np.unique(pred_mask))

    # RGB 마스크 이미지 생성
    color_mask = np.zeros((224, 224, 3), dtype=np.uint8)
    for class_id, color in PALETTE.items():
        color_mask[pred_mask == class_id] = color
    color_mask_img = Image.fromarray(color_mask)

    # 오버레이 이미지 생성
    overlay = Image.blend(original_img, color_mask_img, alpha=0.5)

    # 병변 좌표 추출 (배경 제외)
    lesion_coords = np.column_stack(np.where(pred_mask > 0))  # shape: (N, 2)
    lesion_points = lesion_coords.tolist()  # (y, x) 순서

    # 시각화 (개발용)
    if os.environ.get("FLASK_DEBUG") == "1":
        plt.figure(figsize=(10, 5))
        plt.subplot(1, 3, 1)
        plt.imshow(original_img)
        plt.title("Original")
        plt.axis("off")

        plt.subplot(1, 3, 2)
        plt.imshow(color_mask_img)
        plt.title("Predicted Mask")
        plt.axis("off")

        plt.subplot(1, 3, 3)
        plt.imshow(overlay)
        plt.title("Overlay")
        plt.axis("off")

        plt.tight_layout()
        plt.show()

    return overlay, lesion_points
