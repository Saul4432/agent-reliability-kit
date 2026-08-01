# ADR-0002: Datasets must contain planted failures

**Status:** accepted · **Date:** 2026-08-01

## Context

The most common eval failure mode in practice is a dataset where every case is
easy: pass rates sit at 100%, the gate never fires, and the team believes the
agent is safe. Hiring research in 2026 explicitly calls out "planted-failure
datasets" as the marker of engineers who evaluate seriously. We hit this
ourselves: an earlier RAG eval dataset passed everything until it was hardened
— "an eval that everything passes is measuring nothing."

## Decision

`load_dataset()` **raises `DatasetError`** when fewer than 15% of cases are
`kind: planted_failure` (prompt injections, scope escapes, PII bait — cases
where the correct behaviour is refusal or escalation). Opting out requires
passing `min_planted_failure_ratio=0` explicitly at the call site, where a code
reviewer will see it.

The refusal metric is symmetric: planted failures must be refused AND normal
cases must not be refused, so over-cautious agents also fail.

## Consequences

- Every suite exercises the two failure modes that matter in production:
  complying when it shouldn't, refusing when it shouldn't.
- Slightly higher authoring cost per dataset; templates in `examples/` reduce it.
- The 15% default is a floor, not a target; safety-critical agents should raise it.
