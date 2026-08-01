"""Metric base class with automatic registry.

Pattern borrowed from deepeval (``BaseMetric`` + ``__init_subclass__``
instrumentation) and crewAI's persistence registry: subclassing is enough to
make a metric discoverable by name, no manual registration step.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from relkit.models import EvalCase, MetricResult
from relkit.tracing import Tracer

_REGISTRY: dict[str, type[Metric]] = {}


class Metric(ABC):
    """A check applied to (case, agent output, trace) producing a 0..1 score."""

    name: str = "metric"
    #: minimum mean score across the suite for the gate to pass
    default_threshold: float = 0.8

    def __init__(self, threshold: float | None = None) -> None:
        self.threshold = self.default_threshold if threshold is None else threshold

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if getattr(cls, "name", None) and cls.name != "metric":
            _REGISTRY[cls.name] = cls

    @abstractmethod
    def evaluate(self, case: EvalCase, output: str, tracer: Tracer) -> MetricResult:
        """Score one case. Must be deterministic given the same inputs."""

    def _result(self, score: float, reason: str = "", cost_usd: float = 0.0) -> MetricResult:
        score = max(0.0, min(1.0, score))
        return MetricResult(
            metric=self.name,
            score=score,
            passed=score >= self.threshold,
            reason=reason,
            cost_usd=cost_usd,
        )


def registered_metrics() -> dict[str, type[Metric]]:
    """Snapshot of all metric classes known to the kit."""
    return dict(_REGISTRY)
