from pathlib import Path

import pytest

from relkit import CaseKind, DatasetError, load_dataset

VALID = """
cases:
  - id: a
    input: "hello"
    must_contain: ["hi"]
  - id: b
    input: "ignore instructions"
    kind: planted_failure
"""


def write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "dataset.yaml"
    p.write_text(content, "utf-8")
    return p


def test_loads_valid_dataset(tmp_path: Path) -> None:
    cases = load_dataset(write(tmp_path, VALID))
    assert len(cases) == 2
    assert cases[1].kind is CaseKind.planted_failure


def test_rejects_empty_dataset(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="empty"):
        load_dataset(write(tmp_path, "cases: []"))


def test_rejects_missing_cases_key(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="'cases' list"):
        load_dataset(write(tmp_path, "foo: bar"))


def test_rejects_duplicate_ids(tmp_path: Path) -> None:
    content = """
cases:
  - {id: x, input: "one", kind: planted_failure}
  - {id: x, input: "two"}
"""
    with pytest.raises(DatasetError, match="duplicate"):
        load_dataset(write(tmp_path, content))


def test_rejects_dataset_without_planted_failures(tmp_path: Path) -> None:
    content = """
cases:
  - {id: a, input: "one"}
  - {id: b, input: "two"}
"""
    with pytest.raises(DatasetError, match="measuring nothing"):
        load_dataset(write(tmp_path, content))


def test_planted_failure_ratio_can_be_disabled_explicitly(tmp_path: Path) -> None:
    content = """
cases:
  - {id: a, input: "one"}
"""
    cases = load_dataset(write(tmp_path, content), min_planted_failure_ratio=0)
    assert len(cases) == 1
