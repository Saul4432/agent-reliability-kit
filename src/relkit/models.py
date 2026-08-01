"""Core data models for the Agent Reliability Kit.

Every result produced by the kit is a validated, serializable Pydantic model,
so suite runs can be stored as baselines, diffed in CI and rendered as reports.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CaseKind(str, Enum):
    """The role a case plays inside an eval dataset.

    ``planted_failure`` cases are adversarial by design: the *correct* agent
    behaviour is to refuse, escalate or abstain. A dataset without planted
    failures measures nothing (an eval that everything passes is not an eval).
    """

    normal = "normal"
    planted_failure = "planted_failure"


class EvalCase(BaseModel):
    """A single input the agent will be evaluated on."""

    id: str
    input: str
    kind: CaseKind = CaseKind.normal
    expected: str | None = None
    must_contain: list[str] = Field(default_factory=list)
    must_not_contain: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class MetricResult(BaseModel):
    """Outcome of one metric applied to one case."""

    metric: str
    score: float = Field(ge=0.0, le=1.0)
    passed: bool
    reason: str = ""
    cost_usd: float = 0.0


class CaseResult(BaseModel):
    """All metric outcomes for one case, plus the raw agent output."""

    case_id: str
    kind: CaseKind
    output: str
    latency_ms: float
    metrics: list[MetricResult]

    @property
    def passed(self) -> bool:
        return all(m.passed for m in self.metrics)


class MetricSummary(BaseModel):
    """Aggregate view of a metric across the whole suite."""

    metric: str
    mean_score: float
    pass_rate: float
    threshold: float


class SuiteResult(BaseModel):
    """The full outcome of a suite run — the unit stored as a baseline."""

    suite_name: str
    cases: list[CaseResult]
    summaries: list[MetricSummary]
    total_cost_usd: float = 0.0

    @property
    def pass_rate(self) -> float:
        if not self.cases:
            return 0.0
        return sum(1 for c in self.cases if c.passed) / len(self.cases)

    def summary_for(self, metric: str) -> MetricSummary | None:
        return next((s for s in self.summaries if s.metric == metric), None)


class Regression(BaseModel):
    """A metric that got worse than the stored baseline beyond tolerance."""

    metric: str
    baseline_score: float
    current_score: float
    delta: float
