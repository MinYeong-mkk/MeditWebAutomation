import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from Pages.page_base import BasePage
from Utils.pdf_validator import get_pdf_bytes as _get_pdf_bytes


class CheckpointPage(BasePage):

    # ============================================================
    # URL / Page
    # ============================================================

    CHECKPOINT_URL_KEYWORD = "cloud.meditlink.com"

    # ============================================================
    # Note List
    # ============================================================

    # New Note 버튼
    NEW_NOTE_BUTTON = (
        By.XPATH,
        "//button[.//span[normalize-space()='New Note'] or normalize-space()='New Note']"
    )

    # Note List 첫번째 Note > Edit & Direct Flow
    FIRST_NOTE_CARD = (
        By.XPATH,
        "(//div[contains(@class,'scroll-area')]//button[@aria-checked])[1]"
    )

    # 첫 번째 Note kebab 버튼
    NOTE_KEBAB_BUTTON = (
        By.XPATH,
        "(//div[contains(@class,'scroll-area')]//button[@aria-checked]"
        "/following-sibling::button[1])[1]"
    )

    # Edit 버튼
    EDIT_BUTTON = (
        By.XPATH,
        "//button[.//span[normalize-space()='Edit'] or normalize-space()='Edit']"
    )

    # Delete 버튼
    DELETE_BUTTON = (
        By.XPATH,
        "//button[.//span[normalize-space()='Delete'] or normalize-space()='Delete']"
    )

    # Preview 영역
    PREVIEW_AREA = (
        By.XPATH,
        "//*[contains(normalize-space(),'Preview')]"
    )

    # ============================================================
    # Diagnosis / Loading
    # ============================================================

    # Import loading text
    IMPORT_PROGRESS_TEXT = (
        By.XPATH,
        "//*[contains(normalize-space(), 'Importing data')]"
    )

    # Review popup
    REVIEW_POPUP = (
        By.XPATH,
        "//*[contains(normalize-space(), 'List areas for consultation') "
        "or contains(normalize-space(), 'List areas for review')]"
    )

    # Review popup Yes 버튼
    REVIEW_YES_BUTTON = (
        By.XPATH,
        "//*[contains(normalize-space(), 'List areas for consultation') "
        "or contains(normalize-space(), 'List areas for review')]"
        "/ancestor::*[contains(@class,'snackbar')][1]"
        "//button[.//*[normalize-space()='Yes'] or normalize-space()='Yes']"
    )

    # Finalize 버튼
    FINALIZE_BUTTON = (
        By.XPATH,
        "//button[.//span[normalize-space()='Finalize']]"
    )

    CLICK_TO_REVIEW_BUTTON = (
        By.XPATH,
        "//*[normalize-space()='Click to review']"
    )

    # Capture toolbar 버튼
    CAPTURE_TOOLBAR_BUTTON = (
        By.XPATH,
        "//button[.//*[local-name()='use' and contains(@*[local-name()='href'], 'Capture')]]"
    )

    # Capture mode 내부 Capture 버튼
    CAPTURE_CONFIRM_BUTTON = (
        By.XPATH,
        "//button[.//span[normalize-space()='Capture']]"
    )

    # ============================================================
    # Note Thumbnail
    # ============================================================

    # Note 썸네일 이미지
    NOTE_CARD_IMAGE = (
        By.XPATH,
        "//div[contains(@class,'scroll-area')]//div[.//img and .//button]//img"
    )

    # ============================================================
    # Diagnosis Form
    # ============================================================

    # Diagnosis dropdown input
    DIAGNOSIS_DROPDOWN = (
        By.XPATH,
        "//input[@placeholder='Select diagnosis*']"
    )

    # Treatment dropdown input
    TREATMENT_DROPDOWN = (
        By.XPATH,
        "//input[@placeholder='Select treatment*']"
    )

    # ============================================================
    # Data Tree
    # ============================================================

    # Maxilla tree item
    MAXILLA_TREE_ITEM = (
        By.XPATH,
        "//span[normalize-space()='Maxilla']"
    )

    # Mandible tree item
    MANDIBLE_TREE_ITEM = (
        By.XPATH,
        "//span[normalize-space()='Mandible']"
    )

    # ============================================================
    # Preview
    # ============================================================

    # Preview scan images
    PREVIEW_SCAN_IMAGES = (
        By.XPATH,
        "//img[contains(@alt, 'DiagnosisOverviewImage')]"
    )

    # Preview note cards
    PREVIEW_NOTE_CARDS = (
        By.XPATH,
        "//div[contains(@class,'scroll-area')]"
        "//span[normalize-space()='Diagnosis Explanation']"
    )

    PREVIEW_FINALIZE_BUTTON = (
        By.XPATH,
        "//input[@placeholder='Note title']"
        "/ancestor::*[.//button[.//span[normalize-space()='Finalize']]][1]"
        "//button[.//span[normalize-space()='Finalize']]"
    )

    REPORT_NAME_INPUT = (
        By.XPATH,
        "//input[@placeholder='Note title']"
    )

    DOCTOR_NAME_INPUT = (
        By.XPATH,
        "//input[@placeholder='Dr. name']"
    )

    SIGNATURE_BUTTON = (
        By.XPATH,
        "//span[normalize-space()='Signature']"
    )

    SIGNATURE_CANVAS = (
        By.XPATH,
         "//span[normalize-space()='Sign here']/ancestor::div[contains(@class,'flex-box')]//canvas"
    )

    SIGNATURE_CLEAR_BUTTON = (
        By.XPATH,
        "//button[.//span[normalize-space()='Clear']]"
    )

    SIGNATURE_ADD_BUTTON = (
        By.XPATH,
        "//button[.//span[normalize-space()='Add']]"
    )

    SIGNATURE_CANCEL_BUTTON = (
        By.XPATH,
        "//button[.//span[normalize-space()='Cancel']]"
    )

    # ============================================================
    # PDF Report
    # ============================================================

    PDF_VIEWER = (
        By.XPATH,
        "//iframe[contains(@src, '.pdf')] | //embed[contains(@src, '.pdf')]"
    )

    # ============================================================
    # Page Load
    # ============================================================

    def wait_until_loaded(self):
        """CheckPoint URL 대기 + 초기 UI 렌더링 대기"""
        self.wait_for_url_contains(self.CHECKPOINT_URL_KEYWORD, timeout=30)
        # URL 도달 후 앱이 실제로 화면을 렌더링할 때까지 대기
        WebDriverWait(self.driver, 30).until(
            lambda d: (
                d.find_elements(*self.NEW_NOTE_BUTTON)
                or d.find_elements(*self.FIRST_NOTE_CARD)
                or d.find_elements(*self.CAPTURE_TOOLBAR_BUTTON)
            )
        )

    def has_new_note_button(self) -> bool:
        """New Note 버튼 표시 여부"""
        return self.is_visible(self.NEW_NOTE_BUTTON, timeout=3)

    def has_first_note_card(self) -> bool:
        """첫 번째 Note 표시 여부"""
        return self.is_visible(self.FIRST_NOTE_CARD, timeout=3)

    def is_note_list_page(self) -> bool:
        """Note list 화면 여부"""
        return self.has_new_note_button() or self.has_first_note_card()

    # ============================================================
    # Loading / Popup
    # ============================================================

    def wait_until_import_started(self):
        """Import loading 시작 대기"""
        self.wait_until_visible(self.IMPORT_PROGRESS_TEXT, timeout=20)

    def wait_until_import_completed(self):
        """Import loading 종료 대기"""
        self.wait_until_invisible(self.IMPORT_PROGRESS_TEXT, timeout=180)

    def accept_review_popup(self):
        """Review popup Yes 클릭"""
        self.click(self.REVIEW_YES_BUTTON, timeout=60)
        self.wait_until_invisible(self.REVIEW_POPUP, timeout=15)

    # ============================================================
    # Note List Action
    # ============================================================

    def start_new_note(self):
        """New Note 클릭"""
        self.click(self.NEW_NOTE_BUTTON, timeout=30)

    def select_first_note(self):
        """첫 번째 Note 선택"""
        self.wait_until_visible(self.FIRST_NOTE_CARD, timeout=20)
        self.click(self.FIRST_NOTE_CARD)

    def wait_until_preview_loaded(self):
        """Preview / Edit 표시 대기"""
        self.wait_until_visible(self.PREVIEW_AREA, timeout=30)
        self.wait_until_visible(self.EDIT_BUTTON, timeout=30)

    def open_first_note_for_edit(self):
        """첫 번째 Note Edit 진입"""
        self.select_first_note()
        self.wait_until_preview_loaded()
        self.click_edit()

    def click_edit(self):
        """Edit 클릭"""
        self.click(self.EDIT_BUTTON)

    def delete_first_note(self):
        """첫 번째 Note 삭제"""

        self.wait_until_visible(self.FIRST_NOTE_CARD, timeout=30)

        self.click(self.NOTE_KEBAB_BUTTON)

        self.wait_until_visible(self.DELETE_BUTTON, timeout=10)
        self.click(self.DELETE_BUTTON)

        print("[Checkpoint] Waiting for note deletion...")
        self.wait_until_invisible(self.FIRST_NOTE_CARD, timeout=15)

    # ============================================================
    # Diagnosis Action
    # ============================================================

    def manual_capture(self):
        """수동 Capture 수행"""
        self.click(self.CAPTURE_TOOLBAR_BUTTON, timeout=30)
        self.wait_until_visible(self.CAPTURE_CONFIRM_BUTTON, timeout=30)
        self.click(self.CAPTURE_CONFIRM_BUTTON)
    
    def select_note_card_by_index(self, index: int):
        """Note 선택 by index"""

        cards = self.find_all_present(self.NOTE_CARD_IMAGE, timeout=20)
        cards[index].click()

    def select_tooth_number(self, tooth_number: str):
        """치아 번호 선택"""

        tooth = (
            By.XPATH,
            f"//*[local-name()='g' and (@id='{tooth_number}' or @data-name='ToothArch_{tooth_number}')]"
        )

        self.wait_until_visible(tooth, timeout=10)
        self.click(tooth)

    def select_diagnosis(self, diagnosis_name: str):
        """Diagnosis 선택"""

        self.click(self.DIAGNOSIS_DROPDOWN)

        option = (
            By.XPATH,
            f"//button[.//span[normalize-space()='{diagnosis_name}']]"
        )

        self.wait_until_visible(option, timeout=10)
        self.click(option)


    def select_treatment(self, treatment_name: str):
        """Treatment 선택"""

        self.click(self.TREATMENT_DROPDOWN)

        option = (
            By.XPATH,
            f"//button[.//span[normalize-space()='{treatment_name}']]"
        )

        self.wait_until_visible(option, timeout=10)
        self.click(option)

    def wait_after_note_form_input(self):
        """Note form 입력 후 반영 대기"""
        time.sleep(0.3)

    # ============================================================
    # Note Verification
    # ============================================================

    def get_note_card_count(self) -> int:
        """Note 썸네일 개수 반환"""
        images = self.find_all_present(self.NOTE_CARD_IMAGE, timeout=20)
        return len(images)

    def wait_until_note_cards_created(self, expected_count: int):
        """Note 썸네일 생성 대기"""

        def image_count_matches(driver):
            images = driver.find_elements(*self.NOTE_CARD_IMAGE)

            print(
                f"[DEBUG] note thumbnail count={len(images)}, "
                f"expected={expected_count}"
            )

            return len(images) >= expected_count

        WebDriverWait(self.driver, 60).until(image_count_matches)

    def has_note_card_image(self) -> bool:
        """Note 썸네일 표시 여부"""
        return self.is_visible(self.NOTE_CARD_IMAGE, timeout=10)

    def wait_until_note_card_images_loaded(self):
        """모든 Note card thumbnail이 실제로 렌더링될 때까지 대기 (naturalWidth > 0)"""
        def all_loaded(driver):
            imgs = driver.find_elements(*self.NOTE_CARD_IMAGE)
            if not imgs:
                return False
            return all(
                driver.execute_script(
                    "return arguments[0].complete && arguments[0].naturalWidth > 0",
                    img,
                )
                for img in imgs
            )
        WebDriverWait(self.driver, 30).until(all_loaded)

    # ============================================================
    # Data Tree Verification
    # ============================================================

    def is_maxilla_visible(self) -> bool:
        """Maxilla 표시 여부"""
        return self.is_visible(self.MAXILLA_TREE_ITEM, timeout=5)

    def is_mandible_visible(self) -> bool:
        """Mandible 표시 여부"""
        return self.is_visible(self.MANDIBLE_TREE_ITEM, timeout=5)

    def has_maxilla_tree_item(self) -> bool:
        """Maxilla tree item DOM 존재 여부"""
        try:
            return self.find_present(self.MAXILLA_TREE_ITEM, timeout=5) is not None
        except Exception:
            return False

    def has_mandible_tree_item(self) -> bool:
        """Mandible tree item DOM 존재 여부"""
        try:
            return self.find_present(self.MANDIBLE_TREE_ITEM, timeout=5) is not None
        except Exception:
            return False
    

    # ============================================================
    # Finalize
    # ============================================================

    def blur_active_element(self):
        """현재 focus 해제"""
        self.driver.execute_script("document.activeElement.blur();")

    def is_finalize_enabled(self) -> bool:
        """Finalize 활성화 여부"""

        try:
            button = self.find_visible_finalize_button(timeout=10)
        except TimeoutException:
            return False

        disabled = button.get_attribute("disabled")
        aria_disabled = button.get_attribute("aria-disabled")
        class_name = button.get_attribute("class")

        print(
            f"[DEBUG] finalize state. "
            f"disabled={disabled}, aria_disabled={aria_disabled}, class={class_name}"
        )

        return disabled is None and aria_disabled != "true"

    def find_visible_finalize_button(self, timeout: int = 10):
        """화면에 표시된 Finalize 버튼 반환"""
        WebDriverWait(self.driver, timeout).until(
            lambda driver: self._has_visible_finalize_button_after_scroll(driver)
        )
        for button in self.driver.find_elements(*self.FINALIZE_BUTTON):
            if button.is_displayed():
                return button
        raise TimeoutException("Visible Finalize button was not found.")

    def _has_visible_finalize_button_after_scroll(self, driver) -> bool:
        if any(
            button.is_displayed()
            for button in driver.find_elements(*self.FINALIZE_BUTTON)
        ):
            return True

        driver.execute_script(
            """
            for (const element of document.querySelectorAll('*')) {
                if (element.scrollHeight > element.clientHeight) {
                    element.scrollTop = element.scrollHeight;
                }
            }
            """
        )
        return any(
            button.is_displayed()
            for button in driver.find_elements(*self.FINALIZE_BUTTON)
        )

    def click_finalize(self):
        """Finalize 클릭"""
        button = self.find_visible_finalize_button(timeout=10)
        self.scroll_to_element(button)
        try:
            button.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", button)

    def click_first_review_button(self):
        """첫 번째 Click to review 버튼 클릭"""
        button = self.find_visible(self.CLICK_TO_REVIEW_BUTTON, timeout=10)
        self.scroll_to_element(button)
        try:
            button.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", button)
    
    def is_preview_finalize_enabled(self) -> bool:
        """Preview Finalize 활성화 여부"""

        button = self.find_visible(self.PREVIEW_FINALIZE_BUTTON, timeout=10)

        disabled = button.get_attribute("disabled")
        aria_disabled = button.get_attribute("aria-disabled")

        print(
            f"[DEBUG] preview finalize state. "
            f"disabled={disabled}, aria_disabled={aria_disabled}"
        )

        return disabled is None and aria_disabled != "true"

    def click_preview_finalize(self):
        """Finalize 클릭"""

        assert self.is_preview_finalize_enabled(), (
            "Preview Finalize button should be enabled before click."
        )

        self.click(self.PREVIEW_FINALIZE_BUTTON)

    def get_report_name_value(self) -> str:
        """Report name value 반환"""

        return self.get_attribute(
            self.REPORT_NAME_INPUT,
            "value"
        )
    
    def enter_doctor_name(self, doctor_name: str):
        """Doctor name 입력"""

        self.enter_text(
            self.DOCTOR_NAME_INPUT,
            doctor_name
        )

    def open_signature_modal(self):
        """Signature modal open"""

        self.click(self.SIGNATURE_BUTTON)

    def draw_signature_dot(self):
        """Signature canvas에 점 입력"""

        canvas = self.find_visible(self.SIGNATURE_CANVAS)

        ActionChains(self.driver)\
            .move_to_element_with_offset(canvas, 10, 10)\
            .click_and_hold()\
            .move_by_offset(1, 1)\
            .release()\
            .perform()
        
    def click_signature_add(self):
        """Signature Add 클릭"""

        self.click(self.SIGNATURE_ADD_BUTTON)

    def get_preview_scan_image_count(self) -> int:
        """Preview scan image 개수 반환"""

        images = self.find_all_present(
            self.PREVIEW_SCAN_IMAGES,
            timeout=20
        )

        return len(images)

    def get_preview_note_card_count(self) -> int:
        """Preview note card 개수 반환"""

        cards = self.find_all_present(
            self.PREVIEW_NOTE_CARDS,
            timeout=20
        )

        return len(cards)

    def is_text_displayed(self, text: str) -> bool:
        """텍스트 표시 여부"""

        locator = (
            By.XPATH,
            f"//*[normalize-space()='{text}' or contains(normalize-space(), '{text}')]"
        )

        return self.is_visible(locator, timeout=10)
    
    # ============================================================
    # PDF Report
    # ============================================================

    def wait_until_pdf_generated(self):
        """PDF 뷰어 표시 대기"""
        self.wait_until_visible(self.PDF_VIEWER, timeout=60)

    def get_pdf_bytes(self) -> bytes:
        """PDF 뷰어(iframe/embed)에서 PDF 바이트를 추출"""
        pdf_element = self.find_visible(self.PDF_VIEWER, timeout=60)
        return _get_pdf_bytes(self.driver, pdf_element)
