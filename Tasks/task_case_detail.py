from Pages.page_case_detail import CaseDetailPage


class CaseDetailTask:
    def __init__(self, driver):
        self.page = CaseDetailPage(driver)

    def go_to_case_list(self):
        self.page.go_to_casebox()
        self.page.wait_until_casebox_loaded()

    def search_case(self, keyword: str):
        self.page.search_case(keyword)
        self.page.wait_until_search_results_loaded()

    def open_case(self, case_id: str):
        self.page.open_case_from_list(case_id)
        self.page.wait_until_detail_loaded()

    def launch_checkpoint(self):
        original_handle, new_handle = self.page.click_checkpoint()
        return original_handle, new_handle
