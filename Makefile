.PHONY: help setup fmt lint typecheck test audit

## help: print this help message
help:
	@echo 'Usage:'
	@sed -n 's/^##//p' ${MAKEFILE_LIST} | column -t -s ':' | sed -e 's/^/ /'

## setup: install dependencies and git hooks
setup:
	uv sync
	git config core.hooksPath .githooks
	@echo "Git hooks installed from .githooks/"

## fmt: format code with ruff
fmt:
	uv run ruff format .
	uv run ruff check --fix .

## lint: run ruff linter
lint:
	uv run ruff check .

## typecheck: run ty type checker
typecheck:
	uv run ty check

## test: run all tests
test:
	uv run pytest tests/ -v

## audit: run all quality control checks
audit: lint typecheck test
	uv run ruff format --check .
	@echo "All checks passed"
