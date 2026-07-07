from dataclasses import dataclass

import cv2
import numpy as np


IMAGE_MATCH_THRESHOLD = 0.60


@dataclass(frozen=True)
class ImageMatchResult:
    score: float
    source_index: int | None
    matched_image: np.ndarray | None

    @property
    def passed(self) -> bool:
        return self.score >= IMAGE_MATCH_THRESHOLD


def _masked_color_similarity(
    expected: np.ndarray,
    actual: np.ndarray,
    mask: np.ndarray,
) -> float:
    """마스크 영역의 색상 차이를 0~1 유사도로 변환한다."""
    mask_bool = mask > 0
    if not np.any(mask_bool):
        return 0.0

    diff = np.abs(
        expected.astype(np.float32) - actual.astype(np.float32)
    )
    mean_diff = float(diff[mask_bool].mean())
    return max(0.0, 1.0 - (mean_diff / 255.0))


def _content_crop(image: np.ndarray) -> np.ndarray | None:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mask = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)[1]
    coords = cv2.findNonZero(mask)
    if coords is None:
        return None

    x, y, width, height = cv2.boundingRect(coords)
    crop = image[y:y + height, x:x + width]
    return crop if crop.size else None


def _global_content_similarity(
    expected: np.ndarray,
    actual: np.ndarray,
) -> float:
    """PDF embedded 이미지처럼 후보 전체가 치아 이미지일 때 쓰는 보조 점수."""
    expected_crop = _content_crop(expected)
    actual_crop = _content_crop(actual)
    if expected_crop is None or actual_crop is None:
        return 0.0

    expected_area = expected_crop.shape[0] * expected_crop.shape[1]
    actual_area = actual_crop.shape[0] * actual_crop.shape[1]
    size_score = min(expected_area, actual_area) / max(expected_area, actual_area)
    if size_score < 0.30:
        return 0.0

    size = (256, 256)
    expected_resized = cv2.resize(expected_crop, size, interpolation=cv2.INTER_AREA)
    actual_resized = cv2.resize(actual_crop, size, interpolation=cv2.INTER_AREA)

    expected_gray = cv2.cvtColor(expected_resized, cv2.COLOR_BGR2GRAY)
    actual_gray = cv2.cvtColor(actual_resized, cv2.COLOR_BGR2GRAY)
    texture_score = float(
        cv2.matchTemplate(
            actual_gray,
            expected_gray,
            cv2.TM_CCOEFF_NORMED,
        ).max()
    )

    expected_hsv = cv2.cvtColor(expected_crop, cv2.COLOR_BGR2HSV)
    actual_hsv = cv2.cvtColor(actual_crop, cv2.COLOR_BGR2HSV)
    expected_hist = cv2.calcHist(
        [expected_hsv],
        [0, 1],
        None,
        [30, 32],
        [0, 180, 0, 256],
    )
    actual_hist = cv2.calcHist(
        [actual_hsv],
        [0, 1],
        None,
        [30, 32],
        [0, 180, 0, 256],
    )
    cv2.normalize(expected_hist, expected_hist)
    cv2.normalize(actual_hist, actual_hist)
    color_score = float(
        cv2.compareHist(expected_hist, actual_hist, cv2.HISTCMP_CORREL)
    )

    score = (0.85 * max(texture_score, 0.0)) + (
        0.15 * max(color_score, 0.0)
    )
    return score * size_score


def find_best_image_match(
    source_images: list[np.ndarray],
    baseline: np.ndarray,
    scale_min: float = 0.40,
    scale_max: float = 1.20,
    scale_steps: int = 17,
    color_power: float = 1.0,
    global_similarity: bool = False,
    template_matching: bool = True,
) -> ImageMatchResult:
    """여러 이미지 내부에서 baseline과 가장 비슷한 영역을 다중 크기로 탐색."""
    baseline_gray = cv2.cvtColor(baseline, cv2.COLOR_BGR2GRAY)

    # 검은 배경을 bounding box로 잘라내어 치아 콘텐츠만 템플릿으로 사용.
    # 밝기 패턴만 쓰면 PDF의 흰 배경을 오탐할 수 있어 색상 유사도도 같이 본다.
    mask = cv2.threshold(baseline_gray, 20, 255, cv2.THRESH_BINARY)[1]
    coords = cv2.findNonZero(mask)
    if coords is None:
        return ImageMatchResult(score=0.0, source_index=None, matched_image=None)

    bx, by, bw, bh = cv2.boundingRect(coords)
    template_gray = baseline_gray[by:by + bh, bx:bx + bw]
    template_color = baseline[by:by + bh, bx:bx + bw]
    template_mask = mask[by:by + bh, bx:bx + bw]

    if template_gray.size == 0:
        return ImageMatchResult(score=0.0, source_index=None, matched_image=None)

    best_score = -1.0
    best_source_index = None
    best_crop = None

    for source_index, source in enumerate(source_images):
        if global_similarity:
            global_score = _global_content_similarity(baseline, source)
            if global_score > best_score:
                best_score = global_score
                best_source_index = source_index
                best_crop = _content_crop(source)

        if not template_matching:
            continue

        source_gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)

        for scale in np.linspace(scale_min, scale_max, scale_steps):
            width = max(20, int(template_gray.shape[1] * scale))
            height = max(20, int(template_gray.shape[0] * scale))
            if width > source_gray.shape[1] or height > source_gray.shape[0]:
                continue

            resized_gray = cv2.resize(
                template_gray,
                (width, height),
                interpolation=cv2.INTER_AREA,
            )
            resized_color = cv2.resize(
                template_color,
                (width, height),
                interpolation=cv2.INTER_AREA,
            )
            resized_mask = cv2.resize(
                template_mask,
                (width, height),
                interpolation=cv2.INTER_NEAREST,
            )
            result = cv2.matchTemplate(
                source_gray,
                resized_gray,
                cv2.TM_CCOEFF_NORMED,
            )
            _, texture_score, _, location = cv2.minMaxLoc(result)
            x, y = location
            crop = source[y:y + height, x:x + width]
            color_score = _masked_color_similarity(
                expected=resized_color,
                actual=crop,
                mask=resized_mask,
            )
            score = max(float(texture_score), 0.0) * (color_score ** color_power)

            if score > best_score:
                best_score = score
                best_source_index = source_index
                best_crop = crop.copy()

    return ImageMatchResult(
        score=round(max(best_score, 0.0), 4),
        source_index=best_source_index,
        matched_image=best_crop,
    )
