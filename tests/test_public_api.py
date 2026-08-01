"""The public API is a contract: everything in __all__ must import and exist."""

import relkit


def test_all_exports_exist() -> None:
    for name in relkit.__all__:
        assert hasattr(relkit, name), f"relkit.{name} missing"


def test_version_is_semver() -> None:
    major, minor, patch = relkit.__version__.split(".")
    assert all(part.isdigit() for part in (major, minor, patch))
