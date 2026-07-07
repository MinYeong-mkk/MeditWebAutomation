import os
import re

import pytest

from Tasks.task_case_detail import CaseDetailTask
from Tasks.task_checkpoint import CheckpointTask
from Tasks.task_login import LoginTask
from Utils.report_builder import ReportBuilder
from Utils.test_data_loader import load_checkpoint_test_data


FLOW_VALIDATIONS = {
    "new_note": [
        "케이스 및 스캔 타입 확인",
        "새 Note 생성 및 진단/치료 입력",
        "Preview 이미지/진단/치료/리포트명 확인",
        "Doctor 및 Signature 입력",
        "PDF 진단명/치료명 OCR 확인",
        "PDF 우식 이미지 baseline 비교",
    ],
    "direct": [
        "케이스 및 스캔 타입 확인",
        "자동 생성 Note와 우식 이미지 확인",
        "생성된 Note 정리",
    ],
    "edit": [
        "케이스 및 스캔 타입 확인",
        "기존 Note 편집 진입",
        "Preview 이미지/진단/치료/리포트명 확인",
        "Doctor 및 Signature 입력",
        "PDF 진단명/치료명 OCR 확인",
    ],
}


def _close_window_and_switch(driver, target_handle: str) -> None:
    driver.close()
    driver.switch_to.window(target_handle)


def _complete_report_flow(
    task: CheckpointTask,
    report: ReportBuilder,
    scan_type: str,
    caries_count: int,
    diagnosis_name: str,
    treatment_name: str,
    baseline_image_paths: list[str],
    extras: list,
) -> None:
    expected_card_count = task.get_expected_card_count(caries_count)
    task.open_preview()
    task.verify_preview_modal(
        scan_type=scan_type,
        expected_note_count=expected_card_count,
        diagnosis_name=diagnosis_name,
        treatment_name=treatment_name,
    )
    report.add_check(
        "Preview content",
        "Scan images, notes, diagnosis, treatment, and report name matched.",
    )
    task.complete_signature()
    report.add_check(
        "Doctor / Signature",
        "Doctor name and signature were entered successfully.",
    )
    task.finalize_report()
    task.validate_pdf_report(
        expected_texts=[diagnosis_name, treatment_name],
        expected_image_paths=baseline_image_paths,
        extras=extras,
    )


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
    baseline_image_paths = case_data["baseline_image_paths"]
    report = ReportBuilder(extras)

    report.add_test_context(
        tc_id=tc_id,
        case_name=case_name,
        entry_flow=entry_flow,
        scan_type=scan_type,
        caries_count=caries_count,
    )
    report.add_validation_scope(entry_flow, FLOW_VALIDATIONS[entry_flow])

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
    report.add_check(
        "Case identity",
        f"expected={expected_case_id}, actual={actual_case_id}",
    )

    if caries_count > 0:
        assert len(baseline_images) == caries_count, (
            f"Baseline image count mismatch. "
            f"caries_count={caries_count}, baseline_images={len(baseline_images)}"
        )

    # ================================================================
    # CheckPoint 진입 → 진단 입력
    # cp_task 는 이미지 비교 실패를 내부에 누적하므로 변수를 유지해야 함
    # ================================================================

    original_handle, _ = case_task.launch_checkpoint()
    cp_task = CheckpointTask(driver)

    cp_task.enter_checkpoint_work_area(
        entry_flow=entry_flow,
        caries_count=caries_count,
        scan_type=scan_type,
        diagnosis_name=diagnosis_name,
        treatment_name=treatment_name,
        baseline_image_paths=baseline_image_paths,
        extras=extras,
    )

    cp_task.verify_scan_type_in_tree(scan_type)
    report.add_check(
        "Scan data tree",
        f"Expected scan type '{scan_type}' is displayed correctly.",
    )

    # ================================================================
    # new_note flow: Preview → Finalize → PDF 검증
    # ================================================================

    if entry_flow == "new_note":
        _complete_report_flow(
            task=cp_task,
            report=report,
            scan_type=scan_type,
            caries_count=caries_count,
            diagnosis_name=diagnosis_name,
            treatment_name=treatment_name,
            baseline_image_paths=baseline_image_paths,
            extras=extras,
        )
        _close_window_and_switch(driver, original_handle)

    # ================================================================
    # direct flow: 검증 후 생성된 Note 삭제
    # ================================================================

    elif entry_flow == "direct":
        _close_window_and_switch(driver, original_handle)

        original_handle, _ = case_task.launch_checkpoint()
        cp_task_cleanup = CheckpointTask(driver)
        cp_task_cleanup.delete_created_note()
        report.add_check(
            "Direct flow cleanup",
            "The Note created by the direct flow was deleted.",
        )
        _close_window_and_switch(driver, original_handle)

    # ================================================================
    # edit flow: Note 생성 후 재진입 → Edit → Finalize → PDF 검증
    # ================================================================

    elif entry_flow == "edit":
        _close_window_and_switch(driver, original_handle)

        original_handle, _ = case_task.launch_checkpoint()
        cp_task_edit = CheckpointTask(driver)
        cp_task_edit.enter_edit_flow(caries_count=caries_count)
        report.add_check(
            "Edit flow entry",
            "The existing Note was reopened in edit mode.",
        )
        _complete_report_flow(
            task=cp_task_edit,
            report=report,
            scan_type=scan_type,
            caries_count=caries_count,
            diagnosis_name=diagnosis_name,
            treatment_name=treatment_name,
            baseline_image_paths=baseline_image_paths,
            extras=extras,
        )
        _close_window_and_switch(driver, original_handle)

    else:
        raise ValueError(f"Invalid entry_flow: {entry_flow}")

    # ================================================================
    # 이미지 유사도 실패 최종 판정
    # (이미지 fail 이 있어도 위 flow 전체를 완료한 뒤 여기서 한 번에 실패 처리)
    # ================================================================

    cp_task.assert_no_image_failures()
