# ============================================================================
# AI Trading Pipeline — Makefile
# ============================================================================
# Usage: make <target> [CONFIG=...] [MODEL=...] [SEED=...]
# Run `make help` for a list of available targets.
# ============================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

# ---------------------------------------------------------------------------
# Overridable variables
# ---------------------------------------------------------------------------
CONFIG ?= configs/default.yaml
MODEL ?=
SEED ?=
RUNS_DIR ?= runs/

# Build --set overrides for the run target
OVERRIDES :=
ifneq ($(MODEL),)
	OVERRIDES += --set strategy.name=$(MODEL)
endif
ifneq ($(SEED),)
	OVERRIDES += --set reproducibility.global_seed=$(SEED)
endif

# ============================================================================
# Main targets
# ============================================================================

.PHONY: install fetch-data qa run run-all

install: ## Install Python dependencies from requirements.txt
	pip install -r requirements.txt

fetch-data: ## Fetch OHLCV data via ingestion module
	python -m ai_trading fetch --config $(CONFIG)

qa: ## Run data quality assurance checks
	python -m ai_trading qa --config $(CONFIG)

run: ## Run the full pipeline (use MODEL= and SEED= to override)
	python -m ai_trading run --config $(CONFIG) $(OVERRIDES)

run-all: fetch-data qa run ## Run fetch-data → qa → run in sequence

# ============================================================================
# Utility targets
# ============================================================================

.PHONY: test lint docker-build docker-run clean help

test: ## Run test suite with pytest
	pytest tests/ -v

lint: ## Run ruff linter and mypy type checker on source and tests
	ruff check ai_trading/ tests/
	mypy ai_trading/

docker-build: ## Build Docker image
	docker build -t ai-trading-pipeline .

docker-run: ## Run pipeline in Docker container with data/runs volumes
	docker run --rm -v $(shell pwd)/data:/app/data -v $(shell pwd)/runs:/app/runs ai-trading-pipeline

clean: ## Remove temporary build artifacts (keeps data and runs)
	rm -rf __pycache__ .pytest_cache .ruff_cache .mypy_cache
	rm -rf ai_trading.egg-info build dist
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

help: ## Display this help message
	@echo "AI Trading Pipeline — Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Dashboard targets
# ============================================================================

.PHONY: dashboard install-dashboard

install-dashboard: ## Install dashboard dependencies from requirements-dashboard.txt
	pip install -r requirements-dashboard.txt

dashboard: ## Launch Streamlit dashboard (use RUNS_DIR= to override runs directory)
	streamlit run scripts/dashboard/app.py -- --runs-dir $(RUNS_DIR)

# ============================================================================
# Gate milestone targets
# GM1 → G-Features → G-Split → GM2 → G-Doc → GM3 → G-Backtest → GM4 → GM5 → GM6
# ============================================================================

.PHONY: gate-m1 gate-m2 gate-m3 gate-m4 gate-m5 gate-m6
.PHONY: gate-features gate-split gate-backtest gate-doc gate-perf

gate-m1: ## Gate M1 — Foundations verification
	@mkdir -p reports
	pytest tests/test_config.py tests/test_config_validation.py tests/test_ingestion.py \
		tests/test_qa.py tests/test_missing.py \
		-v --tb=short --cov=ai_trading/config.py --cov=ai_trading/data --cov-fail-under=95
	@echo '{"gate": "M1", "status": "GO"}' > reports/gate_report_M1.json
	@echo "Gate M1: GO"

gate-features: gate-m1 ## Gate Features — Feature engineering verification (requires M1)
	@mkdir -p reports
	pytest tests/test_feature_registry.py tests/test_feature_pipeline.py \
		tests/test_log_returns.py tests/test_volatility.py tests/test_rsi.py \
		tests/test_ema_ratio.py tests/test_volume_features.py \
		tests/test_warmup_validation.py \
		-v --tb=short --cov=ai_trading/features --cov-fail-under=90
	@echo '{"gate": "G_Features", "status": "GO"}' > reports/gate_report_G_Features.json
	@echo "Gate Features: GO"

