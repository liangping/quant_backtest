#!/usr/bin/env python3
"""Sync one symbol/time window from data-api into local ClickHouse."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from run import load_dotenv

load_dotenv()

def clickhouse_identifier(value: str) -> str:
    if not value.replace("_", "").isalnum():
        raise SystemExit(f"Unsafe ClickHouse identifier: {value}")
    return value


def schema_sql(database: str) -> str:
    database = clickhouse_identifier(database)
    return f"""
CREATE DATABASE IF NOT EXISTS {database};

CREATE TABLE IF NOT EXISTS {database}.klines_1m
(
    exchange LowCardinality(String),
    symbol LowCardinality(String),
    open_time DateTime64(3, 'UTC'),
    close_time DateTime64(3, 'UTC'),
    open Decimal(38, 18),
    high Decimal(38, 18),
    low Decimal(38, 18),
    close Decimal(38, 18),
    volume Decimal(38, 18),
    quote_volume Decimal(38, 18),
    trade_count UInt32,
    taker_buy_base_volume Decimal(38, 18),
    taker_buy_quote_volume Decimal(38, 18),
    is_closed Bool,
    source LowCardinality(String),
    ingested_at DateTime64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(open_time)
ORDER BY (exchange, symbol, open_time);
"""


def parse_time(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    if "T" not in normalized and " " not in normalized:
        normalized = f"{normalized}T00:00:00+00:00"
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def sql_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def ensure_schema() -> None:
    sql = schema_sql(os.environ.get("CLICKHOUSE_DATABASE", "market"))
    for statement in [part.strip() for part in sql.split(";") if part.strip()]:
        clickhouse_query(statement)


def expected_1m_rows(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds() // 60))


def local_summary(exchange: str, symbol: str, start: datetime, end: datetime) -> dict:
    database = clickhouse_identifier(os.environ.get("CLICKHOUSE_DATABASE", "market"))
    sql = f"""
SELECT
  count(),
  min(open_time),
  max(open_time)
FROM {database}.klines_1m FINAL
WHERE exchange = {sql_string(exchange)}
  AND symbol = {sql_string(symbol)}
  AND open_time >= parseDateTime64BestEffort({sql_string(iso(start))}, 3, 'UTC')
  AND open_time < parseDateTime64BestEffort({sql_string(iso(end))}, 3, 'UTC')
FORMAT JSONEachRow
"""
    text = clickhouse_query(sql).strip()
    if not text:
        return {"count": 0, "min": None, "max": None}
    row = json.loads(text)
    return {"count": int(row.get("count()", 0)), "min": row.get("min(open_time)"), "max": row.get("max(open_time)")}


def split_days(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    chunks = []
    cursor = start
    while cursor < end:
        next_midnight = (cursor + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        chunk_end = min(next_midnight, end)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end
    return chunks


def missing_chunks(exchange: str, symbol: str, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    summary = local_summary(exchange, symbol, start, end)
    expected = expected_1m_rows(start, end)
    print(
        f"local {exchange}/{symbol} {iso(start)} -> {iso(end)} "
        f"rows={summary['count']} expected={expected} min={summary['min']} max={summary['max']}"
    )
    if summary["count"] >= expected:
        return []

    missing = []
    for chunk_start, chunk_end in split_days(start, end):
        day_summary = local_summary(exchange, symbol, chunk_start, chunk_end)
        day_expected = expected_1m_rows(chunk_start, chunk_end)
        if day_summary["count"] < day_expected:
            missing.append((chunk_start, chunk_end))
            print(f"missing {iso(chunk_start)} -> {iso(chunk_end)} rows={day_summary['count']} expected={day_expected}")
        else:
            print(f"skip    {iso(chunk_start)} -> {iso(chunk_end)} rows={day_summary['count']}")
    return missing


def data_api_get(base_url: str, params: dict[str, str | int], ssl_verify: bool) -> list[dict]:
    url = f"{base_url.rstrip('/')}/klines?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "quant-backtest-strategy-lab/1.0",
        },
    )
    context = None if ssl_verify else ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=120, context=context) as resp:
        return json.loads(resp.read().decode("utf-8"))


def row_to_insert(row: dict, ingested_at: str) -> dict:
    return {
        "exchange": row["exchange"],
        "symbol": row["symbol"],
        "open_time": row["open_time"],
        "close_time": row["close_time"],
        "open": row.get("open", "0"),
        "high": row.get("high", "0"),
        "low": row.get("low", "0"),
        "close": row.get("close", "0"),
        "volume": row.get("volume", "0"),
        "quote_volume": row.get("quote_volume", "0"),
        "trade_count": int(row.get("trade_count") or 0),
        "taker_buy_base_volume": "0",
        "taker_buy_quote_volume": "0",
        "is_closed": True,
        "source": "data_api",
        "ingested_at": ingested_at,
    }


def insert_rows(rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    database = clickhouse_identifier(os.environ.get("CLICKHOUSE_DATABASE", "market"))
    prefix = f"INSERT INTO {database}.klines_1m ({', '.join(columns)}) FORMAT JSONEachRow\n"
    body = prefix + "\n".join(json.dumps(row, separators=(",", ":")) for row in rows)
    clickhouse_query(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync one symbol window from data-api")
    parser.add_argument("--data-api-url", default=os.environ.get("DATA_API_URL", "https://data.becole.com"))
    parser.add_argument("--exchange", default=os.environ.get("BACKTEST_EXCHANGE", "binance_um_futures"))
    parser.add_argument("--symbol", default=os.environ.get("BACKTEST_SYMBOL", "BTCUSDT"))
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--interval", default="1m", help="Use 1m for backtest-live-runner")
    parser.add_argument("--limit", type=int, default=20_000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification for DATA_API_URL",
    )
    args = parser.parse_args()

    if args.interval != "1m":
        raise SystemExit("Only --interval 1m can be written to local market.klines_1m")
    if args.limit <= 0 or args.limit > 20_000:
        raise SystemExit("--limit must be between 1 and 20000")

    start = parse_time(args.start)
    end = parse_time(args.end)
    if start >= end:
        raise SystemExit("--start must be before --end")

    ensure_schema()

    total = 0
    chunks = missing_chunks(args.exchange, args.symbol, start, end)
    if not chunks:
        print("Local data already covers requested window; nothing to sync.")
        return

    if args.dry_run:
        expected_fetch = sum(expected_1m_rows(chunk_start, chunk_end) for chunk_start, chunk_end in chunks)
        print(f"Would fetch up to {expected_fetch} rows across {len(chunks)} missing chunks.")
        return

    ssl_verify = os.environ.get("DATA_API_SSL_VERIFY", "true").lower() not in {"0", "false", "no"}
    if args.insecure:
        ssl_verify = False

    step = timedelta(minutes=args.limit)
    for missing_start, missing_end in chunks:
        cursor = missing_start
        while cursor < missing_end:
            chunk_end = min(cursor + step, missing_end)
            rows = data_api_get(
                args.data_api_url,
                {
                    "exchange": args.exchange,
                    "symbol": args.symbol,
                    "interval": args.interval,
                    "start": iso(cursor),
                    "end": iso(chunk_end),
                    "limit": args.limit,
                },
                ssl_verify,
            )
            print(f"fetch   {args.symbol} {iso(cursor)} -> {iso(chunk_end)} rows={len(rows)}")
            total += len(rows)
            if rows:
                ingested_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                insert_rows([row_to_insert(row, ingested_at) for row in rows])
            cursor = chunk_end

    action = "Would sync" if args.dry_run else "Synced"
    print(f"{action} {total} rows for {args.exchange}/{args.symbol} into local ClickHouse")


if __name__ == "__main__":
    main()
