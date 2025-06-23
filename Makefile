# Makefile for money-flow project

.PHONY: help venv install-dev clean test lint format precommit

help:
	@echo "Available targets:"
	@echo "  venv         Create virtual environment and install all dependencies (including dev)"
	@echo "  install-dev  Install only dev dependencies into the current environment"
	@echo "  clean        Remove the .venv directory"
	@echo "  test         Run pytest"
	@echo "  lint         Run ruff linter"
	@echo "  format       Run ruff formatter"
	@echo "  precommit    Run pre-commit hooks on all files"

venv:
	@echo "[Info] Installing dependencies with uv..."
	uv sync --all-extras
	@echo "[Info] Installing Look Ahead package in editable mode..."
	. .venv/bin/activate && uv pip install -e .
	pre-commit install

install-dev:
	uv pip install -e .[dev]

clean:
	rm -rf .venv

lint:
	ruff check src

format:
	ruff format src

test:
	pytest

precommit:
	pre-commit run --all-files
