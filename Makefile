.PHONY: install format lint typecheck test check demo

install:
	pip install -e ".[dev]"

format:
	ruff format src tests examples
	ruff check --fix src tests examples

lint:
	ruff format --check src tests examples
	ruff check src tests examples

typecheck:
	mypy

# coverage run (not pytest-cov): relkit is itself a pytest plugin, so it gets
# imported before pytest-cov could start measuring.
test:
	coverage run -m pytest
	coverage report

check: lint typecheck test

demo:
	python examples/run_intake_evals.py
