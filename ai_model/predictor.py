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
n_labels = 10 # 모델이 예측하는 클래스 수 (배경 포함)
model = smp.UnetPlusPlus(
    encoder_name='efficientnet-b7',
    encoder_weights='imagenet',
    classes=n_labels,
    activation=None # 로짓(logits)을 직접 출력하도록 None 설정
)
model_path = os.path.join(os.path.dirname(__file__), 'disease_model_saved_weight.pt')
model.load_state_dict(torch.load(model_path, map_location=device))
model.to(device)
model.eval()

# ✅ 모델 파일 이름 추출
BACKEND_MODEL_NAME = os.path.basename(model_path)

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

def predict_overlayed_image(pil_img: Image.Image) -> Tuple[Image.Image, List[List[int]], float, str]:
    """
    PIL 이미지를 받아서 예측된 마스크, 병변 좌표, 백엔드 모델의 추론 신뢰도, 그리고 모델 이름을 반환합니다.
    신뢰도는 감지된 병변 픽셀들의 평균 예측 확률입니다.

    :param pil_img: 원본 이미지 (PIL.Image)
    :return: (덧씌운 이미지, 병변 좌표 리스트, 백엔드 모델 신뢰도, 모델 이름)
    """
    original_img_resized = pil_img.resize((224, 224)).convert('RGB') # 원본 보존 및 리사이즈
    input_tensor = transform(pil_img).unsqueeze(0).to(device)

    with torch.no_grad():
        # 모델 출력은 로짓(logits) 형태
        output_logits = model(input_tensor)[0].cpu().numpy() # Shape: (n_labels, H, W)
        
        # 로짓에 소프트맥스 적용하여 확률로 변환
        # dim=0은 클래스 차원에 대해 소프트맥스를 적용함을 의미
        probabilities = torch.softmax(torch.from_numpy(output_logits), dim=0).numpy() # Shape: (n_labels, H, W)
        
        # 각 픽셀에 대해 가장 높은 확률을 가진 클래스 ID 선택
        pred_mask = np.argmax(output_logits, axis=0) # Shape: (H, W)
        print("예측된 마스크 고유값:", np.unique(pred_mask))

    # RGB 마스크 이미지 생성
    color_mask = np.zeros((224, 224, 3), dtype=np.uint8)
    for class_id, color in PALETTE.items():
        color_mask[pred_mask == class_id] = color
    color_mask_img = Image.fromarray(color_mask)

    # 오버레이 이미지 생성
    overlay = Image.blend(original_img_resized, color_mask_img, alpha=0.5)

    # 병변 좌표 추출 (배경 클래스(0) 제외)
    lesion_coords = np.column_stack(np.where(pred_mask > 0)) # shape: (N, 2) (y, x)
    lesion_points = lesion_coords.tolist() # (y, x) 순서

    # 백엔드 모델의 추론 신뢰도 계산
    backend_model_confidence = 0.0
    if lesion_coords.shape[0] > 0:
        # 감지된 병변 픽셀들의 예측된 클래스에 대한 확률을 수집
        lesion_pixel_confidences = []
        for y, x in lesion_coords:
            predicted_class_id = pred_mask[y, x]
            if predicted_class_id > 0: # 배경이 아닌 병변 클래스에 대해서만
                lesion_pixel_confidences.append(probabilities[predicted_class_id, y, x])
        
        if lesion_pixel_confidences:
            backend_model_confidence = np.mean(lesion_pixel_confidences)
        else:
            backend_model_confidence = 0.0 # 병변 픽셀이 없거나 모두 배경으로 분류된 경우

    # 시각화 (개발용)
    if os.environ.get("FLASK_DEBUG") == "1":
        plt.figure(figsize=(10, 5))
        plt.subplot(1, 3, 1)
        plt.imshow(original_img_resized)
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

    # 덧씌운 이미지, 병변 좌표 리스트, 백엔드 모델 신뢰도, 그리고 모델 이름 반환
    return overlay, lesion_points, float(backend_model_confidence), BACKEND_MODEL_NAME