SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

.PHONY: help setup test lint e2e contract dev-cloud dev-store secret-scan

help:
	@echo "Targets: setup test lint e2e contract dev-cloud dev-store secret-scan"

setup:
	uv sync
	@echo "Python dependencies installed (workspace: packages/rules-engine, apps/cloud-api, apps/local-api)."

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

e2e:
	@echo "E2E suite arrives with TASK-E-13 (first Ops screen); see docs/09-build-plan.md."

contract:
	@echo "Contract suite arrives with TASK-E-12 (erpnext-adapter); see docs/09-build-plan.md."

dev-cloud:
	docker compose -f infra/compose/cloud.yml up --build

dev-store:
	docker compose -f infra/compose/store.yml up --build

secret-scan:
	docker run --rm -v "$(CURDIR):/repo" zricethezav/gitleaks:latest detect --source=/repo --no-git --verbose --no-banner
