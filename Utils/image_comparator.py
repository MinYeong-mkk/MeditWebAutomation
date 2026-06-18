import base64
import io

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

SSIM_THRESHOLD = 0.85


def capture_element_image(driver, element) -> np.ndarray:
    """Selenium element screenshot → numpy array"""
    png_bytes = element.screenshot_as_png
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def load_baseline_image(image_path: str) -> np.ndarray:
    """baseline 이미지 파일 로드"""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Baseline image not found: {image_path}")
    return img


def compare_images(img_captured: np.ndarray, img_baseline: np.ndarray) -> float:
    """SSIM 유사도 반환 (0.0 ~ 1.0)"""
    # 크기 맞추기 (baseline 기준)
    h, w = img_baseline.shape[:2]
    img_resized = cv2.resize(img_captured, (w, h))

    gray_captured = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
    gray_baseline = cv2.cvtColor(img_baseline, cv2.COLOR_BGR2GRAY)

    score, _ = ssim(gray_captured, gray_baseline, full=True)
    return round(score, 4)


def is_similar(score: float) -> bool:
    return score >= SSIM_THRESHOLD


def image_to_base64_src(img: np.ndarray) -> str:
    """numpy array → HTML img src용 base64 문자열"""
    _, buffer = cv2.imencode(".png", img)
    b64 = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/png;base64,{b64}"