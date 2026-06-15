#!/usr/bin/env python3
"""Run live-compatible backtests through Rust backtest-live-runner.

The current backtest path is ClickHouse 1m OHLC replay into the dry-run live
robot runtime. The legacy backtest-direct-runner path is intentionally unused.

Usage:
  python3 scripts/run.py single --strategy bb_rsi_mean_reversion --start 2026-06-10 --end 2026-06-11
  python3 scripts/run.py monthly --strategy bb_rsi_mean_reversion --interval 5m
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parent.parent
STRATEGIES = WORK / "strategies"
DATA_OUT = WORK / "data" / "backtest_reports"
BIN_DIR = WORK / "bin"


def load_dotenv(path: Path = WORK / ".env") -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_dotenv()


def default_runner() -> Path:
    configured = os.environ.get("BACKTEST_LIVE_RUNNER") or os.environ.get("BACKTEST_RUNNER")
    if configured:
        return Path(configured)
    return BIN_DIR / "backtest-live-runner"


RUNNER = default_runner()


def resolve_strategy(value: str) -> Path:
    candidate = Path(value).expanduser()
    if candidate.exists():
        return candidate

    for base in (STRATEGIES, STRATEGIES / "_archive"):
        path = base / f"{value}.json"
        if path.exists():
            return path

    raise SystemExit(f"Strategy not found: {value}")


def rfc3339(value: str) -> str:
    if "T" in value:
        return value
    return f"{value}T00:00:00Z"


def clean_run_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").lower()


def clickhouse_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CLICKHOUSE_URL", "http://127.0.0.1:8123")
    env.setdefault("CLICKHOUSE_DATABASE", "market")
    env.setdefault("CLICKHOUSE_USER", "quant")
    env.setdefault("CLICKHOUSE_PASSWORD", "quant")
    return env


def run_one(
    strategy_path: Path,
    symbol: str,
    exchange: str,
    start: str,
    end: str,
    chart_interval: str | None,
    chunk_size: int,
    monitor: bool,
) -> dict:
    if not RUNNER.exists():
        return {"error": f"backtest-live-runner not found: {RUNNER}"}

    DATA_OUT.mkdir(parents=True, exist_ok=True)
    run_id = clean_run_id(f"{strategy_path.stem}_{symbol}_{start}_{end}")
    report_path = DATA_OUT / f"{run_id}.jsonl"

    cmd = [
        str(RUNNER),
        "clickhouse-bar-replay",
        "--strategy",
        str(strategy_path),
        "--exchange",
        exchange,
        "--symbol",
        symbol,
        "--start",
        rfc3339(start),
        "--end",
        rfc3339(end),
        "--run-id",
        run_id,
        "--chunk-size",
        str(chunk_size),
        "--report-jsonl",
        str(report_path),
    ]
    if chart_interval:
        cmd.extend(["--chart-interval", chart_interval])
    if monitor:
        cmd.extend(["--monitor", "--monitor-every-bars", "1000"])

    proc = subprocess.run(cmd, capture_output=True, text=True, env=clickhouse_env())
    if proc.returncode != 0:
        return {"error": (proc.stderr or proc.stdout).strip()[-2000:]}

    if not report_path.exists():
        return {"error": f"runner completed without report: {report_path}"}

    lines = [line for line in report_path.read_text().splitlines() if line.strip()]
    if not lines:
        return {"error": f"empty report: {report_path}"}

    report = json.loads(lines[-1])
    report["_report_path"] = str(report_path)
    return report


def print_report(report: dict, label: str = "") -> None:
    s = report.get("summary", {})
    print(
        f"  {label:<12s} bars={s.get('processed_bars', 0):>5d} "
        f"fills={s.get('fill_count', 0):>4d} "
        f"positions={s.get('position_count', 0):>4d} "
        f"PnL={float(s.get('total_pnl', 0)):>+10.4f} "
        f"equity={float(s.get('final_equity', 0)):>10.4f} "
        f"ret={s.get('return_pct', '?'):>10s} "
        f"dd={s.get('max_drawdown_pct', '?'):>8s}"
    )


def cmd_single(args) -> None:
    strategy_path = resolve_strategy(args.strategy)
    print(
        f"Strategy: {strategy_path.name}  {args.exchange}:{args.symbol}  "
        f"{args.start} -> {args.end}  chart={args.interval}"
    )
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
        print(f"ERROR: {report['error']}", file=sys.stderr)
        raise SystemExit(1)
    print_report(report)
    print(f"  report: {report['_report_path']}")


def cmd_monthly(args) -> None:
    strategy_path = resolve_strategy(args.strategy)
    months = [
        ("2025-12-01", "2026-01-01"),
        ("2026-01-01", "2026-02-01"),
        ("2026-02-01", "2026-03-01"),
        ("2026-03-01", "2026-04-01"),
        ("2026-04-01", "2026-05-01"),
        ("2026-05-01", "2026-06-01"),
    ]

    print(f"Strategy: {strategy_path.name}  {args.exchange}:{args.symbol}  monthly")
    total_pnl = 0.0
    for start, end in months:
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
        label = start[:7]
        if "error" in report:
            print(f"  {label:<12s} ERROR {report['error'][:120]}")
            continue
        total_pnl += float(report.get("summary", {}).get("total_pnl", 0))
        print_report(report, label)
    print(f"  {'TOTAL':<12s} PnL={total_pnl:+.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Live replay ClickHouse backtest runner")
    sub = parser.add_subparsers(dest="cmd")

    def add_common(p):
        p.add_argument("--strategy", required=True, help="Strategy name or JSON path")
        p.add_argument("--exchange", default="binance_um_futures")
        p.add_argument("--symbol", default="BTCUSDT")
        p.add_argument("--interval", default="5m", help="Chart/report sampling interval")
        p.add_argument("--chunk-size", type=int, default=10000)
        p.add_argument("--monitor", action="store_true")

    single = sub.add_parser("single", help="Single live replay backtest")
    add_common(single)
    single.add_argument("--start", required=True)
    single.add_argument("--end", required=True)

    monthly = sub.add_parser("monthly", help="Built-in six-month monthly report")
    add_common(monthly)

    args = parser.parse_args()
    if args.cmd == "single":
        cmd_single(args)
    elif args.cmd == "monthly":
        cmd_monthly(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
