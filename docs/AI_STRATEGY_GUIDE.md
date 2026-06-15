# AI Strategy Guide

Use this guide when an AI agent designs or modifies strategies in this repo.

## Operating Model

This project is self-contained for strategy research:

- Use `bin/backtest-live-runner`; do not require the private Rust source tree.
- Discover supported indicators and rules with `bin/backtest-live-runner catalog --format pretty`.
- Use local ClickHouse for execution data.
- Use `scripts/sync_data_api_klines.py` to prepare only the exchange/symbol/window needed for a test.
- Store strategy JSON under `strategies/`.
- Store generated reports under `data/backtest_reports/`.

## Data Preparation

Before running a strategy, sync only the requested symbol and time window:

```bash
python3 scripts/sync_data_api_klines.py \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --start 2025-12-01T00:00:00Z \
  --end 2026-06-01T00:00:00Z
```

The sync script first checks local coverage. If the requested days are already present, it skips them. If Python cannot validate the remote TLS certificate on a new machine, use `DATA_API_SSL_VERIFY=false` in `.env` or pass `--insecure`.

## Strategy Rules

Before editing JSON, inspect the current runner contract:

```bash
bin/backtest-live-runner catalog --format pretty
```

Do not infer support from old examples. If an indicator, trigger, signal type, or risk rule is not present in the catalog, do not use it.

Prefer small, testable changes:

- Change one idea at a time: entry, filter, exit, or sizing.
- Add regime filters before increasing exposure.
- For trend-following with Chandelier exits, avoid low-efficiency sideways periods.
- Treat `position_pct`, leverage, and exposure caps as risk controls, not profit targets.
- Keep strategy names descriptive, such as `macd_atr_pullback_er_filter`.

Common signal tools currently used:

- `macd` for directional entry.
- `atr` with `position_indicator` for Chandelier-style exits.
- `er`, `adx`, `chop`, or `natr` for regime filters.
- `composite` signals to combine entry and filter conditions.

## Validation Standard

First validate JSON against the runner-exported catalog:

```bash
python3 scripts/validate_strategy.py strategies/<name>.json
```

Always run both:

```bash
python3 scripts/run.py monthly --strategy <name> --interval 15m
python3 scripts/run.py single --strategy <name> --interval 15m --start <start> --end <end>
```

Monthly split is useful for diagnosing regimes, but it resets runtime state each month. Continuous runs are closer to real operation and must be checked before calling a strategy promising.

Record at least:

- total PnL and final equity
- weakest month
- number of loss months
- fills and positions
- max drawdown
- whether a continuous run behaves consistently with monthly diagnostics

## Current Baseline

`strategies/macd_atr_pullback_er_filter.json` is the current candidate baseline. It uses:

- 15m MACD golden cross entry
- ER(14) >= 0.2 regime filter
- 3 ATR Chandelier exit from `highest_since_entry`
- long-only BTCUSDT

Known caveat: monthly split and long continuous runs may diverge because runtime state persists continuously. Investigate continuous behavior before optimizing only monthly results.
