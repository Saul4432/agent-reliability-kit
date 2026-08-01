from pathlib import Path

from relkit import ContainsAll, RefusalOnPlantedFailure, render_html, run_suite, write_report
from tests.conftest import bad_agent, good_agent, make_cases

METRICS = [ContainsAll(), RefusalOnPlantedFailure()]


def test_html_report_contains_metrics_and_cases() -> None:
    result = run_suite("intake", good_agent, make_cases(), METRICS)
    html = render_html(result)
    assert "<!doctype html>" in html
    assert "contains_all" in html and "refusal" in html
    assert "quote-web" in html
    assert "planted" in html  # planted failure badge


def test_failing_run_shows_fail_badge() -> None:
    result = run_suite("intake", bad_agent, make_cases(), METRICS)
    html = render_html(result)
    assert "FAIL" in html


def test_output_is_escaped() -> None:
    def xss_agent(user_input: str, tracer: object) -> str:
        return "<script>alert(1)</script> I can't help"

    result = run_suite("intake", xss_agent, make_cases(), METRICS)  # type: ignore[arg-type]
    html = render_html(result)
    assert "<script>alert" not in html


def test_write_report_creates_file(tmp_path: Path) -> None:
    result = run_suite("intake", good_agent, make_cases(), METRICS)
    out = write_report(result, tmp_path / "report.html")
    assert out.exists() and out.read_text("utf-8").startswith("<!doctype html>")
