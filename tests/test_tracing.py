from relkit import Tracer


def test_nested_spans_form_a_tree() -> None:
    tracer = Tracer()
    with tracer.span("agent_run", kind="agent") as root:
        with tracer.span("retrieval", kind="tool"):
            pass
        with tracer.span("llm_call", kind="llm") as llm:
            llm.set(tokens=120, cost_usd=0.002)
    assert len(tracer.roots) == 1
    assert [c.name for c in root.children] == ["retrieval", "llm_call"]
    assert root.children[1].parent_id == root.span_id


def test_duration_is_measured() -> None:
    tracer = Tracer()
    with tracer.span("work"):
        pass
    assert tracer.roots[0].end_ns is not None
    assert tracer.roots[0].duration_ms >= 0


def test_total_sums_numeric_attribute_across_tree() -> None:
    tracer = Tracer()
    with tracer.span("run", cost_usd=0.001):
        with tracer.span("llm", cost_usd=0.003):
            pass
        with tracer.span("tool", cost_usd="not-a-number"):
            pass
    assert tracer.total("cost_usd") == 0.004


def test_to_json_roundtrip_contains_attributes() -> None:
    import json

    tracer = Tracer()
    with tracer.span("llm", kind="llm", model="test-model"):
        pass
    data = json.loads(tracer.to_json())
    assert data[0]["kind"] == "llm"
    assert data[0]["attributes"]["model"] == "test-model"


def test_sibling_spans_after_exception_still_recorded() -> None:
    tracer = Tracer()
    try:
        with tracer.span("failing"):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    with tracer.span("next"):
        pass
    assert [s.name for s in tracer.roots] == ["failing", "next"]
    assert tracer.roots[0].end_ns is not None
