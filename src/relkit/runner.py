"""Suite runner: executes an agent over a dataset and aggregates results.

The agent is any callable ``(input: str, tracer: Tracer) -> str``. The runner
never imports an LLM SDK — model access belongs to the agent under test, which
keeps the kit offline-testable and provider-agnostic.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence

from relkit.metrics.base import Metric
from relkit.models import CaseResult, EvalCase, MetricSummary, SuiteResult
from relkit.tracing import Tracer

AgentFn = Callable[[str, Tracer], str]


def run_suite(
    suite_name: str,
    agent: AgentFn,
    cases: Sequence[EvalCase],
    metrics: Sequence[Metric],
) -> SuiteResult:
    """Run every case through the agent and score it with every metric.

    Agent exceptions are captured as outputs (``[agent error] ...``) instead of
    aborting the suite — a crashing agent is a reliability result, not an
    infrastructure failure.
    """
    if not metrics:
        raise ValueError("run_suite requires at least one metric")

    case_results: list[CaseResult] = []
    total_cost = 0.0

    for case in cases:
        tracer = Tracer()
        start = time.perf_counter()
        try:
            with tracer.span("agent_run", kind="agent", case_id=case.id):
                output = agent(case.input, tracer)
        except Exception as exc:
            output = f"[agent error] {type(exc).__name__}: {exc}"
        latency_ms = (time.perf_counter() - start) * 1000

        metric_results = [m.evaluate(case, output, tracer) for m in metrics]
        total_cost += tracer.total("cost_usd") + sum(m.cost_usd for m in metric_results)
        case_results.append(
            CaseResult(
                case_id=case.id,
                kind=case.kind,
                output=output,
                latency_ms=latency_ms,
                metrics=metric_results,
            )
        )

    summaries = [_summarize(m, case_results) for m in metrics]
    return SuiteResult(
        suite_name=suite_name,
        cases=case_results,
        summaries=summaries,
        total_cost_usd=round(total_cost, 6),
    )


def _summarize(metric: Metric, case_results: Sequence[CaseResult]) -> MetricSummary:
    scores = [r.score for c in case_results for r in c.metrics if r.metric == metric.name]
    passed = [r.passed for c in case_results for r in c.metrics if r.metric == metric.name]
    return MetricSummary(
        metric=metric.name,
        mean_score=sum(scores) / len(scores) if scores else 0.0,
        pass_rate=sum(passed) / len(passed) if passed else 0.0,
        threshold=metric.threshold,
    )
