from dataclasses import dataclass
from pathlib import Path

from Utils.image_utils import load_baseline_image
from Utils.image_matcher import find_best_image_match
from Utils.pdf_validator import (
    extract_pdf_images,
    recognize_pdf_text,
    render_pdf_pages,
    validate_pdf_text,
)
from Utils.report_builder import ReportBuilder


PDF_IMAGE_MATCH_THRESHOLD = 0.55
PDF_ASSIGNMENT_CANDIDATE_LIMIT = 8


@dataclass(frozen=True)
class PdfValidationResult:
    text_results: dict[str, bool]
    image_scores: dict[str, float]


class PdfReportValidator:
    """생성된 PDF의 텍스트와 우식 이미지를 검증한다."""

    def __init__(self, page, report: ReportBuilder):
        self.page = page
        self.report = report

    def validate(
        self,
        expected_texts: list[str],
        expected_image_paths: list[str] | None = None,
    ) -> PdfValidationResult:
        print("[Checkpoint] Waiting for PDF generation...")
        self.page.wait_until_pdf_generated()

        print("[Checkpoint] Downloading PDF content...")
        try:
            pdf_bytes = self.page.get_pdf_bytes()
        except Exception as error:
            message = f"PDF 다운로드 실패: {error}"
            print(f"[Checkpoint] {message}")
            self.report.add_error(message)
            raise

        pdf_pages = render_pdf_pages(pdf_bytes)
        pdf_images = extract_pdf_images(pdf_bytes)
        text_results = self._validate_text(pdf_bytes, pdf_pages, expected_texts)
        image_scores = self._validate_images(
            pdf_images,
            pdf_pages,
            expected_image_paths or [],
        )

        for page_index, page_image in enumerate(pdf_pages, start=1):
            self.report.add_pdf_preview(
                page_image,
                title=f"PDF Page {page_index}",
            )

        text_failures = [
            text for text, found in text_results.items() if not found
        ]
        image_failures = [
            f"{name} (best score={score:.2%})"
            for name, score in image_scores.items()
            if score < PDF_IMAGE_MATCH_THRESHOLD
        ]
        assert not text_failures and not image_failures, (
            "PDF validation failed. "
            f"Missing texts: {text_failures}; "
            f"Unmatched caries images: {image_failures}"
        )

        return PdfValidationResult(
            text_results=text_results,
            image_scores=image_scores,
        )

    def _validate_text(
        self,
        pdf_bytes: bytes,
        pdf_pages: list,
        expected_texts: list[str],
    ) -> dict[str, bool]:
        results = validate_pdf_text(pdf_bytes, expected_texts)
        missing_from_text_layer = [
            text for text, found in results.items() if not found
        ]

        if missing_from_text_layer:
            print(
                "[Checkpoint] PDF text layer is incomplete. Running RapidOCR."
            )
            normalized_ocr_text = " ".join(
                recognize_pdf_text(pdf_pages).lower().split()
            )
            for text in missing_from_text_layer:
                normalized_expected = " ".join(text.lower().split())
                results[text] = normalized_expected in normalized_ocr_text

        for text, found in results.items():
            status = "PASS" if found else "FAIL"
            print(f"[Checkpoint] PDF text '{text}' → {status}")
            self.report.add_text_result("PDF text", text, found)

        return results

    def _validate_images(
        self,
        pdf_images: list,
        pdf_pages: list,
        expected_image_paths: list[str],
    ) -> dict[str, float]:
        scores = {}
        if not expected_image_paths:
            return scores

        if pdf_images:
            image_sources = pdf_images
            source_labels = [
                f"pdf image {i}" for i in range(1, len(pdf_images) + 1)
            ]
        else:
            image_sources = pdf_pages
            source_labels = [
                f"pdf page {i}" for i in range(1, len(pdf_pages) + 1)
            ]

        print(
            f"[Checkpoint] PDF image candidates={len(pdf_images)}, "
            f"rendered pages={len(pdf_pages)}, "
            f"expected caries images={len(expected_image_paths)}"
        )

        baselines = [
            (image_path, load_baseline_image(image_path))
            for image_path in expected_image_paths
        ]
        matches = [
            [
                find_best_image_match(
                    [source],
                    baseline,
                    scale_min=0.55,
                    scale_max=1.50,
                    scale_steps=25,
                    color_power=2.0,
                    global_similarity=True,
                    template_matching=False,
                )
                for source in image_sources
            ]
            for _, baseline in baselines
        ]
        score_matrix = [
            [match.score for match in baseline_matches]
            for baseline_matches in matches
        ]
        assignment = self._best_pdf_image_assignment(score_matrix)

        for index, (image_path, baseline) in enumerate(baselines, start=1):
            assigned_source_index = assignment[index - 1]
            match = (
                matches[index - 1][assigned_source_index]
                if assigned_source_index is not None else None
            )
            score = match.score if match is not None else 0.0
            image_name = Path(image_path).name
            scores[image_name] = score
            source_label = (
                source_labels[assigned_source_index]
                if assigned_source_index is not None else None
            )
            status = "PASS" if score >= PDF_IMAGE_MATCH_THRESHOLD else "FAIL"
            print(
                f"[Checkpoint] PDF caries image {index} ({image_name}) "
                f"best score={score:.2%}, "
                f"source={source_label or '-'}, "
                f"threshold={PDF_IMAGE_MATCH_THRESHOLD:.0%}, status={status}"
            )
            details = (
                f"({source_label})"
                if source_label is not None else
                "(No PDF image candidate found)"
            )
            self.report.add_image_result(
                title=f"PDF caries image {index}: {image_name}",
                score=score,
                threshold=PDF_IMAGE_MATCH_THRESHOLD,
                expected_image=baseline,
                actual_image=match.matched_image if match is not None else None,
                details=details,
            )

        return scores

    def _best_pdf_image_assignment(
        self,
        score_matrix: list[list[float]],
    ) -> list[int | None]:
        """각 baseline에 서로 다른 PDF 후보를 배정한다."""
        if not score_matrix:
            return []

        baseline_count = len(score_matrix)
        source_count = len(score_matrix[0]) if score_matrix[0] else 0
        if source_count == 0:
            return [None] * baseline_count

        candidates_by_baseline = [
            sorted(
                range(source_count),
                key=lambda source_index: row[source_index],
                reverse=True,
            )[:PDF_ASSIGNMENT_CANDIDATE_LIMIT]
            for row in score_matrix
        ]
        baseline_order = sorted(
            range(baseline_count),
            key=lambda baseline_index: len(candidates_by_baseline[baseline_index]),
        )

        best_total = -1.0
        best_assignment = [None] * baseline_count
        current_assignment = [None] * baseline_count

        def search(order_index: int, used_sources: set[int], total: float) -> None:
            nonlocal best_total, best_assignment

            if order_index == len(baseline_order):
                if total > best_total:
                    best_total = total
                    best_assignment = current_assignment.copy()
                return

            baseline_index = baseline_order[order_index]
            for source_index in candidates_by_baseline[baseline_index]:
                if source_index in used_sources:
                    continue
                current_assignment[baseline_index] = source_index
                used_sources.add(source_index)
                search(
                    order_index + 1,
                    used_sources,
                    total + score_matrix[baseline_index][source_index],
                )
                used_sources.remove(source_index)
                current_assignment[baseline_index] = None

        search(order_index=0, used_sources=set(), total=0.0)

        if best_total < 0:
            remaining_sources = set(range(source_count))
            for baseline_index, row in enumerate(score_matrix):
                if not remaining_sources:
                    break
                source_index = max(
                    remaining_sources,
                    key=lambda candidate: row[candidate],
                )
                best_assignment[baseline_index] = source_index
                remaining_sources.remove(source_index)

        return best_assignment
