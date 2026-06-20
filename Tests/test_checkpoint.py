import os
import re
import time

import pytest
from pytest_html import extras as html_extras

from Tasks.task_case_detail import CaseDetailTask
from Tasks.task_checkpoint import CheckpointTask
from Tasks.task_login import LoginTask
from Utils.test_data_loader import load_checkpoint_test_data


def _build_test_data() -> list[dict]:
    data = load_checkpoint_test_data()
    target_tc_id = os.getenv("TC_ID")
    if target_tc_id:
        data = [d for d in data if d["TC_ID"] == target_tc_id]
        if not data:
            raise ValueError(f"TC_ID not found in test data: {target_tc_id}")
    return data


def _extract_case_id_from_url(url: str) -> str:
    match = re.search(r"/casebox/detail/([^/?#]+)", url)
    if not match:
        raise ValueError(f"Case ID could not be extracted from URL: {url}")
    return match.group(1)


@pytest.mark.checkpoint
@pytest.mark.parametrize("case_data", _build_test_data(), ids=lambda d: d["TC_ID"])
def test_checkpoint_case(driver, base_url, test_account, case_data, extras):
    tc_id = case_data["TC_ID"]
    case_name = case_data["case_name"]
    expected_case_id = case_data["case_id"]
    scan_type = case_data["scan_type"]
    entry_flow = case_data["entry_flow"]
    caries_count = case_data["caries_count"]
    baseline_images = case_data["baseline_images"]
    diagnosis_name = case_data["diagnosis_name"]
    treatment_name = case_data["treatment_name"]

    extras.append(html_extras.html(
        f"<div style='font-size:13px; padding:6px 0; border-bottom:1px solid #eee; margin-bottom:8px'>"
        f"<b>TC:</b> {tc_id} &nbsp;|&nbsp; "
        f"<b>Case:</b> {case_name} &nbsp;|&nbsp; "
        f"<b>Flow:</b> {entry_flow} &nbsp;|&nbsp; "
        f"<b>Scan:</b> {scan_type} &nbsp;|&nbsp; "
        f"<b>Caries:</b> {caries_count}"
        f"</div>"
    ))

    # ================================================================
    # Login
    # ================================================================

    login_task = LoginTask(driver, base_url)
    login_task.login(test_account["email"], test_account["password"])

    # ================================================================
    # Case Detail 진입
    # ================================================================

    case_task = CaseDetailTask(driver)
    case_task.go_to_case_list()
    case_task.search_case(case_name)
    case_task.open_case(expected_case_id)

    actual_case_id = _extract_case_id_from_url(driver.current_url)
    assert actual_case_id == expected_case_id, (
        f"Case ID mismatch. expected={expected_case_id}, actual={actual_case_id}"
    )

    if caries_count > 0:
        assert len(baseline_images) == caries_count, (
            f"Baseline image count mismatch. "
            f"caries_count={caries_count}, baseline_images={len(baseline_images)}"
        )

    # ================================================================
    # CheckPoint 진입 → 진단 입력
    # ================================================================

    original_handle, _ = case_task.launch_checkpoint()
    checkpoint_task = CheckpointTask(driver)

    checkpoint_task.enter_checkpoint_work_area(
        entry_flow=entry_flow,
        caries_count=caries_count,
        scan_type=scan_type,
        diagnosis_name=diagnosis_name,
        treatment_name=treatment_name,
        baseline_image_paths=case_data["baseline_image_paths"],
        extras=extras,
    )

    checkpoint_task.verify_scan_type_in_tree(scan_type)

    # ================================================================
    # new_note flow: Preview → Finalize → PDF 검증
    # ================================================================

    if entry_flow == "new_note":
        expected_card_count = checkpoint_task.get_expected_card_count(caries_count)
        checkpoint_task.open_preview()
        checkpoint_task.verify_preview_modal(
            scan_type=scan_type,
            expected_note_count=expected_card_count,
            diagnosis_name=diagnosis_name,
            treatment_name=treatment_name,
        )
        checkpoint_task.complete_signature()
        checkpoint_task.finalize_report()
        checkpoint_task.validate_pdf_report(
            expected_texts=[diagnosis_name, treatment_name],
            extras=extras,
        )

        driver.close()
        driver.switch_to.window(original_handle)

    # ================================================================
    # direct flow: 검증 후 생성된 Note 삭제
    # ================================================================

    elif entry_flow == "direct":
        driver.close()
        driver.switch_to.window(original_handle)

        original_handle, _ = case_task.launch_checkpoint()
        checkpoint_task = CheckpointTask(driver)
        checkpoint_task.delete_created_note()

        driver.close()
        driver.switch_to.window(original_handle)
        time.sleep(2)

    # ================================================================
    # edit flow: Note 생성 후 재진입 → Edit → Finalize → PDF 검증
    # ================================================================

    elif entry_flow == "edit":
        driver.close()
        driver.switch_to.window(original_handle)

        original_handle, _ = case_task.launch_checkpoint()
        checkpoint_task = CheckpointTask(driver)
        checkpoint_task.enter_edit_flow(caries_count=caries_count)

        expected_card_count = checkpoint_task.get_expected_card_count(caries_count)
        checkpoint_task.open_preview()
        checkpoint_task.verify_preview_modal(
            scan_type=scan_type,
            expected_note_count=expected_card_count,
            diagnosis_name=diagnosis_name,
            treatment_name=treatment_name,
        )
        checkpoint_task.complete_signature()
        checkpoint_task.finalize_report()
        checkpoint_task.validate_pdf_report(
            expected_texts=[diagnosis_name, treatment_name],
            extras=extras,
        )

        driver.close()
        driver.switch_to.window(original_handle)

    else:
        raise ValueError(f"Invalid entry_flow: {entry_flow}")
