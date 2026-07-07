import base64
import os

import cv2
import numpy as np


# UPDATE_BASELINES=true 로 실행하면 비교 대신 현재 캡처를 베이스라인으로 저장
UPDATE_BASELINES = os.getenv("UPDATE_BASELINES", "false").lower() == "true"


def capture_element_image(driver, element) -> np.ndarray:
    """Selenium element screenshot을 OpenCV 이미지로 변환."""
    cleanup_script = None
    try:
        cleanup_script = driver.execute_script(
            """
            const img = arguments[0];
            const hidden = [];
            let card = img;
            for (let i = 0; i < 8 && card; i++) {
                if (card.querySelectorAll && card.querySelectorAll('button').length) {
                    break;
                }
                card = card.parentElement;
            }

            const hide = (el) => {
                hidden.push([el, el.style.visibility]);
                el.style.visibility = 'hidden';
            };

            if (card) {
                card.querySelectorAll('button,[role="tooltip"],[aria-live]').forEach(hide);
            }
            document.querySelectorAll('[role="tooltip"]').forEach(hide);

            return hidden;
            """,
            element,
        )
        png_bytes = element.screenshot_as_png
    finally:
        if cleanup_script:
            driver.execute_script(
                """
                for (const item of arguments[0]) {
                    item[0].style.visibility = item[1];
                }
                """,
                cleanup_script,
            )

    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(
            "Element screenshot could not be decoded "
            "(image may not be loaded yet)"
        )
    return image


def load_baseline_image(image_path: str) -> np.ndarray:
    """Baseline 이미지 파일을 로드."""
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Baseline image not found: {image_path}")
    return image


def save_baseline(image: np.ndarray, image_path: str) -> None:
    """이미지를 baseline 파일로 저장."""
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    cv2.imwrite(image_path, image)


def image_to_base64_src(image: np.ndarray) -> str:
    """OpenCV 이미지를 HTML img src용 base64 문자열로 변환."""
    _, buffer = cv2.imencode(".png", image)
    encoded = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/png;base64,{encoded}"