gate-split: gate-features ## Gate Split — Dataset/splitter verification (requires G-Features)
	@mkdir -p reports
	pytest tests/test_sample_builder.py tests/test_splitter.py \
		tests/test_label_target.py tests/test_adapter_xgboost.py \
		-v --tb=short --cov=ai_trading/data --cov-fail-under=90
	@echo '{"gate": "G_Split", "status": "GO"}' > reports/gate_report_G_Split.json
	@echo "Gate Split: GO"

gate-m2: gate-split ## Gate M2 — Feature & Data Pipeline verification (requires G-Split)
	@mkdir -p reports
	pytest tests/test_standard_scaler.py tests/test_robust_scaler.py \
		-v --tb=short
	@echo '{"gate": "M2", "status": "GO"}' > reports/gate_report_M2.json
	@echo "Gate M2: GO"

gate-doc: gate-m2 ## Gate Doc — Training/calibration verification (requires M2)
	@mkdir -p reports
	pytest tests/test_base_model.py tests/test_dummy_model.py \
		tests/test_fold_trainer.py tests/test_quantile_grid.py \
		tests/test_theta_optimization.py tests/test_theta_bypass.py \
		-v --tb=short --cov=ai_trading/training --cov=ai_trading/calibration --cov-fail-under=90
	@echo '{"gate": "G_Doc", "status": "GO"}' > reports/gate_report_G_Doc.json
	@echo "Gate Doc: GO"

gate-m3: gate-doc ## Gate M3 — Training Framework verification (requires G-Doc)
	@mkdir -p reports
	pytest tests/test_base_model.py tests/test_dummy_model.py \
		tests/test_fold_trainer.py tests/test_quantile_grid.py \
		tests/test_theta_optimization.py \
		-v --tb=short
	@echo '{"gate": "M3", "status": "GO"}' > reports/gate_report_M3.json
	@echo "Gate M3: GO"

gate-backtest: gate-m3 ## Gate Backtest — Backtest engine verification (requires M3)
	@mkdir -p reports
	pytest tests/test_trade_execution.py tests/test_cost_model.py \
		tests/test_equity_curve.py tests/test_trade_journal.py \
		tests/test_trading_metrics.py \
		-v --tb=short --cov=ai_trading/backtest --cov-fail-under=90
	@echo '{"gate": "G_Backtest", "status": "GO"}' > reports/gate_report_G_Backtest.json
	@echo "Gate Backtest: GO"

gate-m4: gate-backtest ## Gate M4 — Evaluation Engine verification (requires G-Backtest)
	@mkdir -p reports
	pytest tests/test_baseline_no_trade.py tests/test_baseline_buy_hold.py \
		tests/test_baseline_sma_rule.py tests/test_prediction_metrics.py \
		tests/test_aggregation.py \
		-v --tb=short
	@echo '{"gate": "M4", "status": "GO"}' > reports/gate_report_M4.json
	@echo "Gate M4: GO"

gate-m5: gate-m4 ## Gate M5 — Production Readiness verification (requires M4)
	@mkdir -p reports
	pytest tests/test_manifest_builder.py tests/test_metrics_builder.py \
		tests/test_run_dir.py tests/test_seed.py tests/test_runner.py \
		tests/test_json_schema_validation.py \
		-v --tb=short
	@echo '{"gate": "M5", "status": "GO"}' > reports/gate_report_M5.json
	@echo "Gate M5: GO"

gate-m6: gate-m5 ## Gate M6 — Full-scale network validation (requires M5)
	@mkdir -p reports
	pytest -m fullscale tests/test_fullscale_btc.py -v --timeout=600
	@echo '{"gate": "M6", "status": "GO"}' > reports/gate_report_M6.json
	@echo "Gate M6: GO"

gate-perf: ## Gate Perf — Performance benchmarks (post-MVP, non-blocking)
	@mkdir -p reports
	@echo "Performance benchmarks: post-MVP — skipped"
	@echo '{"gate": "G_Perf", "status": "SKIPPED", "note": "post-MVP"}' > reports/gate_report_G_Perf.json
	@echo "Gate Perf: SKIPPED (post-MVP)"
