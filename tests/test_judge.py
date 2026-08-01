from relkit import EvalCase, FakeJudge, JudgeMetric, JudgeVerdict, Tracer, load_rubric


def test_rubric_loads_from_package() -> None:
    rubric = load_rubric()
    assert "{input}" in rubric and "{output}" in rubric


def test_fake_judge_scores_by_expected_containment() -> None:
    metric = JudgeMetric(judge=FakeJudge())
    case = EvalCase(id="x", input="price of a website?", expected="990")
    good = metric.evaluate(case, "It costs 990 EUR", Tracer())
    bad = metric.evaluate(case, "It costs a lot", Tracer())
    assert good.score == 1.0 and good.passed
    assert bad.score == 0.0 and not bad.passed


def test_fake_judge_without_expected_passes() -> None:
    metric = JudgeMetric(judge=FakeJudge())
    case = EvalCase(id="x", input="hello")
    assert metric.evaluate(case, "hi there", Tracer()).score == 1.0


def test_custom_scorer_and_call_recording() -> None:
    judge = FakeJudge(scorer=lambda prompt: 0.42)
    metric = JudgeMetric(judge=judge, threshold=0.5)
    result = metric.evaluate(EvalCase(id="x", input="q"), "out", Tracer())
    assert result.score == 0.42 and not result.passed
    assert len(judge.calls) == 1
    assert "OUTPUT:" in judge.calls[0]


def test_judge_cost_is_propagated() -> None:
    def judge(prompt: str) -> JudgeVerdict:
        return JudgeVerdict(score=1.0, reason="ok", cost_usd=0.01)

    result = JudgeMetric(judge=judge).evaluate(EvalCase(id="x", input="q"), "out", Tracer())
    assert result.cost_usd == 0.01


def test_custom_rubric_is_used() -> None:
    metric = JudgeMetric(
        judge=FakeJudge(scorer=lambda p: 1.0), rubric="Q:{input} E:{expected} OUTPUT:{output}"
    )
    prompt = metric.render_prompt(EvalCase(id="x", input="q", expected="e"), "o")
    assert prompt == "Q:q E:e OUTPUT:o"
