# Engine Capabilities

AI agents must read capabilities directly from the bundled runner. The binary is the source of truth, so strategy support moves with the runner version instead of a hand-maintained file.

## Recommended Flow

1. Run `bin/backtest-live-runner catalog --format pretty` before creating or editing a strategy.
2. Use only listed `indicator_id`, `trigger`, `signal_type`, and rule enum values.
3. Save strategy JSON under `strategies/`.
4. Run `python3 scripts/validate_strategy.py strategies/<name>.json`.
5. Sync the exact symbol/window, then run the backtest.

## Runner Catalog

Use the catalog command to inspect the live contract:

```bash
bin/backtest-live-runner catalog --format pretty
```

`scripts/validate_strategy.py` calls the same command internally. If the command is missing, the bundled runner is too old for AI-driven strategy generation in this repo.

## What the Catalog Covers

- Technical indicators such as `macd`, `rsi`, `atr`, `er`, `adx`, `zscore`, `chop`, and `bb`.
- Trigger names such as `golden_cross`, `death_cross`, `trend_strong`, and Bollinger band crossings.
- Strategy composition primitives: `single`, `composite`, `expression`, `position_atr`, and `position_indicator`.
- Position and risk controls: `long_only`, `short_only`, `switch`, Chandelier-style ATR exits, max loss, max exposure, cooldown, entry lock, and margin coefficient rules.

If a desired feature is missing from the catalog, do not invent the JSON field. Add it to the engine first, export a new catalog, then update strategies.
