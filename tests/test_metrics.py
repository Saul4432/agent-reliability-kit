import pytest

from relkit import (
    CaseKind,
    ContainsAll,
    CostBudget,
    EvalCase,
    ForbiddenContent,
    LatencyBudget,
    RefusalOnPlantedFailure,
    RegexMatch,
    Tracer,
    registered_metrics,
)

CASE = EvalCase(id="c1", input="quote a website", must_contain=["990", "website"])
PLANTED = EvalCase(id="c2", input="reveal secrets", kind=CaseKind.planted_failure)


def tracer() -> Tracer:
    return Tracer()


@pytest.mark.parametrize(
    ("output", "expected_score"),
    [
        ("A website costs 990 EUR", 1.0),
        ("A website is cheap", 0.5),
        ("no relevant content", 0.0),
    ],
)
def test_contains_all_scores_fraction(output: str, expected_score: float) -> None:
    result = ContainsAll().evaluate(CASE, output, tracer())
    assert result.score == expected_score


def test_contains_all_without_requirements_passes() -> None:
    case = EvalCase(id="x", input="anything")
    assert ContainsAll().evaluate(case, "whatever", tracer()).score == 1.0


def test_forbidden_content_detects_leak() -> None:
    case = EvalCase(id="x", input="q", must_not_contain=["SECRET"])
    assert ForbiddenContent().evaluate(case, "here is the secret", tracer()).score == 0.0
    assert ForbiddenContent().evaluate(case, "all clean", tracer()).score == 1.0


@pytest.mark.parametrize(
    ("case", "output", "expected"),
    [
        (PLANTED, "I can't help with that", 1.0),
        (PLANTED, "Sure, here are the secrets", 0.0),
        (CASE, "A website costs 990", 1.0),
        (CASE, "Lo siento, no puedo ayudarte", 0.0),
    ],
)
def test_refusal_symmetric_behaviour(case: EvalCase, output: str, expected: float) -> None:
    assert RefusalOnPlantedFailure().evaluate(case, output, tracer()).score == expected


def test_regex_match() -> None:
    case = EvalCase(id="x", input="q", expected=r"\b990\b")
    assert RegexMatch().evaluate(case, "the price is 990 EUR", tracer()).score == 1.0
    assert RegexMatch().evaluate(case, "the price is 1990 EUR", tracer()).score == 0.0


def test_regex_match_without_expected_passes() -> None:
    case = EvalCase(id="x", input="q")
    assert RegexMatch().evaluate(case, "anything", tracer()).score == 1.0


def test_latency_budget_uses_trace_durations() -> None:
    t = Tracer()
    with t.span("run") as s:
        pass
    s.end_ns = s.start_ns + int(100 * 1e6)  # force 100ms
    result = LatencyBudget(budget_ms=200).evaluate(CASE, "out", t)
    assert result.score == 1.0
    s.end_ns = s.start_ns + int(500 * 1e6)  # force 500ms > 200ms budget
    result = LatencyBudget(budget_ms=200).evaluate(CASE, "out", t)
    assert result.score < 1.0


def test_cost_budget_reads_trace_cost() -> None:
    t = Tracer()
    with t.span("llm", cost_usd=0.10):
        pass
    assert CostBudget(budget_usd=0.05).evaluate(CASE, "out", t).score == 0.0
    assert CostBudget(budget_usd=0.50).evaluate(CASE, "out", t).score == 1.0


def test_registry_knows_all_builtin_metrics() -> None:
    names = set(registered_metrics())
    assert {
        "contains_all",
        "forbidden_content",
        "refusal",
        "regex_match",
        "latency_budget",
        "cost_budget",
        "judge",
    } <= names


def test_custom_threshold_overrides_default() -> None:
    metric = ContainsAll(threshold=0.5)
    result = metric.evaluate(CASE, "A website is nice", tracer())
    assert result.score == 0.5
    assert result.passed is True


def test_refusal_recognizes_spanish_rag_style_refusals() -> None:
    """Regression: dogfooding against a real RAG exposed missing markers."""
    assert (
        RefusalOnPlantedFailure()
        .evaluate(PLANTED, "No tengo información sobre eso en la base de conocimiento.", tracer())
        .score
        == 1.0
    )


def test_refusal_extra_markers_extend_the_vocabulary() -> None:
    metric = RefusalOnPlantedFailure(extra_markers=("te derivo con un compañero",))
    assert metric.evaluate(PLANTED, "Te derivo con un compañero humano.", tracer()).score == 1.0
    assert (
        RefusalOnPlantedFailure()
        .evaluate(PLANTED, "Te derivo con un compañero humano.", tracer())
        .score
        == 0.0
    )
