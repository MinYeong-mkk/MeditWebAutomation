from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from Pages.page_login import LoginPage


class LoginTask:
    def __init__(self, driver, base_url):
        self.driver = driver
        self.login_page = LoginPage(driver, base_url)

    def login(self, email, password):
        self.login_page.open()
        self.login_page.wait_until_loaded()
        self.login_page.login(email, password)
        self.login_page.wait_until_login_completed()
        self.dismiss_notice_if_present()

    def dismiss_notice_if_present(self):
        """Dismiss Link notice popup when it appears.

        For the dedicated automation account we click the notice label which
        both checks "do not show again" and closes the popup in one action.
        If the popup does not appear, continue silently.
        """
        try:
            WebDriverWait(self.driver, 3).until(
                EC.visibility_of_element_located(self.login_page.NOTICE_POPUP)
            )
            self.login_page.click(self.login_page.NOTICE_HIDE_LABEL)
            WebDriverWait(self.driver, 5).until(
                EC.invisibility_of_element_located(self.login_page.NOTICE_POPUP)
            )
        except TimeoutException:
            pass
