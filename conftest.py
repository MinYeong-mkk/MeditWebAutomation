import os

import pytest

from Config.config import get_env_config
from TestBase.webDriverSetup import create_driver


SCREENSHOT_DIR = 'screenshots'


def pytest_addoption(parser):
    parser.addoption(
        '--env',
        action='store',
        default='stage',
        help='Environment: dev, stage, oper',
    )
    parser.addoption(
        '--case-id',
        action='store',
        default=os.getenv('CHECKPOINT_CASE_ID', '6383880'),
        help='Case ID used for checkpoint automation.',
    )
    parser.addoption(
        '--case-search-keyword',
        action='store',
        default=os.getenv('CHECKPOINT_CASE_SEARCH_KEYWORD', 'automationtest'),
        help='Keyword used in the case list search box.',
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f'rep_{rep.when}', rep)


@pytest.fixture(scope='session')
def env(request):
    return request.config.getoption('--env')


@pytest.fixture(scope='session')
def env_config(env):
    return get_env_config(env)


@pytest.fixture(scope='session')
def base_url(env_config):
    return env_config['base_url']


@pytest.fixture(scope='session')
def test_account(env_config):
    return {
        'email': env_config['email'],
        'password': env_config['password'],
    }


@pytest.fixture(scope='session')
def checkpoint_case_id(request):
    return request.config.getoption('--case-id')


@pytest.fixture(scope='session')
def checkpoint_case_search_keyword(request):
    return request.config.getoption('--case-search-keyword')


@pytest.fixture(scope='function')
def driver(request):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    driver = create_driver()
    yield driver

    if getattr(request.node, 'rep_call', None) and request.node.rep_call.failed:
        filename = f"{request.node.name}.png"
        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, filename))

    driver.quit()
