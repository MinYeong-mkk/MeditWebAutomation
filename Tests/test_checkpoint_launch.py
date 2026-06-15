import pytest

from Tasks.task_case_detail import CaseDetailTask
from Tasks.task_checkpoint import CheckpointTask
from Tasks.task_login import LoginTask


@pytest.mark.checkpoint
def test_open_checkpoint_from_case(driver, base_url, test_account, checkpoint_case_id, checkpoint_case_search_keyword):
    login_task = LoginTask(driver, base_url)
    login_task.login(test_account['email'], test_account['password'])

    case_task = CaseDetailTask(driver)
    case_task.go_to_case_list()
    case_task.search_case(checkpoint_case_search_keyword)
    case_task.open_case(checkpoint_case_id)
    original_handle, _ = case_task.launch_checkpoint()

    checkpoint_task = CheckpointTask(driver)
    checkpoint_task.page.wait_until_loaded()

    assert 'cloud.meditlink.com' in driver.current_url.lower()

    driver.close()
    driver.switch_to.window(original_handle)
