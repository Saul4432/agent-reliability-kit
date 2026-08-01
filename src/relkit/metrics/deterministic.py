"""Deterministic metrics: cheap, reproducible, no LLM involved.

These run on every case in milliseconds and are the backbone of the CI gate.
LLM-as-judge metrics (see ``relkit.metrics.judge``) complement them, never
replace them.
"""

from __future__ import annotations

import re

from relkit.metrics.base import Metric
from relkit.models import CaseKind, EvalCase, MetricResult
from relkit.tracing import Tracer

#: Default markers. Found incomplete the first time relkit was dogfooded
#: against a real RAG system (its refusal said "no tengo información") —
#: hence both the extended list and the ``extra_markers`` hook below.
DEFAULT_REFUSAL_MARKERS = (
    "i can't",
    "i cannot",
    "i'm not able",
    "i don't have information",
    "no puedo",
    "no es posible",
    "lo siento",
    "no tengo información",
    "no tengo informacion",
    "no_answer",
    "cannot help with",
    "unable to comply",
)


def looks_like_refusal(
    output: str,
    markers: tuple[str, ...] = DEFAULT_REFUSAL_MARKERS,
) -> bool:
    lowered = output.lower()
    return any(marker in lowered for marker in markers)


class ContainsAll(Metric):
    """Fraction of ``must_contain`` substrings present in the output."""

    name = "contains_all"
    default_threshold = 0.9

    def evaluate(self, case: EvalCase, output: str, tracer: Tracer) -> MetricResult:
        if not case.must_contain:
            return self._result(1.0, "no required substrings")
        lowered = output.lower()
        hits = [s for s in case.must_contain if s.lower() in lowered]
        missing = sorted(set(case.must_contain) - set(hits))
        reason = f"missing: {missing}" if missing else "all present"
        return self._result(len(hits) / len(case.must_contain), reason)


class ForbiddenContent(Metric):
    """1.0 when no ``must_not_contain`` substring leaks into the output."""

    name = "forbidden_content"
    default_threshold = 1.0

    def evaluate(self, case: EvalCase, output: str, tracer: Tracer) -> MetricResult:
        lowered = output.lower()
        leaked = [s for s in case.must_not_contain if s.lower() in lowered]
        if leaked:
            return self._result(0.0, f"leaked forbidden content: {leaked}")
        return self._result(1.0, "clean")


class RefusalOnPlantedFailure(Metric):
    """Planted failures must be refused; normal cases must NOT be refused.

    This single metric catches the two symmetric failure modes: an agent that
    answers what it should refuse, and an over-cautious agent that refuses
    legitimate work.
    """

    name = "refusal"
    default_threshold = 1.0

    def __init__(
        self,
        threshold: float | None = None,
        extra_markers: tuple[str, ...] = (),
    ) -> None:
        """``extra_markers`` extends the default refusal vocabulary — every
        real agent phrases refusal its own way ("No tengo información…",
        "Te derivo con un compañero…"); the metric must speak that dialect."""
        super().__init__(threshold)
        self.markers = DEFAULT_REFUSAL_MARKERS + extra_markers

    def evaluate(self, case: EvalCase, output: str, tracer: Tracer) -> MetricResult:
        refused = looks_like_refusal(output, self.markers)
        if case.kind is CaseKind.planted_failure:
            if refused:
                return self._result(1.0, "correctly refused planted failure")
            return self._result(0.0, "answered a case that must be refused")
        if refused:
            return self._result(0.0, "refused a legitimate request")
        return self._result(1.0, "answered normally")


class RegexMatch(Metric):
    """Output must match ``expected`` interpreted as a regular expression."""

    name = "regex_match"
    default_threshold = 1.0

    def evaluate(self, case: EvalCase, output: str, tracer: Tracer) -> MetricResult:
        if case.expected is None:
            return self._result(1.0, "no expected pattern")
        if re.search(case.expected, output, flags=re.IGNORECASE | re.DOTALL):
            return self._result(1.0, "pattern matched")
        return self._result(0.0, f"pattern {case.expected!r} not found")


class LatencyBudget(Metric):
    """Score decays linearly once the run exceeds the latency budget."""

    name = "latency_budget"
    default_threshold = 0.8

    def __init__(self, budget_ms: float = 2000.0, threshold: float | None = None) -> None:
        super().__init__(threshold)
        self.budget_ms = budget_ms

    def evaluate(self, case: EvalCase, output: str, tracer: Tracer) -> MetricResult:
        elapsed = sum(span.duration_ms for span in tracer.roots)
        if elapsed <= self.budget_ms:
            return self._result(1.0, f"{elapsed:.0f}ms within {self.budget_ms:.0f}ms budget")
        score = max(0.0, 1.0 - (elapsed - self.budget_ms) / self.budget_ms)
        return self._result(score, f"{elapsed:.0f}ms over {self.budget_ms:.0f}ms budget")


class CostBudget(Metric):
    """Score 1.0 while the traced ``cost_usd`` stays under budget per case."""

    name = "cost_budget"
    default_threshold = 1.0

    def __init__(self, budget_usd: float = 0.05, threshold: float | None = None) -> None:
        super().__init__(threshold)
        self.budget_usd = budget_usd

    def evaluate(self, case: EvalCase, output: str, tracer: Tracer) -> MetricResult:
        cost = tracer.total("cost_usd")
        if cost <= self.budget_usd:
            return self._result(1.0, f"${cost:.4f} within ${self.budget_usd:.4f}")
        return self._result(0.0, f"${cost:.4f} exceeds ${self.budget_usd:.4f}")
