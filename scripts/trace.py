#!/usr/bin/env python3
"""Single-bar trace: validate indicator computation, signal evaluation, and fill details."""
import json, subprocess
from pathlib import Path
import pandas as pd

WORK = Path.home() / "quant_backtest"
BIN = Path.home() / "Documents/New project/rust/target/release/backtest-direct-runner"
if not BIN.exists():
    BIN = Path.home() / "Documents/New project/rust/target/debug/backtest-direct-runner"
CACHE = Path.home() / "Documents/New project/data/local-market-cache/binance_um_futures"

# Load BB+RSI strategy (known to trade in Feb)
config = json.loads((WORK / "strategies" / "bb_rsi_mean_reversion.json").read_text())

# Load first 5 days of Feb 2026 (where we know trades happen)
SYM, IV = "BTCUSDT", "5m"
start_ts = pd.Timestamp("2026-02-01", tz="UTC")
end_ts = pd.Timestamp("2026-02-03", tz="UTC")

dfs = []
for pq in sorted((CACHE / SYM / IV).glob("*.parquet")):
    df = pd.read_parquet(pq)
    if "open_time" not in df.columns: continue
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df = df[(df["open_time"] >= start_ts) & (df["open_time"] < end_ts)]
    if not df.empty: dfs.append(df)
all_data = pd.concat(dfs).sort_values("open_time")

rows = []
for _, row in all_data.iterrows():
    rows.append({
        "exchange": "binance_um_futures", "symbol": SYM, "interval": IV,
        "open_time": pd.Timestamp(row["open_time"]).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "close_time": pd.Timestamp(row["close_time"]).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "open": str(row["open"]), "high": str(row["high"]),
        "low": str(row["low"]), "close": str(row["close"]),
        "volume": str(row.get("volume",0)), "quote_volume": str(row.get("quote_volume",0)),
        "trade_count": int(row["trade_count"]) if not pd.isna(row.get("trade_count")) else None,
        "source_row_count": int(row["n_trades"]) if not pd.isna(row.get("n_trades")) else None,
    })

payload = {
    "strategy": config,
    "rows_by_interval": {IV: rows},
    "start": "2026-02-01T00:00:00+00:00",
    "end": "2026-02-03T00:00:00+00:00",
    "fee_rate": "0.0004",
}

r = subprocess.run([str(BIN)], input=json.dumps(payload), capture_output=True, text=True)
report = json.loads(r.stdout)
s = report["summary"]
orders = report["orders"]

print(f"=== BB+RSI $1k/100% — Feb 1-3, 2026 ===")
print(f"Bars processed: {s['processed_bars']}")
print(f"Fills: {s['fill_count']}, Positions: {s.get('position_count', '?')}")
print(f"PnL: {s['total_pnl']}, Equity: {s['final_equity']}")
print()

if not orders:
    print("No orders — no trades triggered in this window")
    # Check if window is too small
    print(f"\nTry a larger window...")

# Show all orders with details
for i, o in enumerate(orders):
    side = o.get("side", "?")
    action = o.get("order_action", o.get("action", "?"))
    rule = o.get("rule_label", o.get("rule_id", "?"))
    qty = o.get("quantity", "?")
    price = o.get("price", "?")
    fee = o.get("fee", "?")
    reason = o.get("reason", "")[:60]
    print(f"  #{i}: {side} {action} qty={qty[:15]}  price={price}  fee={fee}  rule={rule}")
    if reason:
        print(f"       reason: {reason}")
