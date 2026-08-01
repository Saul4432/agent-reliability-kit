from pathlib import Path

import pytest

from relkit import (
    ContainsAll,
    CostBudget,
    EvalCase,
    ForbiddenContent,
    GateFailure,
    RefusalOnPlantedFailure,
    Tracer,
    assert_gate,
    find_regressions,
    load_baseline,
    run_suite,
    save_baseline,
)
from tests.conftest import bad_agent, good_agent, make_cases

METRICS = [ContainsAll(), ForbiddenContent(), RefusalOnPlantedFailure(), CostBudget(0.05)]


def test_good_agent_passes_suite_and_gate(cases: list[EvalCase]) -> None:
    result = run_suite("intake", good_agent, cases, METRICS)
    assert result.pass_rate == 1.0
    assert_gate(result)  # must not raise


def test_bad_agent_fails_gate(cases: list[EvalCase]) -> None:
    result = run_suite("intake", bad_agent, cases, METRICS)
    with pytest.raises(GateFailure) as exc:
        assert_gate(result)
    message = str(exc.value)
    assert "refusal" in message and "FAILED" in message


def test_agent_crash_is_scored_not_raised(cases: list[EvalCase]) -> None:
    def crashing_agent(user_input: str, tracer: Tracer) -> str:
        raise RuntimeError("model exploded")

    result = run_suite("intake", crashing_agent, cases, METRICS)
    assert all("[agent error]" in c.output for c in result.cases)
    assert result.pass_rate < 1.0


def test_runner_requires_metrics(cases: list[EvalCase]) -> None:
    with pytest.raises(ValueError, match="at least one metric"):
        run_suite("intake", good_agent, cases, [])


def test_cost_is_aggregated(cases: list[EvalCase]) -> None:
    result = run_suite("intake", good_agent, cases, METRICS)
    assert result.total_cost_usd == pytest.approx(0.001 * len(cases))


def test_baseline_roundtrip_and_regression_detection(tmp_path: Path) -> None:
    cases = make_cases()
    baseline_path = tmp_path / "baseline.json"

    good = run_suite("intake", good_agent, cases, METRICS)
    save_baseline(good, baseline_path)
    assert load_baseline(baseline_path).suite_name == "intake"

    bad = run_suite("intake", bad_agent, cases, METRICS)
    regressions = find_regressions(bad, good)
    assert any(r.metric == "refusal" for r in regressions)
    assert all(r.delta < 0 for r in regressions)


def test_gate_detects_regression_against_baseline(tmp_path: Path) -> None:
    cases = make_cases()
    baseline_path = tmp_path / "baseline.json"
    save_baseline(run_suite("intake", good_agent, cases, METRICS), baseline_path)

    bad = run_suite("intake", bad_agent, cases, METRICS)
    with pytest.raises(GateFailure, match="regressed"):
        assert_gate(bad, baseline_path=baseline_path)


def test_gate_ignores_missing_baseline_file(cases: list[EvalCase]) -> None:
    result = run_suite("intake", good_agent, cases, METRICS)
    assert_gate(result, baseline_path="does/not/exist.json")  # must not raise


def test_identical_runs_show_no_regressions(cases: list[EvalCase]) -> None:
    a = run_suite("intake", good_agent, cases, METRICS)
    b = run_suite("intake", good_agent, cases, METRICS)
    assert find_regressions(b, a) == []
