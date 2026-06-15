from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from Pages.page_base import BasePage


class CaseDetailPage(BasePage):
    
    CASEBOX_BUTTON = (By.ID, "btn-sidebar-casebox")

    SEARCH_INPUT = (By.ID, "input-search-case")
    SEARCH_BUTTON = (By.ID, "icon-input-search-case")
    SEARCH_CLEAR_BUTTON = (By.ID, "icon-clear-input-search-case")

    DETAIL_TITLE = (By.CSS_SELECTOR, ".detail-title-text")
    CHECKPOINT_ICON = (By.ID, "btn-checkpoint")
    CASE_TABLE_ROW = (By.CSS_SELECTOR, "tr.main-body-tr")

    def go_to_casebox(self):
        self.click(self.CASEBOX_BUTTON)

    def clear_search_input(self):
        if self.is_visible(self.SEARCH_CLEAR_BUTTON, timeout=2):
            self.click(self.SEARCH_CLEAR_BUTTON)
            return

        self.clear_input_by_keyboard(self.SEARCH_INPUT, timeout=5)

    def search_case(self, keyword: str, use_search_button: bool = True):
        self.clear_search_input()
        self.focus_and_type(self.SEARCH_INPUT, keyword, timeout=10)

        if use_search_button:
            self.click(self.SEARCH_BUTTON)
        else:
            element = self.find_visible(self.SEARCH_INPUT)
            element.send_keys(Keys.ENTER)

    def open_case_from_list(self, case_id: str):
        case_locator = (By.ID, f"label-case-name-{case_id}")
        self.click(case_locator)

    def wait_until_casebox_loaded(self):
        self.wait_for_url_contains("/casebox")
        self.wait_until_visible(self.SEARCH_INPUT, timeout=20)

    def wait_until_search_results_loaded(self):
        self.wait_until_visible(self.CASE_TABLE_ROW, timeout=20)

    def wait_until_detail_loaded(self):
        self.wait_for_url_contains("/casebox/detail")
        self.wait_until_visible(self.DETAIL_TITLE, timeout=20)

    def click_checkpoint(self) -> tuple[str, str]:
        original_handle = self.driver.current_window_handle
        existing_handles = list(self.driver.window_handles)

        self.click(self.CHECKPOINT_ICON)

        new_handle = self.wait_for_new_window(existing_handles, timeout=20)
        self.switch_to_window(new_handle)

        return original_handle, new_handle