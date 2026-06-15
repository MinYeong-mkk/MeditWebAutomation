from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from Config.config import HEADLESS, BROWSER


def create_driver():
    if BROWSER.lower() != 'chrome':
        raise ValueError(f'Unsupported browser: {BROWSER}')

    options = Options()
    options.add_argument('--start-maximized')
    options.add_argument('--disable-notifications')

    if HEADLESS:
        options.add_argument('--headless=new')
        options.add_argument('--window-size=1920,1080')

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    driver.implicitly_wait(3)
    return driver
