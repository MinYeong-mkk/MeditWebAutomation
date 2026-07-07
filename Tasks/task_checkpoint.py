import itertools
import time

from selenium.common.exceptions import TimeoutException

from Pages.page_checkpoint import CheckpointPage
from Utils.image_utils import (
    UPDATE_BASELINES,
    capture_element_image,
    load_baseline_image,
    save_baseline,
)
from Utils.image_matcher import IMAGE_MATCH_THRESHOLD, find_best_image_match
from Utils.pdf_report_validator import PdfReportValidator
from Utils.report_builder import ReportBuilder


MAX_EXHAUSTIVE_IMAGE_ASSIGNMENT = 8

# ============================================================
# Tooth Number Mapping
# ============================================================

TOOTH_NUMBERS_BY_SCAN_TYPE = {
    "maxilla": [
        "11", "12", "13", "14", "15", "16", "17", "18",
        "21", "22", "23", "24", "25", "26", "27", "28",
    ],

    "mandible": [
        "31", "32", "33", "34", "35", "36", "37", "38",
        "41", "42", "43", "44", "45", "46", "47", "48",
    ],

    "both": [
        "11", "12", "13", "14", "15", "16", "17", "18",
        "21", "22", "23", "24", "25", "26", "27", "28",
        "31", "32", "33", "34", "35", "36", "37", "38",
        "41", "42", "43", "44", "45", "46", "47", "48",
    ],
}


