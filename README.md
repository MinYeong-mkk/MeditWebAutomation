# MeditWebAutomation

이 프로젝트는 아래 흐름을 기준으로 최소 자동화 구조를 갖춘 상태입니다.

1. Medit Link Web 로그인
2. 케이스 상세 진입
3. checkpoint 아이콘 클릭
4. 새 탭으로 열린 Checkpoint 웹 전환
5. New Note 진입까지 자동화

## 실행 예시

```bash
pytest Tests/test_login.py --env=stage
pytest Tests/test_checkpoint_launch.py --env=stage --case-name="TestAutomationCase 001"
```

## 환경 변수

`.env`에 아래 값이 있어야 합니다.

```env
STAGE_EMAIL=your_email
STAGE_PASSWORD=your_password
CHECKPOINT_CASE_NAME=TestAutomationCase 001
```

## 주의

- `page_case_detail.py`, `page_checkpoint.py`의 locator는 실제 DOM에 따라 일부 조정이 필요할 수 있습니다.
- 현재 구조는 네 프로젝트에 필요한 최소 공통 기능만 남긴 버전입니다.


## Checkpoint entry test

The current automation covers this path:

1. Medit Link Web login
2. Dismiss notice popup for the dedicated automation account
3. Open Case Box
4. Search by case keyword
5. Open the target case detail page
6. Launch Checkpoint in a new tab

### Useful pytest options

```bash
pytest Tests/test_checkpoint_launch.py --env=stage --case-search-keyword="automationtest" --case-name="Automation001"
```

- `--case-search-keyword`: keyword entered in the case search field
- `--case-name`: exact case name opened from the search result table
