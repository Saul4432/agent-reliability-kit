# Agent Reliability Kit (`relkit`)

**Observability, planted-failure evals and CI quality gates for LLM agents — zero API keys required to test.**

[![CI](https://github.com/Saul4432/agent-reliability-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/Saul4432/agent-reliability-kit/actions)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![Typed](https://img.shields.io/badge/typing-mypy%20strict-informational)
![License](https://img.shields.io/badge/license-MIT-green)

Quality is the #1 blocker for agents in production (32% of teams, [State of Agent Engineering 2026](https://www.langchain.com/state-of-agent-engineering)), and 89% of organizations now require observability. `relkit` turns both into code: **trace every agent run, evaluate it against a golden dataset with planted failures, and fail the CI build when quality regresses.**

```
agent ──▶ Tracer (spans: llm, tools, cost, tokens)
              │
   run_suite(agent, dataset, metrics)
              │
      SuiteResult ──▶ HTML report
              │
   assert_gate(result, baseline) ──▶ ✅ merge  /  ❌ build fails
```

## Why this exists

Most agent demos are graded by vibes. This kit enforces three habits that separate production agents from demos:

1. **Planted failures are mandatory.** `load_dataset()` *rejects* datasets without adversarial cases (prompt injection, scope escapes). An eval that everything passes is measuring nothing.
2. **Deterministic metrics first, LLM-as-judge second.** Substring/regex/refusal/cost/latency checks run in milliseconds on every commit; the judge metric complements them and ships with a first-class `FakeJudge` so the whole suite runs offline.
3. **Baselines make quality a diff.** Every suite result serializes to JSON; `assert_gate()` fails the build if any metric drops below threshold *or* regresses vs the committed baseline.

## Quickstart

```bash
pip install -e ".[dev]"
make demo        # run the example suite: report + baseline + gate
make check       # lint + mypy strict + tests (90%+ coverage enforced)
```

```python
from relkit import (
    ContainsAll, RefusalOnPlantedFailure, CostBudget, JudgeMetric, FakeJudge,
    Tracer, load_dataset, run_suite, assert_gate, write_report,
)

def my_agent(user_input: str, tracer: Tracer) -> str:
    with tracer.span("llm_call", kind="llm", cost_usd=0.002, tokens=350):
        return call_your_model(user_input)   # any provider, any framework

cases = load_dataset("evals/dataset.yaml")   # rejects datasets w/o planted failures
result = run_suite("support-agent", my_agent, cases, [
    ContainsAll(),
    RefusalOnPlantedFailure(),               # symmetric: catches over-refusal too
    CostBudget(budget_usd=0.01),
    JudgeMetric(judge=FakeJudge()),          # swap for an LLM judge in prod
])

write_report(result, "report.html")
assert_gate(result, baseline_path="evals/baseline.json")  # raises in CI on regression
```

The agent contract is one function: `(input: str, tracer: Tracer) -> str`. No SDK lock-in — wrap LangGraph, CrewAI, pydantic-ai, raw API calls or an n8n webhook exactly the same way.

## What's in the box

| Module | What it does |
|---|---|
| `relkit.tracing` | Dependency-free span tracer (nested spans via contextvars, cost/token accounting, JSON export) |
| `relkit.dataset` | YAML golden datasets, validated: unique ids, **minimum planted-failure ratio enforced** |
| `relkit.metrics` | `ContainsAll`, `ForbiddenContent`, `RefusalOnPlantedFailure`, `RegexMatch`, `LatencyBudget`, `CostBudget`, `JudgeMetric` — auto-registered via `__init_subclass__` |
| `relkit.metrics.judge` | LLM-as-judge with **versioned YAML rubric** and public `FakeJudge` (inspired by pydantic-ai's `TestModel`) |
| `relkit.runner` | Runs the suite; agent crashes are *scored*, not raised — a crash is a reliability result |
| `relkit.gate` | Thresholds + baseline regression detection, CI-log-friendly failure messages |
| `relkit.report` | Self-contained HTML dashboard (no external assets, output escaped) |
| `relkit.pytest_plugin` | `relkit_report_dir` fixture + terminal summary |

## Design decisions (ADRs)

Key tradeoffs are documented in [`docs/adr/`](docs/adr/):

- [ADR-0001](docs/adr/0001-offline-first-fakes-as-public-api.md) — Offline-first: fakes are public API, not test fixtures
- [ADR-0002](docs/adr/0002-planted-failures-are-mandatory.md) — Datasets must contain planted failures
- [ADR-0003](docs/adr/0003-agent-contract-is-a-function.md) — The agent contract is one function, not a framework

## Engineering standard

- `mypy --strict` on all source, `py.typed` shipped
- ruff (incl. import sorting, bugbear, complexity ≤ 12)
- 50+ tests, coverage gate ≥ 90%, Python 3.10–3.12 matrix in CI
- GitHub Actions pinned by SHA; the CI **gates itself** with its own example suite and uploads the HTML report as an artifact
- Judge rubric lives in [versioned YAML](src/relkit/prompts/judge_rubric.yaml) — prompt changes show up in code review

## Roadmap

- OpenTelemetry span exporter
- VCR-style recording of real model calls for judge metrics
- Multi-run statistical mode (variance across seeds)

## License

MIT © Saúl Gimeno
