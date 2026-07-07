import base64

import fitz  # PyMuPDF
import cv2
import numpy as np
import requests


MIN_PDF_IMAGE_WIDTH = 240
MIN_PDF_IMAGE_HEIGHT = 240


def get_pdf_bytes(driver, pdf_element) -> bytes:
    """PDF iframe/embed에서 PDF 바이트를 추출.

    직접 URL(http/https)이면 requests로 다운로드.
    blob: URL이면 JavaScript로 ArrayBuffer를 읽어 변환.
    """
    src = pdf_element.get_attribute("src") or ""

    if not src:
        raise ValueError("PDF 뷰어 엘리먼트에 src 속성이 없습니다.")

    if src.startswith("blob:"):
        script = """
        var callback = arguments[arguments.length - 1];
        fetch(arguments[0])
            .then(function(r) { return r.arrayBuffer(); })
            .then(function(buf) {
                var bytes = new Uint8Array(buf);
                var binary = '';
                for (var i = 0; i < bytes.byteLength; i++) {
                    binary += String.fromCharCode(bytes[i]);
                }
                callback(btoa(binary));
            })
            .catch(function(e) { callback(null); });
        """
        b64 = driver.execute_async_script(script, src)
        if b64 is None:
            raise RuntimeError("blob URL에서 PDF를 가져오지 못했습니다.")
        return base64.b64decode(b64)

    cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
    user_agent = driver.execute_script("return navigator.userAgent")
    resp = requests.get(
        src,
        cookies=cookies,
        headers={"User-Agent": user_agent},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.content


def _decode_pdf_image(image_bytes: bytes) -> np.ndarray | None:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
    if image is None:
        return None

    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

    if image.shape[2] == 3:
        return image

    return None


def extract_pdf_images(
    pdf_bytes: bytes,
    min_width: int = MIN_PDF_IMAGE_WIDTH,
    min_height: int = MIN_PDF_IMAGE_HEIGHT,
) -> list[np.ndarray]:
    """PDF에 embedded된 raster image 후보를 BGR 이미지로 추출."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    seen_xrefs = set()

    try:
        for page in doc:
            for image_info in page.get_images(full=True):
                xref = image_info[0]
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)

                extracted = doc.extract_image(xref)
                image = _decode_pdf_image(extracted.get("image", b""))
                if image is None:
                    continue

                height, width = image.shape[:2]
                if width < min_width or height < min_height:
                    continue

                images.append(image)
    finally:
        doc.close()

    return images


def validate_pdf_text(pdf_bytes: bytes, expected_texts: list[str]) -> dict[str, bool]:
    """PDF 전체 텍스트에서 각 문자열 포함 여부를 반환."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "".join(page.get_text() for page in doc)
    doc.close()
    return {text: text in full_text for text in expected_texts}


def render_pdf_pages(pdf_bytes: bytes, dpi: int = 150) -> list[np.ndarray]:
    """PDF 전체 페이지를 BGR 이미지로 렌더링."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height,
            pix.width,
            pix.n,
        )
        color_code = cv2.COLOR_RGBA2BGR if pix.n == 4 else cv2.COLOR_RGB2BGR
        images.append(cv2.cvtColor(arr, color_code))
    doc.close()
    return images


def recognize_pdf_text(pdf_pages: list[np.ndarray]) -> str:
    """RapidOCR로 렌더링된 PDF 페이지의 텍스트를 인식."""
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR()
    recognized_lines = []
    for page in pdf_pages:
        results, _ = engine(page)
        recognized_lines.extend(
            item[1] for item in (results or [])
            if len(item) > 1 and item[1]
        )
    return "\n".join(recognized_lines)
