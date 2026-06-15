# Repository Guidelines

## Project Structure & Module Organization
This repository is a lightweight quant backtest workspace. Python utilities live in `scripts/` and run from the repository root with `python3 scripts/<name>.py`. Local strategy definitions live in `strategies/`. The bundled Rust runner lives at `bin/backtest-live-runner` and exports its own strategy/indicator catalog. Backtest reports and diagnostics are stored in `data/`. `docs/` contains AI strategy and engine capability guidance.

## Build, Test, and Development Commands
There is no local package build step. Current backtests call Rust `backtest-live-runner clickhouse-bar-replay`, which reads local ClickHouse `market.klines_1m` and replays 1m OHLC mark prices:

- `python3 scripts/run.py single --strategy bb_rsi_mean_reversion --start 2026-06-10T00:00:00Z --end 2026-06-10T06:00:00Z` runs one live-replay backtest.
- `python3 scripts/run.py monthly --strategy bb_rsi_mean_reversion` runs the built-in six-month monthly report.
- `python3 scripts/run_suite.py --mode continuous --strategy bb_rsi_mean_reversion` runs the suite wrapper for one strategy.
- `bin/backtest-live-runner catalog --format pretty` prints supported indicators, triggers, signal types, risk rules, and runner options.
- `python3 scripts/validate_strategy.py strategies/<name>.json` validates a strategy against the runner-exported catalog.
- `python3 scripts/analyze_trades.py` prints detailed trade-cycle diagnostics for its configured strategy/month.

The wrapper defaults to `bin/backtest-live-runner`. Override with `BACKTEST_LIVE_RUNNER=/path/to/backtest-live-runner`. Local ClickHouse defaults are URL `http://127.0.0.1:8123`, database `market`, user/password `quant/quant`. Use `scripts/sync_data_api_klines.py` to sync only the target exchange/symbol/window from `https://data.becole.com`.

## Coding Style & Naming Conventions
Use Python 3 with 4-space indentation and keep scripts executable with a short usage docstring when they are command-line tools. Prefer `pathlib.Path` for filesystem paths and `argparse` for new CLI options. Name scripts in snake_case, for example `quick_stats.py`; name strategy JSON files in lowercase snake_case, for example `ema_atr_trend.json`.

## Testing Guidelines
This repo currently uses script-based validation rather than a formal test framework. Before changing strategy selection or runner orchestration, inspect `bin/backtest-live-runner catalog --format pretty`, validate the edited JSON, sync the exact target data window, then run a focused live-replay backtest. Use fixed UTC date ranges and symbols in examples so results are reproducible. For JSON strategy edits, run `python3 scripts/validate_strategy.py strategies/<name>.json` and at least one `single` or `run_suite.py --strategy <name>` check.

## Commit & Pull Request Guidelines
No Git history is available in this checkout, so use clear imperative commit messages such as `Add EMA pullback strategy` or `Switch suite to live replay`. Pull requests should include changed scripts or strategies, exact commands run, notable PnL/equity deltas, and assumptions about local ClickHouse data or Rust binary versions.

## Security & Configuration Tips
Do not commit secrets, account identifiers, or private exchange credentials. Treat `data/` as generated or diagnostic output; keep large raw market data in ClickHouse or the upstream market-data stack instead of adding it to the repository.
