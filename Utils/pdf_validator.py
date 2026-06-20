import base64

import fitz  # PyMuPDF
import numpy as np
import cv2
import requests


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


def validate_pdf_text(pdf_bytes: bytes, expected_texts: list[str]) -> dict[str, bool]:
    """PDF 전체 텍스트에서 각 문자열 포함 여부를 반환."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "".join(page.get_text() for page in doc)
    doc.close()
    return {text: text in full_text for text in expected_texts}


def render_pdf_page(pdf_bytes: bytes, page_index: int = 0, dpi: int = 150) -> np.ndarray:
    """PDF 특정 페이지를 numpy 이미지(BGR)로 렌더링."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_index]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    doc.close()

    if arr.shape[2] == 4:
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def extract_embedded_images(pdf_bytes: bytes) -> list[np.ndarray]:
    """PDF에 임베드된 이미지를 numpy 배열 리스트로 반환."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        for img_info in page.get_images():
            xref = img_info[0]
            base_img = doc.extract_image(xref)
            arr = np.frombuffer(base_img["image"], dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                images.append(img)
    doc.close()
    return images
