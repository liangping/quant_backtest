#!/usr/bin/env python3
"""Run a small suite through backtest-live-runner clickhouse-bar-replay."""

from __future__ import annotations

import argparse
from run import STRATEGIES, print_report, resolve_strategy, run_one

DEFAULT_STRATEGIES = [
    "bb_rsi_mean_reversion",
    "adx_bb_zscore_mean_reversion",
]

MONTHS = [
    ("2025-12-01", "2026-01-01", "Dec"),
    ("2026-01-01", "2026-02-01", "Jan"),
    ("2026-02-01", "2026-03-01", "Feb"),
    ("2026-03-01", "2026-04-01", "Mar"),
    ("2026-04-01", "2026-05-01", "Apr"),
    ("2026-05-01", "2026-06-01", "May"),
]


def discover_strategies() -> list[str]:
    names = sorted(path.stem for path in STRATEGIES.glob("*.json"))
    return names or DEFAULT_STRATEGIES


def run_strategy(args, strategy: str) -> None:
    strategy_path = resolve_strategy(strategy)
    print(f"\n{strategy_path.name}  {args.exchange}:{args.symbol}  mode={args.mode}")

    if args.mode == "continuous":
        report = run_one(
            strategy_path,
            args.symbol,
            args.exchange,
            args.start,
            args.end,
            args.interval,
            args.chunk_size,
            args.monitor,
        )
        if "error" in report:
            print(f"  ERROR {report['error'][:180]}")
            return
        print_report(report, f"{args.start[:10]}")
        return

    total_pnl = 0.0
    for start, end, label in MONTHS:
        report = run_one(
            strategy_path,
            args.symbol,
            args.exchange,
            start,
            end,
            args.interval,
            args.chunk_size,
            args.monitor,
        )
        if "error" in report:
            print(f"  {label:<12s} ERROR {report['error'][:120]}")
            continue
        total_pnl += float(report.get("summary", {}).get("total_pnl", 0))
        print_report(report, label)
    print(f"  {'TOTAL':<12s} PnL={total_pnl:+.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Live replay backtest suite")
    parser.add_argument("--strategy", help="Strategy name or JSON path")
    parser.add_argument("--mode", choices=["monthly", "continuous"], default="monthly")
    parser.add_argument("--exchange", default="binance_um_futures")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="5m", help="Chart/report sampling interval")
    parser.add_argument("--start", default="2026-06-10T00:00:00Z")
    parser.add_argument("--end", default="2026-06-10T06:00:00Z")
    parser.add_argument("--chunk-size", type=int, default=10000)
    parser.add_argument("--monitor", action="store_true")
    args = parser.parse_args()

    strategies = [args.strategy] if args.strategy else discover_strategies()
    for strategy in strategies:
        run_strategy(args, strategy)


if __name__ == "__main__":
    main()
