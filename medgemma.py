# pip install accelerate
from transformers import AutoProcessor, AutoModelForImageTextToText
from PIL import Image
import requests
import torch

model_id = "google/medgemma-4b-it"

model = AutoModelForImageTextToText.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
processor = AutoProcessor.from_pretrained(model_id)

# Image attribution: Stillwaterising, CC0, via Wikimedia Commons
# image_url = "https://upload.wikimedia.org/wikipedia/commons/c/c8/Chest_Xray_PA_3-8-2010.png"
image_url = r"C:\Users\sptzk\Desktop\backend0709\images\original\121212_20250721001358441006_web_image.png"
image = Image.open(requests.get(image_url, headers={"User-Agent": "example"}, stream=True).raw)

messages = [
    {
        "role": "system",
        "content": [{"type": "text", "text": "You are an Dentist."}]
    },
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "잇몸 염증 초기, 치석, Describe this Image, and then tell me Korean"},
            {"type": "image", "image": image}
        ]
    }
]

inputs = processor.apply_chat_template(
    messages, add_generation_prompt=True, tokenize=True,
    return_dict=True, return_tensors="pt"
).to(model.device, dtype=torch.bfloat16)

input_len = inputs["input_ids"].shape[-1]

with torch.inference_mode():
    generation = model.generate(**inputs, max_new_tokens=200, do_sample=False)
    generation = generation[0][input_len:]

decoded = processor.decode(generation, skip_special_tokens=True)
print(decoded)
