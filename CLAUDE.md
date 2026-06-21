# CLAUDE.md

Guidance for AI assistants (Claude Code and others) working in this repository.
For human-facing onboarding see `README.md`; for the condensed contributor
conventions see `AGENTS.md`. This file is the most detailed map of how the repo
fits together.

## What This Repo Is

A self-contained **quant strategy research workspace** for AI-assisted strategy
design. It does not contain a trading engine source tree. Instead it bundles a
prebuilt Rust binary (`bin/backtest-live-runner`) that replays historical 1m
OHLC bars from a local ClickHouse database through the same dry-run runtime used
for live trading. Strategies are plain JSON files; Python scripts in `scripts/`
orchestrate the runner and analyze its output.

The core loop is: **edit a strategy JSON → validate it against the runner's
catalog → sync the needed market data → run a backtest → read the report.**

## Repository Layout

- `bin/backtest-live-runner` — the prebuilt backtest engine. **Source of truth**
  for which indicators, triggers, signal types, and risk rules exist. It exports
  its own capability catalog (see "The Runner Catalog" below).
- `strategies/*.json` — active, editable strategy definitions.
- `strategies/_archive/*.json` — retired/experimental strategies kept for
  reference. `scripts/run.py` resolves names from `_archive/` as a fallback.
- `scripts/*.py` — Python 3.10+ orchestration and analysis utilities, run from
  the repo root as `python3 scripts/<name>.py`. They share helpers by importing
  from `run.py` (e.g. `from run import RUNNER, run_one, print_report`).
- `data/backtest_reports/` — generated JSONL reports (gitignored except
  `.gitkeep`).
- `data/` — generated diagnostics and local market-data scratch (gitignored).
- `docs/AI_STRATEGY_GUIDE.md` — rules for designing strategies.
- `docs/ENGINE_CAPABILITIES.md` — how to discover runner-supported rules.
- `BUG_REPORT_cash_basis.md` — a standing bug report about the runner's
  `cash_basis`/`realized_pnl` accounting (the runner source lives elsewhere; this
  repo only documents the issue).
- `.env.example` — template for local config; copy to `.env`.

## Platform Caveat — Read First

This repository runs on **Linux x86-64** (currently deployed in cloud). The
`bin/backtest-live-runner` is an ELF x86-64 Linux binary. However, **backtests
still require ClickHouse**:

- **Local development**: See [LOCAL_SETUP.md](LOCAL_SETUP.md) to install
  ClickHouse via Docker Compose, Homebrew, or system packages.
- **This cloud environment**: Network restrictions prevent Docker pulls and
  ClickHouse installation. Work locally and push strategy updates from this
  branch.

Before assuming a backtest can execute:

- Check the binary's platform (`file bin/backtest-live-runner`).
- On a non-macOS host, the runner must be replaced with a compatible build or
  pointed elsewhere via `BACKTEST_LIVE_RUNNER=/path/to/runner` in `.env`.
- A runnable backtest also requires a **local ClickHouse** populated with the
  target symbol/window. None of that is provisioned by default.

If you are asked to "run" a strategy in an environment that lacks a compatible
runner or ClickHouse, say so explicitly rather than reporting a failed run as a
strategy result. Editing, validating (statically), and reasoning about
strategies does not require the runner; executing backtests does.

## Environment Configuration

**Cloud environment**: PostgreSQL 16 is available (`localhost:5432`). Use for
strategy metadata, backtest archival, and analysis results. See
**[POSTGRES_SETUP.md](POSTGRES_SETUP.md)**.

**Local development**: See **[LOCAL_SETUP.md](LOCAL_SETUP.md)** for step-by-step
ClickHouse installation (Docker Compose, Homebrew, or system packages).

Copy `.env.example` to `.env` and adjust. Scripts load `.env` via
`run.load_dotenv()` (only sets keys not already in the environment). Keys:

- `BACKTEST_LIVE_RUNNER` — override path to the runner binary (default
  `bin/backtest-live-runner`). `BACKTEST_RUNNER` is also accepted.
- `CLICKHOUSE_URL` (default `http://127.0.0.1:8123`), `CLICKHOUSE_DATABASE`
  (`market`), `CLICKHOUSE_USER` (`quant`), `CLICKHOUSE_PASSWORD` (`quant`).
- `DATA_API_URL` (default `https://data.becole.com`) — readonly market-data API.
- `DATA_API_SSL_VERIFY=false` / `--insecure` — bypass TLS validation if certs
  fail on a new machine.
- `BACKTEST_EXCHANGE` (`binance_um_futures`), `BACKTEST_SYMBOL` (`BTCUSDT`) —
  defaults used in examples.

## Core Workflows

### 1. Environment smoke check

```bash
python3 scripts/doctor.py
```

Checks Python ≥3.10, runner presence, that the runner catalog command works and
exports indicators, that every `strategies/*.json` parses, and runs a tiny
ClickHouse replay smoke test.

### 2. Discover engine capabilities (always before editing JSON)

```bash
bin/backtest-live-runner catalog --format pretty   # human-readable
bin/backtest-live-runner catalog --format json     # machine-readable
```

The catalog is the **only** authoritative list of supported `indicator_id`,
`trigger`, `signal_type`, condition/composite operators, exit actions/quantities,
risk rule types, and ATR/position reference enums. Do not infer support from
existing JSON files — capabilities move with the runner version.

### 3. Validate a strategy against the catalog

```bash
python3 scripts/validate_strategy.py strategies/<name>.json
```

This loads `catalog --format json` and statically checks signal IDs,
indicator/trigger validity, composite refs, position-indicator/ATR fields, entry
`position_pct` totals, exit actions/quantities, switch rules, and risk rule
types. **This still requires a runnable runner binary** (it shells out to
`catalog`). Run this on every JSON edit.

