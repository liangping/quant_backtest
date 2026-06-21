#!/usr/bin/env python3
"""Generate synthetic 1m OHLCV data and load it into local ClickHouse.

Uses a geometric Brownian motion model seeded from the symbol name so
results are reproducible. Useful for pipeline testing when the real
data API (data.becole.com) is not reachable.

Usage:
  python3 scripts/gen_synthetic_klines.py \
    --exchange binance_um_futures --symbol BTCUSDT \
    --start 2026-06-10T00:00:00Z --end 2026-06-11T00:00:00Z

  # Longer window for monthly runs:
  python3 scripts/gen_synthetic_klines.py \
    --start 2025-12-01T00:00:00Z --end 2026-06-21T00:00:00Z
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from run import load_dotenv

load_dotenv()

# Realistic BTC params (rough approximation)
INITIAL_PRICE = 105_000.0
ANNUAL_DRIFT = 0.30       # 30% annual upward drift
ANNUAL_VOL = 0.80         # 80% annualised volatility
MINUTES_PER_YEAR = 525_600


def clickhouse_url() -> str:
    base = os.environ.get("CLICKHOUSE_URL", "http://127.0.0.1:8123").rstrip("/")
    user = os.environ.get("CLICKHOUSE_USER", "quant")
    password = os.environ.get("CLICKHOUSE_PASSWORD", "quant")
    query = urllib.parse.urlencode({"user": user, "password": password})
    return f"{base}/?{query}"


def clickhouse_query(sql: str) -> str:
    req = urllib.request.Request(clickhouse_url(), data=sql.encode("utf-8"), method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8")


def parse_time(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    if "T" not in normalized and " " not in normalized:
        normalized = f"{normalized}T00:00:00+00:00"
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000")


def generate_bars(
    exchange: str,
    symbol: str,
    start: datetime,
    end: datetime,
    seed: int | None = None,
) -> list[dict]:
    if seed is None:
        seed = int(hashlib.md5(f"{symbol}{start.isoformat()}".encode()).hexdigest(), 16) % (2**31)
    rng = random.Random(seed)

    mu_per_min = ANNUAL_DRIFT / MINUTES_PER_YEAR
    sigma_per_min = ANNUAL_VOL / math.sqrt(MINUTES_PER_YEAR)

    price = INITIAL_PRICE
    bars = []
    cursor = start
    ingested_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000")

    while cursor < end:
        close_time = cursor + timedelta(minutes=1) - timedelta(milliseconds=1)

        # GBM step for close
        z = rng.gauss(0, 1)
        log_ret = (mu_per_min - 0.5 * sigma_per_min**2) + sigma_per_min * z
        close = price * math.exp(log_ret)

        # Intrabar high/low with simple volatility-scaled spread
        spread_pct = abs(rng.gauss(0, sigma_per_min)) * 2.5 + sigma_per_min * 0.5
        high = max(price, close) * (1 + spread_pct)
        low = min(price, close) * (1 - spread_pct)
        open_ = price

        # Synthetic volume
        volume = rng.uniform(5.0, 50.0) * (1 + abs(log_ret) * 100)
        quote_volume = volume * (open_ + close) / 2

        bars.append({
            "exchange": exchange,
            "symbol": symbol,
            "open_time": iso(cursor),
            "close_time": iso(close_time),
            "open": f"{open_:.8f}",
            "high": f"{high:.8f}",
            "low": f"{low:.8f}",
            "close": f"{close:.8f}",
            "volume": f"{volume:.8f}",
            "quote_volume": f"{quote_volume:.4f}",
            "trade_count": rng.randint(100, 2000),
            "taker_buy_base_volume": f"{volume * 0.5:.8f}",
            "taker_buy_quote_volume": f"{quote_volume * 0.5:.4f}",
            "is_closed": True,
            "source": "synthetic",
            "ingested_at": ingested_at,
        })
        price = close
        cursor += timedelta(minutes=1)

    return bars


def insert_chunk(rows: list[dict]) -> None:
    if not rows:
        return
    database = os.environ.get("CLICKHOUSE_DATABASE", "market")
    columns = list(rows[0].keys())
    prefix = f"INSERT INTO {database}.klines_1m ({', '.join(columns)}) FORMAT JSONEachRow\n"
    body = prefix + "\n".join(json.dumps(r, separators=(",", ":")) for r in rows)
    clickhouse_query(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic 1m OHLCV bars into ClickHouse")
    parser.add_argument("--exchange", default=os.environ.get("BACKTEST_EXCHANGE", "binance_um_futures"))
    parser.add_argument("--symbol", default=os.environ.get("BACKTEST_SYMBOL", "BTCUSDT"))
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--chunk-size", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    start = parse_time(args.start)
    end = parse_time(args.end)
    if start >= end:
        raise SystemExit("--start must be before --end")

    total_minutes = int((end - start).total_seconds() // 60)
    print(f"Generating {total_minutes:,} synthetic 1m bars for {args.exchange}/{args.symbol}")
    print(f"  {iso(start)} → {iso(end)}")

    bars = generate_bars(args.exchange, args.symbol, start, end, seed=args.seed)

    # Insert in chunks
    for i in range(0, len(bars), args.chunk_size):
        chunk = bars[i : i + args.chunk_size]
        insert_chunk(chunk)
        pct = min(100, (i + len(chunk)) * 100 // len(bars))
        print(f"  inserted {i + len(chunk):,}/{len(bars):,} rows ({pct}%)")

    print(f"Done. {len(bars):,} synthetic bars loaded into market.klines_1m.")

    # Verify
    count = clickhouse_query(
        f"SELECT count() FROM market.klines_1m FINAL WHERE exchange='{args.exchange}' AND symbol='{args.symbol}'"
    ).strip()
    print(f"DB count for {args.exchange}/{args.symbol}: {count} rows")


if __name__ == "__main__":
    main()
