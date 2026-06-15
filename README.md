# Quant Backtest Strategy Lab

This repo is a self-contained strategy research workspace for AI-assisted strategy design. It uses the bundled Rust `backtest-live-runner` binary to replay ClickHouse 1m bars through the live-compatible dry-run runtime.

## What Is Included

- `bin/backtest-live-runner`: bundled runner binary.
- `scripts/run.py`: single/monthly backtest wrapper.
- `scripts/run_suite.py`: small multi-strategy runner.
- `scripts/doctor.py`: environment smoke check.
- `strategies/`: editable strategy JSON files.
- `data/backtest_reports/`: generated JSONL reports.
- `docs/AI_STRATEGY_GUIDE.md`: rules for AI agents designing strategies.
- `docs/ENGINE_CAPABILITIES.md`: how AI agents discover runner-supported rules.

## Machine Setup

1. Copy env defaults:

```bash
cp .env.example .env
```

2. Start or point to a local ClickHouse. The sync script can create the
   required `market.klines_1m` table.

Default local settings are:

```text
CLICKHOUSE_URL=http://127.0.0.1:8123
CLICKHOUSE_DATABASE=market
CLICKHOUSE_USER=quant
CLICKHOUSE_PASSWORD=quant
```

3. Run the doctor:

```bash
python3 scripts/doctor.py
```

Note: the bundled binary is macOS arm64. On another platform, replace `bin/backtest-live-runner` with a compatible build or set `BACKTEST_LIVE_RUNNER` in `.env`.

## Prepare Market Data On Demand

Do not sync the whole market. When an AI wants to test one exchange/symbol,
prepare only that symbol and time window from the readonly data API:

```bash
python3 scripts/sync_data_api_klines.py \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --start 2025-12-01T00:00:00Z \
  --end 2026-06-01T00:00:00Z
```

The script first checks local ClickHouse coverage. Fully present days are
skipped; only missing days are fetched from `https://data.becole.com/klines`.
If Python certificate validation fails on a new machine, set
`DATA_API_SSL_VERIFY=false` in `.env` or pass `--insecure`.

## Common Commands

Inspect engine capabilities from the bundled binary:

```bash
bin/backtest-live-runner catalog --format pretty
```

Validate a strategy against the runner catalog:

```bash
python3 scripts/validate_strategy.py strategies/macd_atr_pullback_er_filter.json
```

Single backtest:

```bash
python3 scripts/run.py single \
  --strategy macd_atr_pullback_er_filter \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --interval 15m \
  --start 2026-06-10T00:00:00Z \
  --end 2026-06-10T06:00:00Z
```

Monthly split:

```bash
python3 scripts/run.py monthly --strategy macd_atr_pullback_er_filter --interval 15m
```

Continuous suite check:

```bash
python3 scripts/run_suite.py --mode continuous --strategy macd_atr_pullback_er_filter
```

## Strategy Design Workflow

1. Run `bin/backtest-live-runner catalog --format pretty` and use only supported fields.
2. Copy an existing JSON in `strategies/`.
3. Change one idea at a time: entry trigger, regime filter, sizing, or exit.
4. Validate the strategy JSON with `scripts/validate_strategy.py`.
5. Sync the exact symbol/window needed for the test.
6. Run monthly and continuous windows.
7. Compare total return, weakest month, fills, positions, and drawdown.
8. Keep promising reports in `data/backtest_reports/`; delete noisy one-off outputs.

Important: monthly split resets runtime state each month. Always validate promising strategies with a continuous run before treating results as realistic.
