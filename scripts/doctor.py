#!/usr/bin/env python3
"""Check local prerequisites for strategy backtesting."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from run import RUNNER, STRATEGIES, clickhouse_env


def ok(message: str) -> None:
    print(f"OK   {message}")


def warn(message: str) -> None:
    print(f"WARN {message}")


def fail(message: str) -> None:
    print(f"FAIL {message}")


def check_python() -> bool:
    if sys.version_info >= (3, 10):
        ok(f"Python {sys.version.split()[0]}")
        return True
    fail("Python 3.10+ is required")
    return False


def check_runner() -> bool:
    if not RUNNER.exists():
        fail(f"backtest-live-runner not found: {RUNNER}")
        return False
    if not RUNNER.is_file():
        fail(f"runner path is not a file: {RUNNER}")
        return False
    ok(f"runner: {RUNNER}")
    return True


def check_catalog() -> bool:
    proc = subprocess.run(
        [str(RUNNER), "catalog", "--format", "json"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        fail("runner catalog command failed")
        print((proc.stderr or proc.stdout).strip()[-1200:])
        return False
    try:
        payload = json.loads(proc.stdout)
    except Exception as exc:  # noqa: BLE001 - diagnostic script
        fail(f"runner catalog returned invalid JSON: {exc}")
        return False
    entries = payload.get("indicator_catalog", {}).get("entries", [])
    if not entries:
        fail("runner catalog has no indicator entries")
        return False
    ok(f"runner catalog exported {len(entries)} indicators")
    return True


def check_clickhouse() -> bool:
    cmd = [
        str(RUNNER),
        "clickhouse-bar-replay",
        "--strategy",
        str(STRATEGIES / "macd_atr_pullback_er_filter.json"),
        "--exchange",
        "binance_um_futures",
        "--symbol",
        "BTCUSDT",
        "--start",
        "2026-06-10T00:00:00Z",
        "--end",
        "2026-06-10T00:05:00Z",
        "--run-id",
        "doctor_smoke",
        "--chunk-size",
        "100",
        "--report-jsonl",
        "/tmp/quant_backtest_doctor_report.jsonl",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=clickhouse_env())
    if proc.returncode != 0:
        fail("ClickHouse/runner smoke failed")
        print((proc.stderr or proc.stdout).strip()[-1200:])
        print(
            "\nIf this is only missing local market data, prepare the test window first:\n"
            "  python3 scripts/sync_data_api_klines.py "
            "--exchange binance_um_futures --symbol BTCUSDT "
            "--start 2026-06-10T00:00:00Z --end 2026-06-10T00:05:00Z"
        )
        return False
    ok("ClickHouse smoke query succeeded")
    return True


def check_strategies() -> bool:
    files = sorted(STRATEGIES.glob("*.json"))
    if not files:
        fail(f"no strategy JSON files under {STRATEGIES}")
        return False
    bad = []
    for path in files:
        try:
            json.loads(path.read_text())
        except Exception as exc:  # noqa: BLE001 - diagnostic script
            bad.append((path, exc))
    if bad:
        for path, exc in bad:
            fail(f"invalid JSON: {path}: {exc}")
        return False
    ok(f"{len(files)} strategy files parse")
    return True


def main() -> None:
    results = [
        check_python(),
        check_runner(),
        check_catalog(),
        check_strategies(),
        check_clickhouse(),
    ]
    if shutil.which("docker"):
        ok("docker CLI found")
    else:
        warn("docker CLI not found; use an external ClickHouse if needed")
    raise SystemExit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
