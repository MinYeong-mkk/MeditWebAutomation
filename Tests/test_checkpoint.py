import os
import re
import time

import pytest

from Tasks.task_case_detail import CaseDetailTask
from Tasks.task_checkpoint import CheckpointTask
from Tasks.task_login import LoginTask
from Utils.test_data_loader import load_checkpoint_test_data
from Utils.image_comparator import (
    capture_element_image,
    load_baseline_image,
    compare_images,
    is_similar,
    image_to_base64_src,
    SSIM_THRESHOLD,
)
from pytest_html import extras as html_extras

def extract_case_id_from_url(url: str) -> str:
    """Case detail URL에서 case_id 추출"""

    match = re.search(r"/casebox/detail/([^/?#]+)", url)

    if not match:
        raise ValueError(f"Case ID could not be extracted from URL: {url}")

    return match.group(1)


@pytest.mark.checkpoint
def test_checkpoint_data_driven_all_cases(driver, base_url, test_account, extras):
    """CheckPoint data-driven test"""

    # ============================================================
    # Test Data
    # ============================================================

    test_data_list = load_checkpoint_test_data()

    # TC_ID 환경변수 지정 시 단일 TC만 실행
    target_tc_id = os.getenv("TC_ID")

    if target_tc_id:
        test_data_list = [
            row for row in test_data_list
            if row["TC_ID"] == target_tc_id
        ]

        if not test_data_list:
            raise ValueError(f"TC_ID not found in test data: {target_tc_id}")

    # ============================================================
    # Login
    # ============================================================

    login_task = LoginTask(driver, base_url)
    login_task.login(test_account["email"], test_account["password"])

    case_task = CaseDetailTask(driver)

    # ============================================================
    # Test Execution
    # ============================================================
    tc_failures = []

    for case_data in test_data_list:
        tc_id = case_data["TC_ID"]
        case_name = case_data["case_name"]
        expected_case_id = case_data["case_id"]
        scan_type = case_data["scan_type"]
        entry_flow = case_data["entry_flow"]
        caries_count = case_data["caries_count"]
        #occlusion_count = case_data["occlusion_count"]
        baseline_images = case_data["baseline_images"]
        diagnosis_name= case_data["diagnosis_name"]
        treatment_name= case_data["treatment_name"]

        original_handle = None

        print(f"\n========== Start {tc_id}: {case_name} ==========")

        try:
            # TC 요약 헤더 (리포트 상단)
            extras.append(html_extras.html(
                f"<div style='font-size:13px; padding:6px 0; border-bottom:1px solid #eee; margin-bottom:8px'>"
                f"<b>TC:</b> {tc_id} &nbsp;|&nbsp; "
                f"<b>Case:</b> {case_name} &nbsp;|&nbsp; "
                f"<b>Flow:</b> {entry_flow} &nbsp;|&nbsp; "
                f"<b>Scan:</b> {scan_type} &nbsp;|&nbsp; "
                f"<b>Caries:</b> {caries_count}"
                f"</div>"
            ))
            # ========================================================
            # Case Detail 진입
            # ========================================================

            case_task.go_to_case_list()
            case_task.search_case(case_name)
            case_task.open_case(expected_case_id)

            actual_case_id = extract_case_id_from_url(driver.current_url)

            assert actual_case_id == expected_case_id, (
                f"[{tc_id}] Case ID mismatch. "
                f"expected={expected_case_id}, actual={actual_case_id}"
            )

            # 우식 케이스 기준 이미지 개수 검증
            if caries_count > 0:
                assert len(baseline_images) == caries_count, (
                    f"[{tc_id}] Baseline image count mismatch. "
                    f"caries_count={caries_count}, "
                    f"baseline_images={len(baseline_images)}"
                )

            # ========================================================
            # CheckPoint 진입
            # ========================================================

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

            if entry_flow == "new_note":
                expected_card_count = checkpoint_task.get_expected_card_count(caries_count)
                checkpoint_task.open_preview()
                checkpoint_task.verify_preview_modal(
                    scan_type=scan_type,
                    expected_note_count=expected_card_count,
                    diagnosis_name=diagnosis_name,
                    treatment_name=treatment_name
                )

                checkpoint_task.complete_signature()
                checkpoint_task.finalize_report()

            # ========================================================
            # Branch Log
            # ========================================================

            if scan_type == "mandible":
                print(f"[{tc_id}] Branch: mandible only scenario")

            elif scan_type == "maxilla":
                print(f"[{tc_id}] Branch: maxilla only scenario")

            elif scan_type == "both":
                print(f"[{tc_id}] Branch: both arch scenario")

            else:
                raise ValueError(f"[{tc_id}] Invalid scan_type: {scan_type}")

            if caries_count > 0:
                print(f"[{tc_id}] Caries exists. Count: {caries_count}")
                print(f"[{tc_id}] Baseline images: {baseline_images}")

            else:
                print(f"[{tc_id}] No caries. Skip caries image comparison.")


            print(f"========== Completed {tc_id} ==========\n")

            # ========================================================
            # CheckPoint tab 종료
            # ========================================================

            driver.close()
            driver.switch_to.window(original_handle)

            # ========================================================
            # Direct Flow Cleanup
            # ========================================================

            if entry_flow == "direct":
                print(f"[{tc_id}] Direct flow cleanup: re-enter CheckPoint and delete created note.")

                original_handle, _ = case_task.launch_checkpoint()

                checkpoint_task = CheckpointTask(driver)
                checkpoint_task.delete_created_note()

                driver.close()
                driver.switch_to.window(original_handle)

                time.sleep(2)

            # ========================================================
            # Edit Flow Re-entry
            # ========================================================

            elif entry_flow == "edit":
                print(f"[{tc_id}] Edit flow re-entry start.")

                original_handle, _ = case_task.launch_checkpoint()

                checkpoint_task = CheckpointTask(driver)
                checkpoint_task.enter_edit_flow(
                    caries_count=caries_count
                )

                expected_card_count = checkpoint_task.get_expected_card_count(caries_count)

                checkpoint_task.open_preview()
                
                checkpoint_task.verify_preview_modal(
                    scan_type=scan_type,
                    expected_note_count=expected_card_count,
                    diagnosis_name=diagnosis_name,
                    treatment_name=treatment_name
                )

                checkpoint_task.complete_signature()
                checkpoint_task.finalize_report()

                print(f"[{tc_id}] Edit flow re-entry completed.")

                driver.close()
                driver.switch_to.window(original_handle)
        except Exception as e:   # ← 여기서 잡기
            print(f"[{tc_id}] FAILED: {e}")
            tc_failures.append(f"{tc_id}: {e}")

            # 실패 사유 리포트에 추가
            extras.append(html_extras.html(
                f"<div style='color:#ea4335; background:#fff0f0; border-left:3px solid #ea4335;"
                f"padding:8px 12px; margin:4px 0; font-size:12px; white-space:pre-wrap'>"
                f"<b>FAILED [{tc_id}]</b><br/>{str(e)}"
                f"</div>"
            ))

        finally:
            try:
                # try 블록 안에서 close 못 하고 예외 터진 경우에만 정리
                handles = driver.window_handles
                if original_handle and original_handle in handles and len(handles) > 1:
                    for handle in handles:
                        if handle != original_handle:
                            driver.switch_to.window(handle)
                            driver.close()
                    driver.switch_to.window(original_handle)
            except Exception:
                pass

    # 루프 끝난 후 판정  ← for랑 같은 레벨
    assert not tc_failures, (
        f"\n{len(tc_failures)} TC(s) failed:\n" +
        "\n".join(tc_failures)
    )