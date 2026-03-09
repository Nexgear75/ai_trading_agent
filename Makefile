# ============================================================================
# AI Trading Pipeline - Makefile
# ============================================================================
# Usage: make <target> [CONFIG=...] [STRATEGY=...] [OUTPUT_DIR=...]
# Run `make help` for a list of available targets.
# ============================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

# ---------------------------------------------------------------------------
# Overridable variables
# ---------------------------------------------------------------------------
CONFIG     ?= fullscale_btc_xgboost.yaml
STRATEGY   ?=
OUTPUT_DIR ?=

# Build CLI flags from overrides
CLI_FLAGS := --config $(CONFIG)
ifneq ($(STRATEGY),)
	CLI_FLAGS += --strategy $(STRATEGY)
endif
ifneq ($(OUTPUT_DIR),)
	CLI_FLAGS += --output-dir $(OUTPUT_DIR)
endif

# ============================================================================
# Main targets
# ============================================================================

.PHONY: install install-dev fetch run

install: ## Install runtime dependencies
	pip install -r requirements.txt

install-dev: ## Install runtime + dev/test dependencies
	pip install -r requirements-dev.txt

fetch: ## Fetch OHLCV data (ccxt) using config ingestion settings
	python fetch.py --config $(CONFIG)

run: ## Run the full pipeline (use STRATEGY= and OUTPUT_DIR= to override)
	python pipeline.py $(CLI_FLAGS)

# ============================================================================
# Quality targets
# ============================================================================

.PHONY: test lint typecheck check

test: ## Run test suite with pytest
	python -m pytest pipeline_test.py -v

lint: ## Lint with ruff
	ruff check pipeline.py lib/ pipeline_test.py conftest.py

typecheck: ## Type-check with mypy
	mypy pipeline.py lib/ --ignore-missing-imports

check: lint typecheck test ## Run lint + typecheck + tests

# ============================================================================
# Utility targets
# ============================================================================

.PHONY: clean help

clean: ## Remove caches and temporary files (keeps data/ and runs/)
	rm -rf __pycache__ .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
