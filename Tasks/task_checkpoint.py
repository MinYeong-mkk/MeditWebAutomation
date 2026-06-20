import time

from selenium.common.exceptions import TimeoutException

from Pages.page_checkpoint import CheckpointPage

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
        baseline_image_paths: list[str] | None = None,  # 추가
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
            self.page.wait_until_review_popup_visible()
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
            self._compare_note_card_images(
                baseline_image_paths=baseline_image_paths,
                extras=extras or [],
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
        extras: list,
    ):
        """Note card thumbnail vs baseline 이미지 SSIM 비교.

        UPDATE_BASELINES=true 환경변수 시 비교 대신 현재 캡처를 베이스라인으로 저장.
        """
        from Utils.image_comparator import (
            UPDATE_BASELINES,
            SSIM_THRESHOLD,
            capture_element_image,
            compare_images,
            image_to_base64_src,
            is_similar,
            load_baseline_image,
            save_baseline,
        )
        from pytest_html import extras as html_extras

        note_card_elements = self.page.find_all_present(
            self.page.NOTE_CARD_IMAGE, timeout=20
        )

        failures = []

        for i, (element, image_path) in enumerate(
            zip(note_card_elements, baseline_image_paths)
        ):
            captured = capture_element_image(self.page.driver, element)

            if UPDATE_BASELINES:
                save_baseline(captured, image_path)
                print(f"[Checkpoint] Baseline updated: card={i+1}, path={image_path}")
                if extras is not None:
                    extras.append(html_extras.html(
                        f"<div style='margin:4px 0;color:#1a73e8'>"
                        f"Baseline updated: Card {i+1} → {image_path}"
                        f"</div>"
                    ))
                continue

            baseline = load_baseline_image(image_path)
            score = compare_images(captured, baseline)
            passed = is_similar(score)
            status = "PASS" if passed else "FAIL"
            color = "green" if passed else "red"

            print(
                f"[Checkpoint] Image comparison card={i+1}, "
                f"score={score:.2%}, threshold={SSIM_THRESHOLD:.0%}, status={status}"
            )

            if extras is not None:
                extras.append(html_extras.html(
                    f"<div style='margin:8px 0'>"
                    f"<b>Card {i+1} similarity</b>: {score:.2%} "
                    f"→ <b style='color:{color}'>{status}</b> "
                    f"(threshold {SSIM_THRESHOLD:.0%})<br/>"
                    f"<img src='{image_to_base64_src(captured)}' width='200' "
                    f"style='margin-right:8px' title='Captured'/>"
                    f"<img src='{image_to_base64_src(baseline)}' width='200' "
                    f"title='Baseline'/>"
                    f"</div>"
                ))

            if not passed:
                failures.append(
                    f"card={i+1}, score={score:.2%}, threshold={SSIM_THRESHOLD:.0%}"
                )

        if failures:
            raise AssertionError(
                "Image similarity too low.\n" + "\n".join(failures)
            )

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
            assert maxilla_visible is True, "Maxilla should be visible."
            assert mandible_visible is True, "Mandible should be visible."

        else:
            raise ValueError(f"Invalid scan_type: {scan_type}")
        
    def open_preview(self):
        """Preview modal open"""

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

        print(
            f"[Checkpoint] Preview scan image count. "
            f"expected={expected_scan_image_count[scan_type]}, "
            f"actual={actual_scan_image_count}"
        )

        assert actual_scan_image_count == (
            expected_scan_image_count[scan_type]
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

    def validate_pdf_report(
        self,
        expected_texts: list[str],
        extras: list | None = None,
    ):
        """PDF 생성 후 텍스트 포함 여부를 검증하고 HTML 리포트에 결과를 기록."""
        from Utils.pdf_validator import validate_pdf_text, render_pdf_page
        from Utils.image_comparator import image_to_base64_src
        from pytest_html import extras as html_extras

        print("[Checkpoint] Waiting for PDF generation...")
        self.page.wait_until_pdf_generated()

        print("[Checkpoint] Downloading PDF content...")
        try:
            pdf_bytes = self.page.get_pdf_bytes()
        except Exception as e:
            msg = f"PDF 다운로드 실패: {e}"
            print(f"[Checkpoint] {msg}")
            if extras is not None:
                extras.append(html_extras.html(
                    f"<div style='color:#ea4335;padding:6px'>{msg}</div>"
                ))
            raise

        # ── 텍스트 검증 ──────────────────────────────────────────
        results = validate_pdf_text(pdf_bytes, expected_texts)
        failures = []

        for text, found in results.items():
            status = "PASS" if found else "FAIL"
            color = "green" if found else "red"
            print(f"[Checkpoint] PDF text '{text}' → {status}")
            if extras is not None:
                extras.append(html_extras.html(
                    f"<div style='margin:3px 0;font-size:12px'>"
                    f"PDF text: <b>{text}</b> → "
                    f"<b style='color:{color}'>{status}</b>"
                    f"</div>"
                ))
            if not found:
                failures.append(text)

        # ── PDF 1페이지 썸네일 리포트에 첨부 ──────────────────────
        try:
            page_img = render_pdf_page(pdf_bytes, page_index=0)
            if extras is not None:
                extras.append(html_extras.html(
                    f"<div style='margin:6px 0'>"
                    f"<b>PDF Page 1</b><br/>"
                    f"<img src='{image_to_base64_src(page_img)}' "
                    f"style='max-width:600px;border:1px solid #ddd'/>"
                    f"</div>"
                ))
        except Exception as e:
            print(f"[Checkpoint] PDF page rendering skipped: {e}")

        assert not failures, (
            f"PDF text validation failed. Missing: {failures}"
        )