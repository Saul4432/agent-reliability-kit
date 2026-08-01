"""Lightweight span tracer for agent runs.

Inspired by the tracing modules of openai-agents-python and pydantic-ai:
spans are plain data, nesting is handled with a ``contextvars`` stack, and a
whole trace exports to JSON so it can be attached to eval results, diffed, or
shipped to any backend. No third-party dependency, works offline.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

_current_span: ContextVar[Span | None] = ContextVar("relkit_current_span", default=None)


@dataclass
class Span:
    """One timed unit of work (llm call, tool call, retrieval, ...)."""

    name: str
    kind: str = "internal"
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    parent_id: str | None = None
    start_ns: int = field(default_factory=time.perf_counter_ns)
    end_ns: int | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    children: list[Span] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        end = self.end_ns if self.end_ns is not None else time.perf_counter_ns()
        return (end - self.start_ns) / 1e6

    def set(self, **attributes: Any) -> Span:
        """Attach attributes (tokens, cost_usd, model, ...) to the span."""
        self.attributes.update(attributes)
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "duration_ms": round(self.duration_ms, 3),
            "attributes": self.attributes,
            "children": [c.to_dict() for c in self.children],
        }


class Tracer:
    """Collects a tree of spans for a single agent run."""

    def __init__(self) -> None:
        self.roots: list[Span] = []

    @contextmanager
    def span(self, name: str, kind: str = "internal", **attributes: Any) -> Iterator[Span]:
        parent = _current_span.get()
        span = Span(name=name, kind=kind, parent_id=parent.span_id if parent else None)
        span.attributes.update(attributes)
        if parent is not None:
            parent.children.append(span)
        else:
            self.roots.append(span)
        token = _current_span.set(span)
        try:
            yield span
        finally:
            span.end_ns = time.perf_counter_ns()
            _current_span.reset(token)

    def iter_spans(self) -> Iterator[Span]:
        stack = list(self.roots)
        while stack:
            span = stack.pop()
            yield span
            stack.extend(span.children)

    def total(self, attribute: str) -> float:
        """Sum a numeric attribute (e.g. ``cost_usd``, ``tokens``) across all spans."""
        acc = 0.0
        for span in self.iter_spans():
            value = span.attributes.get(attribute)
            if isinstance(value, (int, float)):
                acc += float(value)
        return acc

    def to_json(self, indent: int = 2) -> str:
        return json.dumps([s.to_dict() for s in self.roots], indent=indent)
