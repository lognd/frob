.PHONY: all install lint format typecheck test clean

all: lint typecheck test

install:
	uv sync

lint: install
	uv run ruff check src/ tests/
	uv run black --check src/ tests/
	uv run isort --check-only src/ tests/

format: install
	uv run black src/ tests/
	uv run isort src/ tests/

typecheck: install
	uv run ty check src/

test: install
	uv run pytest

clean:
	rm -rf .venv .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