class CheckpointTask:
    def __init__(self, driver):
        self.page = CheckpointPage(driver)
        self._image_failures: list[str] = []

    # ============================================================
    # Entry Flow
    # ============================================================

    def enter_checkpoint_work_area(
        self, 
        entry_flow: str, 
        caries_count: int,
        scan_type: str,
        diagnosis_name: str,
        treatment_name: str,
        baseline_image_paths: list[str] | None = None,
        extras: list | None = None,
    ):
        """CheckPoint 작업 영역 진입"""

        self.page.wait_until_loaded()

        if entry_flow == "direct":
            print("[Checkpoint] Direct diagnosis flow.")

        elif entry_flow == "new_note":
            print("[Checkpoint] New Note flow.")
            self.page.start_new_note()

        elif entry_flow == "edit":
            print("[Checkpoint] Edit preparation flow. Create note first.")

            if self.page.is_note_list_page():
                self.page.start_new_note()
            else:
                print("[Checkpoint] Already in diagnosis page for edit preparation.")

        else:
            raise ValueError(f"Invalid entry_flow value: {entry_flow}")

        self.wait_import_if_displayed()
        
        self.handle_caries_or_manual_capture(
            caries_count=caries_count,
            scan_type=scan_type,
            diagnosis_name=diagnosis_name,
            treatment_name=treatment_name,
            baseline_image_paths=baseline_image_paths,
            extras=extras,
        )

    def enter_edit_flow(
        self,
        caries_count: int,
    ):
        """기존 Note Edit 진입"""

        self.page.wait_until_loaded()

        print("[Checkpoint] Re-enter CheckPoint and open first note for Edit.")
        self.page.open_first_note_for_edit()

        self.wait_import_if_displayed()

        expected_card_count = self.get_expected_card_count(caries_count)

        self.page.wait_until_note_cards_created(expected_card_count)

        actual_card_count = self.page.get_note_card_count()

        print(
            f"[Checkpoint] Edit note card count. "
            f"expected={expected_card_count}, actual={actual_card_count}"
        )

        assert actual_card_count >= expected_card_count, (
            f"Edit note card count mismatch. "
            f"expected_at_least={expected_card_count}, actual={actual_card_count}"
        )

        assert self.page.has_note_card_image(), (
            "Note card image should be visible after edit entry."
        )

    def delete_created_note(self):
        """생성된 Note 삭제"""

        self.page.wait_until_loaded()

        print("[Checkpoint] Delete created note.")
        self.page.delete_first_note()

        print("[Checkpoint] Note deleted.")

    # ============================================================
    # Loading
    # ============================================================

    def wait_import_if_displayed(self):
        """Import loading 표시 시 대기"""

        try:
            print("[Checkpoint] Waiting for import loading...")
            self.page.wait_until_import_started()
            self.page.wait_until_import_completed()
            print("[Checkpoint] Import loading completed.")

        except TimeoutException:
            print("[Checkpoint] Import loading was not displayed or already completed.")

    # ============================================================
    # Diagnosis / Capture
    # ============================================================

    def handle_caries_or_manual_capture(
        self,
        caries_count: int,
        scan_type: str,
        diagnosis_name: str,
        treatment_name: str,
        baseline_image_paths: list[str] | None = None,
        extras: list | None = None,
    ):
        """우식 popup 처리 또는 수동 capture 수행"""

        if caries_count > 0:
            print("[Checkpoint] Caries exists. Accept review popup.")
            self.page.accept_review_popup()

        else:
            print("[Checkpoint] No caries. Start manual capture.")
            self.page.manual_capture()

        expected_card_count = self.get_expected_card_count(caries_count)

        self.page.wait_until_note_cards_created(expected_card_count)

        actual_card_count = self.page.get_note_card_count()

        print(
            f"[Checkpoint] Note card count. "
            f"expected={expected_card_count}, actual={actual_card_count}"
        )

        assert actual_card_count >= expected_card_count, (
            f"Note card count mismatch. "
            f"expected_at_least={expected_card_count}, actual={actual_card_count}"
        )

        assert self.page.has_note_card_image(), (
            "Note card image should be visible after diagnosis/capture."
        )
        # ★ 이미지 유사도 비교 (caries 자동 캡처 케이스만)
        if caries_count > 0 and baseline_image_paths:
            # 썸네일이 실제로 로딩된 뒤 캡처해야 0% 오류 방지
            self.page.wait_until_note_card_images_loaded()
            self._compare_note_card_images(
                baseline_image_paths=baseline_image_paths,
                report=ReportBuilder(extras),
            )

        self.complete_note_forms(
            card_count=expected_card_count,
            scan_type=scan_type,
            diagnosis_name=diagnosis_name,
            treatment_name=treatment_name
        )

    def _compare_note_card_images(
        self,
        baseline_image_paths: list[str],
        report: ReportBuilder,
    ):
        """Note card thumbnail 내부에서 baseline 이미지를 다중 크기로 탐색.

        UPDATE_BASELINES=true 환경변수 시 비교 대신 현재 캡처를 베이스라인으로 저장.
        """
        note_card_elements = self.page.find_all_present(
            self.page.NOTE_CARD_IMAGE, timeout=20
        )

        captured_images = []
        for i, element in enumerate(note_card_elements[:len(baseline_image_paths)]):
            self.page.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
            captured = capture_element_image(self.page.driver, element)
            captured_images.append(captured)

            if UPDATE_BASELINES:
                image_path = baseline_image_paths[i]
                save_baseline(captured, image_path)
                print(f"[Checkpoint] Baseline updated: card={i+1}, path={image_path}")
                report.add_check(
                    f"Baseline updated: Card {i + 1}",
                    image_path,
                )
        if UPDATE_BASELINES:
            return

        baselines = [
            (image_path, load_baseline_image(image_path))
            for image_path in baseline_image_paths
        ]
        scores = [
            [
                find_best_image_match([captured], baseline, color_power=0.0).score
                for _, baseline in baselines
            ]
            for captured in captured_images
        ]

        assignment = self._best_image_assignment(scores)

        for card_index, baseline_index in enumerate(assignment):
            captured = captured_images[card_index]
            image_path, baseline = baselines[baseline_index]
            score = scores[card_index][baseline_index]
            status = "PASS" if score >= IMAGE_MATCH_THRESHOLD else "FAIL"

            print(
                f"[Checkpoint] Image comparison card={card_index+1}, "
                f"baseline={image_path}, score={score:.2%}, "
                f"threshold={IMAGE_MATCH_THRESHOLD:.0%}, status={status}"
            )
            report.add_image_result(
                title=f"Card {card_index + 1} similarity",
                score=score,
                threshold=IMAGE_MATCH_THRESHOLD,
                expected_image=baseline,
                actual_image=captured,
                details=f"(baseline {image_path})",
            )

            if score < IMAGE_MATCH_THRESHOLD:
                self._image_failures.append(
                    f"card={card_index+1}, baseline={image_path}, "
                    f"score={score:.2%}, "
                    f"threshold={IMAGE_MATCH_THRESHOLD:.0%}"
                )

    def _best_image_assignment(self, scores: list[list[float]]) -> list[int]:
        """카드 순서가 바뀌어도 전체 유사도가 가장 높은 baseline 매칭을 선택."""
        card_count = len(scores)
        baseline_count = len(scores[0]) if scores else 0

        if card_count == 0 or baseline_count == 0:
            return []

        if card_count <= MAX_EXHAUSTIVE_IMAGE_ASSIGNMENT:
            best_assignment = None
            best_total = -1.0
            for assignment in itertools.permutations(range(baseline_count), card_count):
                total = sum(scores[card_index][baseline_index] for card_index, baseline_index in enumerate(assignment))
                if total > best_total:
                    best_total = total
                    best_assignment = assignment
            return list(best_assignment)

        remaining = set(range(baseline_count))
        assignment = []
        for row in scores:
            best_baseline = max(remaining, key=lambda baseline_index: row[baseline_index])
            assignment.append(best_baseline)
            remaining.remove(best_baseline)
        return assignment

    def get_expected_card_count(self, caries_count: int) -> int:
        """기대 Note 개수 계산"""

        if caries_count > 0:
            return caries_count

        return 1
    
    def complete_note_forms(
        self,
        card_count: int,
        scan_type: str,
        diagnosis_name: str,
        treatment_name: str
    ):
        """Note별 치아 번호 / Diagnosis / Treatment 입력"""

        tooth_numbers = TOOTH_NUMBERS_BY_SCAN_TYPE[scan_type]

        if card_count > len(tooth_numbers):
            raise ValueError(
                f"Not enough tooth numbers. "
                f"scan_type={scan_type}, "
                f"card_count={card_count}, "
                f"tooth_numbers={len(tooth_numbers)}"
            )

        for index in range(card_count):
            print(f"[Checkpoint] Fill note form. index={index + 1}/{card_count}")

            tooth_number = tooth_numbers[index]

            self.page.select_note_card_by_index(index)

            print(f"[Checkpoint] Select tooth number: {tooth_number}")
            self.page.select_tooth_number(tooth_number)

            print(f"[Checkpoint] Select diagnosis: {diagnosis_name}")
            self.page.select_diagnosis(diagnosis_name)

            print(f"[Checkpoint] Select treatment: {treatment_name}")
            self.page.select_treatment(treatment_name)

            self.page.wait_after_note_form_input()
        
        # 마지막 Note 입력값 저장 트리거
        self.page.blur_active_element()
        self.page.wait_after_note_form_input()

        if card_count > 1:
            self.page.select_note_card_by_index(0)
            self.page.wait_after_note_form_input()

    # ============================================================
    # Data Tree Verification
    # ============================================================

    def verify_scan_type_in_tree(self, scan_type: str):
        """Scan type별 Data Tree 검증"""

        maxilla_visible = self.page.is_maxilla_visible()
        mandible_visible = self.page.is_mandible_visible()

        if scan_type == "maxilla":
            assert maxilla_visible is True, "Maxilla should be visible."
            assert mandible_visible is False, "Mandible should not be visible."

        elif scan_type == "mandible":
            assert mandible_visible is True, "Mandible should be visible."
            assert maxilla_visible is False, "Maxilla should not be visible."

        elif scan_type == "both":
            assert self.page.has_maxilla_tree_item() is True, "Maxilla should be present."
            assert self.page.has_mandible_tree_item() is True, "Mandible should be present."

        else:
            raise ValueError(f"Invalid scan_type: {scan_type}")
        
    def open_preview(self):
        """Preview modal open"""

        if not self.page.is_finalize_enabled():
            print("[Checkpoint] Finalize button is not visible. Open review.")
            self.page.click_first_review_button()
            self.page.wait_after_note_form_input()

        assert self.page.is_finalize_enabled(), (
            "Finalize button should be enabled before opening preview."
        )

        print("[Checkpoint] Open preview.")
        self.page.click_finalize()
    
    # ============================================================
    # Finalize
    # ============================================================

    def verify_preview_modal(
        self,
        scan_type: str,
        expected_note_count: int,
        diagnosis_name: str,
        treatment_name: str
    ):
        """Preview 검증"""

        expected_scan_image_count = {
            "maxilla": 5,
            "mandible": 5,
            "both": 6
        }

        actual_scan_image_count = (
            self.page.get_preview_scan_image_count()
        )
        actual_note_count = self.page.get_preview_note_card_count()

        print(
            f"[Checkpoint] Preview scan image count. "
            f"expected={expected_scan_image_count[scan_type]}, "
            f"actual={actual_scan_image_count}"
        )

        assert actual_scan_image_count == (
            expected_scan_image_count[scan_type]
        )
        assert actual_note_count >= expected_note_count, (
            "Preview note count mismatch. "
            f"expected_at_least={expected_note_count}, actual={actual_note_count}"
        )

        assert self.page.is_text_displayed(diagnosis_name)
        assert self.page.is_text_displayed(treatment_name)

        report_name = self.page.get_report_name_value()

        print(f"[Checkpoint] Report name: {report_name}")

        assert report_name.strip() != ""

    def complete_signature(
        self,
        doctor_name: str = "AutomationDoctor"
    ):
        """Doctor / Signature 입력"""

        print(f"[Checkpoint] Enter doctor name: {doctor_name}")

        self.page.enter_doctor_name(doctor_name)

        print("[Checkpoint] Open signature modal.")
        self.page.open_signature_modal()

        print("[Checkpoint] Draw signature.")
        self.page.draw_signature_dot()

        print("[Checkpoint] Add signature.")
        self.page.click_signature_add()

    def finalize_report(self):
        """Preview Finalize 수행"""

        assert self.page.is_preview_finalize_enabled(), (
            "Preview Finalize button should be enabled before click."
        )

        print("[Checkpoint] Click preview Finalize.")
        self.page.click_preview_finalize()

        print("[Checkpoint] Preview Finalize clicked.")

    def assert_no_image_failures(self):
        """누적된 이미지 유사도 실패를 TC 마지막에 일괄 assert."""
        if self._image_failures:
            failures = self._image_failures[:]
            self._image_failures.clear()
            raise AssertionError(
                "Image similarity too low.\n" + "\n".join(failures)
            )

    def validate_pdf_report(
        self,
        expected_texts: list[str],
        expected_image_paths: list[str] | None = None,
        extras: list | None = None,
    ):
        """PDF 검증 서비스로 위임한다."""
        validator = PdfReportValidator(
            page=self.page,
            report=ReportBuilder(extras),
        )
        return validator.validate(expected_texts, expected_image_paths)