### 4. Prepare market data (only the window you need)

```bash
python3 scripts/sync_data_api_klines.py \
  --exchange binance_um_futures --symbol BTCUSDT \
  --start 2025-12-01T00:00:00Z --end 2026-06-01T00:00:00Z
```

Do **not** sync the whole market. The script creates `market.klines_1m` if
needed, checks existing local coverage, and fetches only missing days from
`DATA_API_URL`. Use `--insecure` / `DATA_API_SSL_VERIFY=false` for cert issues.

### 5. Run backtests

```bash
# Single fixed window
python3 scripts/run.py single --strategy macd_atr_pullback_er_filter \
  --interval 15m --start 2026-06-10T00:00:00Z --end 2026-06-10T06:00:00Z

# Built-in six-month monthly report (Dec 2025 – May 2026)
python3 scripts/run.py monthly --strategy macd_atr_pullback_er_filter --interval 15m

# Suite wrapper: --mode monthly (per-month) or --mode continuous (one window)
python3 scripts/run_suite.py --mode continuous --strategy macd_atr_pullback_er_filter
```

`run.py` invokes `backtest-live-runner clickhouse-bar-replay`, writes a JSONL
report to `data/backtest_reports/<run_id>.jsonl`, and prints the last line's
summary (bars, fills, positions, PnL, equity, return %, max drawdown). Defaults:
exchange `binance_um_futures`, symbol `BTCUSDT`, interval `5m`, chunk size 10000.

**Important:** `monthly` resets runtime state at each month boundary, so it is a
regime diagnostic, not a realistic equity curve. Always confirm a promising
strategy with a **continuous** run before trusting results.

## Strategy JSON Structure

Strategies are objects with: top-level `name`, `position_mode`
(`long_only`/`short_only`/`switch`), a `basic` block (exchange, symbol,
`initial_capital`, `leverage`, `compound_profit`), a flat `signals` list, `long`
and `short` blocks (each with `entry_rules`/`exit_rules`), `switch_rules`, and
`strategy_risk_rules`. See `strategies/macd_atr_pullback_er_filter.json` (the
current baseline candidate) for a complete, validated example.

Signal types in use: `single` (one indicator + `trigger` or
`condition_operator`/`value`), `composite` (combine prior signals with an
`operator` like `all`), `position_indicator`/`position_atr` (Chandelier-style ATR
trailing exits referencing `highest_since_entry`), and `expression`. Entry rules
reference a `trigger_signal` and set `position_pct`; exit rules set `exit_action`
(e.g. `stop_loss`) and `quantity` (e.g. `full_position`). Risk rules include
`max_loss_percent`, `max_exposure_percent`, and `cooldown_bars`.

Numeric fields are commonly **strings** (e.g. `"leverage": "10"`,
`"position_pct": "200"`); match the surrounding style when editing.

## Strategy Design Conventions

- Change **one idea at a time** (entry, regime filter, sizing, or exit) so a
  result is attributable.
- Add regime filters (`er`, `adx`, `chop`, `natr`) before increasing exposure.
- Treat `position_pct`, leverage, and exposure caps as risk controls, not profit
  knobs.
- Name strategy files in lowercase `snake_case` and make the name descriptive
  (e.g. `macd_atr_pullback_er_filter`). The JSON `name` should match the file
  stem.
- For each promising strategy, record: total PnL/final equity, weakest month,
  number of loss months, fills, positions, max drawdown, and whether continuous
  behavior matches the monthly diagnostic.
- Keep useful reports under `data/backtest_reports/`; delete noisy one-offs.

## Python / Scripts Conventions

- Python 3.10+ (uses `from __future__ import annotations`, `X | None`, `UTC`).
- 4-space indentation; `argparse` for CLIs; `pathlib.Path` for filesystem paths.
- Scripts are executable, carry a short usage docstring, and run from repo root.
- Shared logic lives in `scripts/run.py`; other scripts import from it rather
  than duplicating runner/ClickHouse plumbing. There are many small analysis
  scripts (`analyze_trades.py`, `stats.py`, `compare_*.py`, `trace*.py`, etc.) —
  reuse `run.run_one` / `run.print_report` when adding new ones.
- No formal test framework: validation is the catalog check plus focused
  backtests. Use fixed UTC date ranges and explicit symbols in examples so runs
  are reproducible.
- `scripts/_tmp_*.py` is gitignored; use that prefix for throwaway scratch.

## Git & Contribution Conventions

- Active development branch for this work: `claude/claude-md-docs-vacpet`. Commit
  and push there; never push to `main` without explicit permission.
- Use clear imperative commit messages (e.g. `Add EMA pullback strategy`,
  `Switch suite to live replay`).
- Do **not** create pull requests unless explicitly asked.
- Never commit secrets, account identifiers, or exchange credentials. Keep large
  raw market data in ClickHouse, not in the repo. `data/` is generated output.

## Gotchas

- The runner binary is platform-specific (see "Platform Caveat"); a missing or
  incompatible binary makes both `validate_strategy.py` and any backtest fail.
- Backtests need both a compatible runner **and** populated ClickHouse data for
  the exact window — sync first.
- `monthly` mode resets state per month; only `continuous` reflects real
  operation.
- The catalog — not older JSON examples — defines what fields are legal. If a
  feature is missing from the catalog, it must be added to the engine first; do
  not invent JSON fields.
- See `BUG_REPORT_cash_basis.md`: realized PnL / final equity reported by the
  runner may be affected by a known `cash_basis` margin-accounting bug. Be
  cautious when interpreting absolute PnL until that is resolved upstream.
