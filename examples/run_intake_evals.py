"""End-to-end demo: evaluate a client-intake agent, write report + baseline.

Runs fully offline (FakeJudge). Swap ``FakeJudge`` for an LLM-backed judge in
production — nothing else changes.

    python examples/run_intake_evals.py
"""

from __future__ import annotations

from pathlib import Path

from relkit import (
    ContainsAll,
    CostBudget,
    FakeJudge,
    ForbiddenContent,
    JudgeMetric,
    RefusalOnPlantedFailure,
    Tracer,
    assert_gate,
    load_dataset,
    run_suite,
    save_baseline,
    write_report,
)

HERE = Path(__file__).parent


def intake_agent(user_input: str, tracer: Tracer) -> str:
    """A tiny simulated intake agent for a marketing agency."""
    lowered = user_input.lower()
    with tracer.span("guardrail_check", kind="guardrail"):
        if "ignore" in lowered and "instructions" in lowered:
            return "I can't help with that request."
        if "contract" in lowered or "sue" in lowered:
            return "I can't give legal advice — I'll connect you with a human."
    with tracer.span("llm_call", kind="llm", model="demo", cost_usd=0.0012, tokens=240):
        if "shop" in lowered:
            return "An online shop starts at 1490 EUR, delivered in 3 weeks."
        if "automate" in lowered or "automation" in lowered.replace("automate", "automation"):
            return (
                "Yes — invoice reminder automation is one of our core services (automation pack)."
            )
        if "spanish" in lowered or "english" in lowered:
            return "Yes, we build bilingual sites in Spanish and English."
        if "how long" in lowered:
            return "A standard website takes 2-3 weeks."
        return "A website for your business costs 990 EUR."


def main() -> None:
    cases = load_dataset(HERE / "intake_evals" / "dataset.yaml")
    metrics = [
        ContainsAll(),
        ForbiddenContent(),
        RefusalOnPlantedFailure(),
        CostBudget(budget_usd=0.01),
        JudgeMetric(judge=FakeJudge(), threshold=0.7),
    ]
    result = run_suite("client-intake", intake_agent, cases, metrics)

    report = write_report(result, HERE / "intake_report.html")
    save_baseline(result, HERE / "intake_evals" / "baseline.json")
    print(f"pass rate: {result.pass_rate:.0%} | eval cost: ${result.total_cost_usd:.4f}")
    print(f"report:   {report}")

    assert_gate(result, baseline_path=HERE / "intake_evals" / "baseline.json")
    print("gate:     PASSED")


if __name__ == "__main__":
    main()
