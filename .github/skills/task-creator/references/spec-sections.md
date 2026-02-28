# Analyzing Specification Documents

## Purpose

This reference provides a methodology for extracting implementation tasks from the AI Trading Pipeline specification.

## Step 1: Understand Document Structure

Scan the specification to identify:

| Element | What to look for |
|---------|------------------|
| **Table of contents** | Section hierarchy (§1–§17, Annexes) |
| **Formulas** | Feature calculations (§6), labels (§5), backtest (§12), metrics (§14) |
| **Config parameters** | Annexe E.1 (all MVP parameters in `configs/default.yaml`) |
| **Constraints** | Anti-fuite (§8.2), embargo, scaler fit-on-train (§9) |
| **Interfaces** | BaseModel ABC (§10), BaseFeature registry (§6) |
| **Schemas** | manifest.schema.json, metrics.schema.json (§15) |
| **Gates** | Milestone gates (M1–M5), intra-milestone gates (G-Features, G-Split, G-Backtest, G-Doc) |

## Step 2: Categorize Requirements

Map specification content to task types:

| Spec Content | Task Type | Example |
|--------------|-----------|---------|
| Feature formula (§6) | Feature task | "RSI with Wilder smoothing" → rsi.py |
| Config parameter (Annexe E.1) | Config validation task | "embargo_bars >= H" → config validation |
| Split/embargo rule (§8) | Data pipeline task | "walk-forward splitter" → splitter.py |
| Backtest rule (§12) | Backtest task | "one_at_a_time mode" → engine.py |
| Metric formula (§14) | Metrics task | "Sharpe ratio" → trading.py |
| JSON schema (§15) | Artifact task | "manifest.json validation" → schema_validator.py |
| Anti-fuite constraint | Test task | "perturbation test for causal features" |

## Step 3: Identify Dependencies

Before creating tasks, map dependencies using the plan's WS dependency graph:

```
M1: WS-1 → WS-2
M2: WS-3 → G-Features → WS-4 → G-Split → WS-5
M3: WS-6 → WS-7 → G-Doc
M4: WS-8 → G-Backtest → WS-9, WS-10
M5: WS-11 → WS-12
```

## Step 4: Cross-Reference with Implementation Plan

1. **Identify the WS** from `docs/plan/implementation.md`
2. **Match spec sections** to WS tasks (e.g., §6.3 RSI → WS-3.3)
3. **Respect gate ordering** (G-Features before WS-4, G-Split before WS-5, etc.)
4. **Check existing tasks** to avoid duplication

## Step 5: Gap Analysis

1. List all plan tasks (WS-X.Y) from `docs/plan/implementation.md`
2. Check which have corresponding files in `docs/tasks/`
3. For each gap, create a task following the template
4. Prioritize: M1 before M2, M2 before M3, etc.

## Common Pitfalls

- **Over-scoping**: One task should cover ONE WS-X.Y, not an entire WS
- **Missing anti-fuite tests**: Every feature/split/backtest task MUST include leak checks
- **Config hardcoding**: Every parameter must reference `configs/default.yaml`
- **Spec ambiguity**: If spec is unclear, note the ambiguity — do not guess
