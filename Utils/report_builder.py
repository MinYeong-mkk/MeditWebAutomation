from pytest_html import extras as html_extras

from Utils.image_utils import image_to_base64_src


class ReportBuilder:
    """pytest-html 상세 결과 생성을 한곳에서 담당한다."""

    def __init__(self, extras: list | None):
        self.extras = extras

    def _append(self, content: str) -> None:
        if self.extras is not None:
            self.extras.append(html_extras.html(content))

    def add_test_context(
        self,
        tc_id: str,
        case_name: str,
        entry_flow: str,
        scan_type: str,
        caries_count: int,
    ) -> None:
        self._append(
            "<div style='font-size:13px;padding:6px 0;"
            "border-bottom:1px solid #eee;margin-bottom:8px'>"
            f"<b>TC:</b> {tc_id} &nbsp;|&nbsp; "
            f"<b>Case:</b> {case_name} &nbsp;|&nbsp; "
            f"<b>Flow:</b> {entry_flow} &nbsp;|&nbsp; "
            f"<b>Scan:</b> {scan_type} &nbsp;|&nbsp; "
            f"<b>Caries:</b> {caries_count}</div>"
        )

    def add_validation_scope(self, entry_flow: str, items: list[str]) -> None:
        item_html = "".join(f"<li>{item}</li>" for item in items)
        self._append(
            "<div style='margin:6px 0;font-size:12px'>"
            f"<b>Validation scope: {entry_flow}</b>"
            f"<ul style='margin:5px 0 0 18px'>{item_html}</ul></div>"
        )

    def add_check(self, title: str, description: str) -> None:
        self._append(
            "<div style='margin:4px 0;font-size:12px'>"
            f"<b>{title}</b> → <b style='color:green'>PASS</b><br/>"
            f"<span style='color:#5f6368'>{description}</span></div>"
        )

    def add_error(self, message: str) -> None:
        self._append(
            f"<div style='color:#ea4335;padding:6px'>{message}</div>"
        )

    def add_text_result(self, label: str, text: str, passed: bool) -> None:
        status = "PASS" if passed else "FAIL"
        color = "green" if passed else "red"
        self._append(
            "<div style='margin:3px 0;font-size:12px'>"
            f"{label}: <b>{text}</b> → "
            f"<b style='color:{color}'>{status}</b></div>"
        )

    def add_image_result(
        self,
        title: str,
        score: float,
        threshold: float,
        expected_image,
        actual_image,
        details: str = "",
    ) -> None:
        passed = score >= threshold
        status = "PASS" if passed else "FAIL"
        color = "green" if passed else "red"
        actual_html = (
            f"<img src='{image_to_base64_src(actual_image)}' width='200' "
            "title='Actual match'/>"
            if actual_image is not None else
            "<span style='color:red'>No matching image found</span>"
        )
        detail_html = f" {details}" if details else ""
        self._append(
            "<div style='margin:8px 0'>"
            f"<b>{title}</b><br/>"
            f"Best similarity: {score:.2%} → "
            f"<b style='color:{color}'>{status}</b> "
            f"(threshold {threshold:.0%}){detail_html}<br/>"
            f"<img src='{image_to_base64_src(expected_image)}' width='200' "
            "style='margin-right:8px' title='Expected baseline'/>"
            f"{actual_html}</div>"
        )

    def add_pdf_preview(self, page_image, title: str = "PDF Page 1") -> None:
        self._append(
            f"<div style='margin:6px 0'><b>{title}</b><br/>"
            f"<img src='{image_to_base64_src(page_image)}' "
            "style='max-width:600px;border:1px solid #ddd'/></div>"
        )
