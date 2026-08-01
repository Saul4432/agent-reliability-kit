"""Pytest integration: run suites inside your normal test run.

Usage in a test module::

    from relkit import ContainsAll, RefusalOnPlantedFailure, load_dataset, run_suite
    from relkit.gate import assert_gate

    def test_agent_quality(relkit_report_dir):
        cases = load_dataset("evals/dataset.yaml")
        result = run_suite("my-agent", my_agent, cases, [ContainsAll(), ...])
        assert_gate(result, baseline_path="evals/baseline.json")

The ``relkit_report_dir`` fixture gives a directory where HTML reports are
written and a terminal summary line is printed at the end of the session.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_written_reports: list[Path] = []


@pytest.fixture()
def relkit_report_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Directory for reliability reports (kept after the run, path printed)."""
    directory = tmp_path_factory.mktemp("relkit-reports")
    _written_reports.append(directory)
    return directory


def pytest_terminal_summary(terminalreporter: object) -> None:  # pragma: no cover - cosmetic
    if _written_reports:
        writer = getattr(terminalreporter, "write_line", print)
        for directory in _written_reports:
            writer(f"[relkit] reliability reports in: {directory}")
