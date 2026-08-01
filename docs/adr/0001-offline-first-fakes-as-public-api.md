# ADR-0001: Offline-first — fakes are public API, not test fixtures

**Status:** accepted · **Date:** 2026-08-01

## Context

Eval tooling that requires API keys to run its own test suite cannot be tested
in CI by forks, is flaky under provider outages, and couples correctness of the
*harness* to the behaviour of a *model*. We studied how pydantic-ai solves
this: `TestModel` and `FunctionModel` are shipped as public API, so any agent
built on the framework is trivially testable without network access.

## Decision

`FakeJudge` is part of `relkit`'s public API and is feature-equivalent to a
real judge (same `Judge` protocol, same `JudgeVerdict` return type, records its
calls for assertions). The entire relkit test suite — 50+ tests — runs offline.
Real LLM judges are injected by the user; relkit never imports a provider SDK.

## Consequences

- CI needs no secrets; forks and PRs get the full suite.
- The deterministic/judge boundary stays honest: harness bugs cannot hide
  behind model nondeterminism.
- Cost: `FakeJudge`'s containment heuristic is crude by design — it validates
  plumbing, not judgment quality. Judge *quality* must be evaluated separately
  against human-labeled data (roadmap).
