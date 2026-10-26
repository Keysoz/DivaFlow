SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

# gitleaks v8.30.1, digest pinned (verified 2026-10-26).
GITLEAKS_IMAGE := zricethezav/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f

# Requirements snapshot for pip-audit (generated from uv.lock; removed after the scan).
AUDIT_REQ := /tmp/diva-audit-requirements.txt

.PHONY: help setup test lint audit e2e contract dev-cloud dev-store secret-scan

help:
	@echo "Targets: setup test lint audit e2e contract dev-cloud dev-store secret-scan"

setup:
	uv sync
	@echo "Python dependencies installed (workspace: packages/rules-engine, apps/cloud-api, apps/local-api)."

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

audit:
	uv export --format requirements-txt --no-hashes --all-groups > $(AUDIT_REQ)
	uvx pip-audit -r $(AUDIT_REQ)
	rm -f $(AUDIT_REQ)
	@if [ -f package.json ]; then pnpm audit --audit-level=high; else echo "No JavaScript dependencies yet; npm/pnpm audit joins with the first UI task (TASK-E-13)."; fi

e2e:
	@echo "E2E suite arrives with TASK-E-13 (first Ops screen); see docs/09-build-plan.md."

contract:
	@echo "Contract suite arrives with TASK-E-12 (erpnext-adapter); see docs/09-build-plan.md."

dev-cloud:
	docker compose -f infra/compose/cloud.yml up --build

dev-store:
	docker compose -f infra/compose/store.yml up --build

secret-scan:
	docker run --rm -v "$$(git rev-parse --show-toplevel):/repo" $(GITLEAKS_IMAGE) detect --source=/repo --no-git --verbose --redact --no-banner
