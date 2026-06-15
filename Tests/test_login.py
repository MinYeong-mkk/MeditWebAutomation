import pytest

from Tasks.task_login import LoginTask


@pytest.mark.smoke
def test_login(driver, base_url, test_account):
    assert test_account['email'], 'Missing email for selected environment'
    assert test_account['password'], 'Missing password for selected environment'

    login_task = LoginTask(driver, base_url)
    login_task.login(test_account['email'], test_account['password'])

    assert 'login' not in driver.current_url.lower(), 'Login appears to have failed.'
