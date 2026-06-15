from __future__ import annotations

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from Config.config import DEFAULT_TIMEOUT


class BasePage:
    def __init__(self, driver, timeout: int = DEFAULT_TIMEOUT):
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)

    def open(self, url: str):
        self.driver.get(url)

    def wait_for_url_contains(self, partial_url: str, timeout: int | None = None):
        WebDriverWait(self.driver, timeout or self.timeout).until(EC.url_contains(partial_url))

    def wait_for_new_window(self, previous_handles: list[str], timeout: int | None = None) -> str:
        wait = WebDriverWait(self.driver, timeout or self.timeout)
        wait.until(lambda d: len(d.window_handles) > len(previous_handles))
        new_handles = [handle for handle in self.driver.window_handles if handle not in previous_handles]
        if not new_handles:
            raise TimeoutException('New window was not created.')
        return new_handles[0]

    def switch_to_window(self, handle: str):
        self.driver.switch_to.window(handle)

    def close_current_window_and_switch(self, target_handle: str):
        self.driver.close()
        self.driver.switch_to.window(target_handle)

    def find_visible(self, locator, timeout: int | None = None) -> WebElement:
        return WebDriverWait(self.driver, timeout or self.timeout).until(
            EC.visibility_of_element_located(locator)
        )

    def find_present(self, locator, timeout: int | None = None) -> WebElement:
        return WebDriverWait(self.driver, timeout or self.timeout).until(
            EC.presence_of_element_located(locator)
        )

    def find_clickable(self, locator, timeout: int | None = None) -> WebElement:
        return WebDriverWait(self.driver, timeout or self.timeout).until(
            EC.element_to_be_clickable(locator)
        )

    def find_all_present(self, locator, timeout: int | None = None):
        return WebDriverWait(self.driver, timeout or self.timeout).until(
            EC.presence_of_all_elements_located(locator)
        )

    def click(self, locator, timeout: int | None = None):
        element = self.find_clickable(locator, timeout=timeout)
        try:
            element.click()
        except Exception:
            self.driver.execute_script('arguments[0].click();', element)
        return element
    
    def scroll_to_element(self, element: WebElement):
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});",
            element
        )
        return element

    def js_click_element(self, element: WebElement):
        self.scroll_to_element(element)
        self.driver.execute_script("arguments[0].click();", element)
        return element

    def clear_input_by_keyboard(self, locator, timeout: int | None = None):
        element = self.find_visible(locator, timeout=timeout)
        element.click()
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.BACKSPACE)
        return element

    def focus_and_type(self, locator, text: str, timeout: int | None = None):
        element = self.find_visible(locator, timeout=timeout)
        self.scroll_to_element(element)
        ActionChains(self.driver).move_to_element(element).click().perform()
        self.driver.execute_script("arguments[0].focus();", element)
        element.send_keys(text)
        return element

    def enter_text(self, locator, text, clear: bool = True, timeout: int | None = None):
        element = self.find_visible(locator, timeout=timeout)
        if clear:
            element.clear()
        element.send_keys(text)
        return element

    def get_text(self, locator, timeout: int | None = None):
        return self.find_visible(locator, timeout=timeout).text

    def get_attribute(self, locator, name: str, timeout: int | None = None):
        return self.find_present(locator, timeout=timeout).get_attribute(name)

    def is_visible(self, locator, timeout: int | None = None) -> bool:
        try:
            return self.find_visible(locator, timeout=timeout).is_displayed()
        except TimeoutException:
            return False

    def wait_until_invisible(self, locator, timeout: int | None = None):
        WebDriverWait(self.driver, timeout or self.timeout).until(
            EC.invisibility_of_element_located(locator)
        )

    def wait_until_visible(self, locator, timeout: int | None = None):
        self.find_visible(locator, timeout=timeout)

    def wait_until_present(self, locator, timeout: int | None = None):
        self.find_present(locator, timeout=timeout)
