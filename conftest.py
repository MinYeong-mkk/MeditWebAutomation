import os

import pytest

from Config.config import get_env_config
from TestBase.webDriverSetup import create_driver
from datetime import datetime
from pytest_html import extras as html_extras

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

@pytest.fixture
def extras(request):
    """pytest-html extras fixture — TC별 유사도/이미지/에러 inject"""
    _extras = []
    yield _extras

    # pytest-html이 report에 extras 붙이는 방식
    if hasattr(request.node, "stash"):
        from pytest_html.plugin import extras as stash_key
        request.node.stash[stash_key] = _extras

def pytest_html_report_title(report):
    report.title = "Checkpoint QA Automation Report"


def pytest_configure(config):
    config._metadata = {
        "Project": "Medit Checkpoint",
        "Environment": config.getoption("--env", default="stage"),
        "Executed": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def pytest_html_results_summary(prefix, summary, postfix):
    from pytest_html import extras
    prefix.extend([extras.html("""
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f9f9f9; color: #222; }
        #report-header { background: #fff; border-bottom: 3px solid #1a73e8; padding: 16px 24px; }
        h1 { color: #1a73e8; font-size: 22px; margin: 0; }
        #results-table { border-collapse: collapse; width: 100%; margin-top: 16px; }
        #results-table th {
            background: #1a73e8; color: #fff;
            padding: 10px 14px; text-align: left; font-size: 13px;
        }
        #results-table td { padding: 9px 14px; border-bottom: 1px solid #eee; font-size: 13px; }
        #results-table tr:hover td { background: #f0f6ff; }
        .passed { color: #fff; background: #34a853; border-radius: 4px; padding: 2px 10px; font-weight: 600; }
        .failed { color: #fff; background: #ea4335; border-radius: 4px; padding: 2px 10px; font-weight: 600; }
        .error  { color: #fff; background: #f29900; border-radius: 4px; padding: 2px 10px; font-weight: 600; }
        div.extraHTML { padding: 8px 0; }
        div.extraHTML div { border-left: 3px solid #1a73e8; padding-left: 12px; margin: 6px 0; }
    </style>
    """)])