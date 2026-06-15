from selenium.webdriver.common.by import By

from Config.config import LOGIN_PATH
from Pages.page_base import BasePage


class LoginPage(BasePage):
    EMAIL_INPUT = (By.ID, 'input-login-id')
    PASSWORD_INPUT = (By.ID, 'input-login-password')
    LOGIN_BUTTON = (By.ID, 'btn-login')
    PROFILE_BUTTON = (By.ID, 'btn-header-profile')

    # Notice & Update popup
    NOTICE_POPUP = (By.ID, 'label-medit-notice')
    NOTICE_HIDE_LABEL = (By.ID, 'checkbox-hide-notice-unchecked')
    NOTICE_CLOSE_BUTTON = (By.ID, 'btn-close-guide')

    def __init__(self, driver, base_url):
        super().__init__(driver)
        self.base_url = base_url

    def open(self):
        super().open(self.base_url + LOGIN_PATH)

    def enter_email(self, email):
        self.enter_text(self.EMAIL_INPUT, email)

    def enter_password(self, password):
        self.enter_text(self.PASSWORD_INPUT, password)

    def submit(self):
        self.click(self.LOGIN_BUTTON)

    def login(self, email, password):
        self.enter_email(email)
        self.enter_password(password)
        self.submit()

    def wait_until_loaded(self):
        self.wait_until_visible(self.EMAIL_INPUT)
        self.wait_until_visible(self.PASSWORD_INPUT)
        self.wait_until_visible(self.LOGIN_BUTTON)

    def wait_until_login_completed(self):
        self.wait.until(lambda d: 'login' not in d.current_url.lower())
        self.wait_until_visible(self.PROFILE_BUTTON)
