"""Agent Reliability Kit — observability, planted-failure evals and CI gates.

Public API surface. Anything importable from ``relkit`` directly is stable;
everything else is internal.
"""

from relkit.dataset import DatasetError, load_dataset
from relkit.gate import GateFailure, assert_gate, find_regressions, load_baseline, save_baseline
from relkit.metrics.base import Metric, registered_metrics
from relkit.metrics.deterministic import (
    ContainsAll,
    CostBudget,
    ForbiddenContent,
    LatencyBudget,
    RefusalOnPlantedFailure,
    RegexMatch,
)
from relkit.metrics.judge import FakeJudge, JudgeMetric, JudgeVerdict, load_rubric
from relkit.models import (
    CaseKind,
    CaseResult,
    EvalCase,
    MetricResult,
    MetricSummary,
    Regression,
    SuiteResult,
)
from relkit.report import render_html, write_report
from relkit.runner import AgentFn, run_suite
from relkit.tracing import Span, Tracer

__version__ = "0.1.1"

__all__ = [
    "AgentFn",
    "CaseKind",
    "CaseResult",
    "ContainsAll",
    "CostBudget",
    "DatasetError",
    "EvalCase",
    "FakeJudge",
    "ForbiddenContent",
    "GateFailure",
    "JudgeMetric",
    "JudgeVerdict",
    "LatencyBudget",
    "Metric",
    "MetricResult",
    "MetricSummary",
    "RefusalOnPlantedFailure",
    "RegexMatch",
    "Regression",
    "Span",
    "SuiteResult",
    "Tracer",
    "assert_gate",
    "find_regressions",
    "load_baseline",
    "load_dataset",
    "load_rubric",
    "registered_metrics",
    "render_html",
    "run_suite",
    "save_baseline",
    "write_report",
]
