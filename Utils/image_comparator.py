import base64
import io
import os

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

SSIM_THRESHOLD = 0.75

# UPDATE_BASELINES=true 로 실행하면 비교 대신 현재 캡처를 베이스라인으로 저장
UPDATE_BASELINES = os.getenv("UPDATE_BASELINES", "false").lower() == "true"


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


def _preprocess(img: np.ndarray, target_size: tuple[int, int]) -> np.ndarray:
    """그레이스케일 변환 + CLAHE 정규화"""
    resized = cv2.resize(img, target_size, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def compare_images(img_captured: np.ndarray, img_baseline: np.ndarray) -> float:
    """SSIM 유사도 반환 (0.0 ~ 1.0)"""
    h, w = img_baseline.shape[:2]
    proc_captured = _preprocess(img_captured, (w, h))
    proc_baseline = _preprocess(img_baseline, (w, h))

    score, _ = ssim(proc_captured, proc_baseline, full=True)
    return round(score, 4)


def is_similar(score: float) -> bool:
    return score >= SSIM_THRESHOLD


def save_baseline(image: np.ndarray, image_path: str) -> None:
    """캡처 이미지를 베이스라인으로 저장"""
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    cv2.imwrite(image_path, image)


def image_to_base64_src(img: np.ndarray) -> str:
    """numpy array → HTML img src용 base64 문자열"""
    _, buffer = cv2.imencode(".png", img)
    b64 = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/png;base64,{b64}"
