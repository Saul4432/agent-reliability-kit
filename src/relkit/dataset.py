"""Golden dataset loading and validation.

Datasets are YAML files checked into the repo next to the code they guard.
A dataset MUST contain planted failures — ``load_dataset`` enforces a minimum
ratio, because a suite that cannot fail is measuring nothing.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from relkit.models import CaseKind, EvalCase


class DatasetError(ValueError):
    """Raised when a dataset file is structurally invalid or too weak."""


def load_dataset(
    path: str | Path,
    *,
    min_planted_failure_ratio: float = 0.15,
) -> list[EvalCase]:
    """Load and validate an eval dataset from YAML.

    Args:
        path: YAML file with a top-level ``cases`` list.
        min_planted_failure_ratio: minimum fraction of adversarial cases
            required (set to 0 to opt out, explicitly).
    """
    raw = yaml.safe_load(Path(path).read_text("utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("cases"), list):
        raise DatasetError(f"{path}: expected a mapping with a 'cases' list")

    cases = [EvalCase.model_validate(item) for item in raw["cases"]]
    if not cases:
        raise DatasetError(f"{path}: dataset is empty")

    ids = [c.id for c in cases]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise DatasetError(f"{path}: duplicate case ids {duplicates}")

    planted = sum(1 for c in cases if c.kind is CaseKind.planted_failure)
    ratio = planted / len(cases)
    if ratio < min_planted_failure_ratio:
        raise DatasetError(
            f"{path}: only {planted}/{len(cases)} planted failures "
            f"({ratio:.0%} < required {min_planted_failure_ratio:.0%}). "
            "An eval that everything passes is measuring nothing."
        )
    return cases
