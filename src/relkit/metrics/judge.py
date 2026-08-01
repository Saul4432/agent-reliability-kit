"""LLM-as-judge metric with a first-class fake.

Two patterns learned from elite repos are combined here:

* **pydantic-ai** ships ``TestModel`` as *public API*, not as a test fixture —
  so here ``FakeJudge`` is public API too: every judge-based eval can run
  offline, in CI, with zero API keys.
* **deepeval** externalizes judge prompts as versioned artifacts — the rubric
  lives in ``relkit/prompts/judge_rubric.yaml``, not inside Python strings.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib import resources
from typing import Protocol

import yaml
from pydantic import BaseModel, Field

from relkit.metrics.base import Metric
from relkit.models import EvalCase, MetricResult
from relkit.tracing import Tracer


class JudgeVerdict(BaseModel):
    """Structured verdict a judge must return."""

    score: float = Field(ge=0.0, le=1.0)
    reason: str = ""
    cost_usd: float = 0.0


class Judge(Protocol):
    """Anything that maps a rendered rubric prompt to a verdict."""

    def __call__(self, prompt: str) -> JudgeVerdict: ...


def load_rubric(name: str = "judge_rubric") -> str:
    """Load a versioned rubric template shipped with the package."""
    text = resources.files("relkit.prompts").joinpath(f"{name}.yaml").read_text("utf-8")
    data = yaml.safe_load(text)
    template = data.get("template")
    if not isinstance(template, str):
        raise ValueError(f"rubric {name!r} has no 'template' string")
    return template


class JudgeMetric(Metric):
    """Grade faithfulness/quality of an output using any ``Judge`` callable.

    Pass a real LLM-backed judge in production and ``FakeJudge`` in tests —
    the metric code is identical, which is the whole point.
    """

    name = "judge"
    default_threshold = 0.7

    def __init__(
        self,
        judge: Judge,
        rubric: str | None = None,
        threshold: float | None = None,
    ) -> None:
        super().__init__(threshold)
        self.judge = judge
        self.rubric = rubric if rubric is not None else load_rubric()

    def render_prompt(self, case: EvalCase, output: str) -> str:
        return self.rubric.format(
            input=case.input,
            expected=case.expected or "(not provided)",
            output=output,
        )

    def evaluate(self, case: EvalCase, output: str, tracer: Tracer) -> MetricResult:
        verdict = self.judge(self.render_prompt(case, output))
        return self._result(verdict.score, verdict.reason, cost_usd=verdict.cost_usd)


class FakeJudge:
    """Deterministic offline judge — public API, mirrors pydantic-ai's TestModel.

    By default scores 1.0 when the case's ``expected`` text (if any) appears in
    the output, else 0.0. A custom ``scorer`` makes it programmable per test.
    """

    def __init__(self, scorer: Callable[[str], float] | None = None) -> None:
        self.scorer = scorer
        self.calls: list[str] = []

    def __call__(self, prompt: str) -> JudgeVerdict:
        self.calls.append(prompt)
        if self.scorer is not None:
            return JudgeVerdict(score=self.scorer(prompt), reason="fake scorer")
        # crude containment heuristic on the rendered prompt sections
        try:
            expected = prompt.split("EXPECTED:", 1)[1].split("OUTPUT:", 1)[0].strip()
            output = prompt.split("OUTPUT:", 1)[1].strip()
        except IndexError:
            return JudgeVerdict(score=0.0, reason="malformed prompt")
        if expected == "(not provided)" or expected.lower() in output.lower():
            return JudgeVerdict(score=1.0, reason="expected content present")
        return JudgeVerdict(score=0.0, reason="expected content missing")
