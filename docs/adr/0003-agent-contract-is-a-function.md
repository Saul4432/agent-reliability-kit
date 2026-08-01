# ADR-0003: The agent contract is one function, not a framework

**Status:** accepted · **Date:** 2026-08-01

## Context

Agent frameworks churn fast (AutoGen entered maintenance mode and is merging
into a new framework; CrewAI breaks between minors). An eval kit that imports
any of them inherits their churn and excludes everyone else. Meanwhile 75%+ of
teams run multiple models/frameworks side by side.

## Decision

The unit under test is `AgentFn = Callable[[str, Tracer], str]`. relkit imports
no LLM SDK and no agent framework. Adapters are the user's one-liner:

```python
def agent(x: str, tracer: Tracer) -> str:
    with tracer.span("llm_call", kind="llm"):
        return str(my_langgraph_app.invoke({"input": x})["output"])
```

Agent exceptions are captured and scored as outputs (`[agent error] ...`)
rather than aborting the suite: a crashing agent is a reliability *result*.

## Consequences

- Works with LangGraph, CrewAI, pydantic-ai, raw HTTP, n8n webhooks — and
  whatever ships next year — with zero changes to relkit.
- Tracing inside the agent is opt-in via the passed `Tracer`; an agent that
  ignores it still gets latency and output metrics, just not cost/token ones.
- Structured (non-string) outputs must be serialized by the adapter; a typed
  generic output is deliberately deferred until a real use case demands it.
