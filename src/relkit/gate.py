"""The CI quality gate: thresholds + baseline regression detection.

``assert_gate`` is designed to be called from a pytest test. It fails the
build when (a) any metric's mean score is below its threshold, or (b) any
metric regressed versus the stored baseline beyond ``tolerance``.

Baselines are plain JSON files checked into the repo (pattern: LangGraph's
bench baseline on main + comparison on PR).
"""

from __future__ import annotations

import json
from pathlib import Path

from relkit.models import Regression, SuiteResult


class GateFailure(AssertionError):
    """Raised when the reliability gate fails; message is CI-log friendly."""


def save_baseline(result: SuiteResult, path: str | Path) -> None:
    Path(path).write_text(result.model_dump_json(indent=2), "utf-8")


def load_baseline(path: str | Path) -> SuiteResult:
    return SuiteResult.model_validate(json.loads(Path(path).read_text("utf-8")))


def find_regressions(
    current: SuiteResult,
    baseline: SuiteResult,
    tolerance: float = 0.02,
) -> list[Regression]:
    """Metrics whose mean score dropped more than ``tolerance`` vs baseline."""
    regressions: list[Regression] = []
    for summary in current.summaries:
        base = baseline.summary_for(summary.metric)
        if base is None:
            continue
        delta = summary.mean_score - base.mean_score
        if delta < -tolerance:
            regressions.append(
                Regression(
                    metric=summary.metric,
                    baseline_score=round(base.mean_score, 4),
                    current_score=round(summary.mean_score, 4),
                    delta=round(delta, 4),
                )
            )
    return regressions


def assert_gate(
    result: SuiteResult,
    baseline_path: str | Path | None = None,
    tolerance: float = 0.02,
) -> None:
    """Fail loudly (and readably) when quality drops. Passes silently."""
    failures: list[str] = []

    for summary in result.summaries:
        if summary.mean_score < summary.threshold:
            failures.append(
                f"metric '{summary.metric}': mean {summary.mean_score:.3f} "
                f"< threshold {summary.threshold:.3f}"
            )

    if baseline_path is not None and Path(baseline_path).exists():
        baseline = load_baseline(baseline_path)
        for reg in find_regressions(result, baseline, tolerance):
            failures.append(
                f"metric '{reg.metric}' regressed: {reg.baseline_score:.3f} "
                f"-> {reg.current_score:.3f} (delta {reg.delta:+.3f})"
            )

    if failures:
        details = "\n  - ".join(failures)
        raise GateFailure(
            f"Reliability gate FAILED for suite '{result.suite_name}' "
            f"({len(failures)} problem(s)):\n  - {details}"
        )
