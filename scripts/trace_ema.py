#!/usr/bin/env python3
"""Trace EMA trend strategy: why do shorts lose in a bear market?"""
import json, subprocess
from pathlib import Path
import pandas as pd

WORK = Path.home() / "quant_backtest"
BIN = Path.home() / "Documents/New project/rust/target/release/backtest-direct-runner"
if not BIN.exists(): BIN = Path.home() / "Documents/New project/rust/target/debug/backtest-direct-runner"
CACHE = Path.home() / "Documents/New project/data/local-market-cache/binance_um_futures"

config = json.loads((WORK / "strategies/ema_trend_simple.json").read_text())
IV, start, end = "15m", "2025-12-01", "2026-06-01"
st, et = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")

dfs = []
for pq in sorted((CACHE / "BTCUSDT" / IV).glob("*.parquet")):
    df = pd.read_parquet(pq)
    if "open_time" not in df.columns: continue
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df = df[(df["open_time"] >= st) & (df["open_time"] < et)]
    if not df.empty: dfs.append(df)
all_data = pd.concat(dfs).sort_values("open_time")

rows = []
for _, row in all_data.iterrows():
    rows.append({
        "exchange": "binance_um_futures", "symbol": "BTCUSDT", "interval": IV,
        "open_time": pd.Timestamp(row["open_time"]).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "close_time": pd.Timestamp(row["close_time"]).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "open": str(row.get("open", 0)), "high": str(row.get("high", 0)),
        "low": str(row.get("low", 0)), "close": str(row.get("close", 0)),
        "volume": str(row.get("volume", 0)), "quote_volume": str(row.get("quote_volume", 0)),
        "trade_count": int(row["trade_count"]) if not pd.isna(row.get("trade_count")) else None,
        "source_row_count": int(row["n_trades"]) if not pd.isna(row.get("n_trades")) else None,
    })

payload = {
    "strategy": config, "rows_by_interval": {IV: rows},
    "start": f"{start}T00:00:00+00:00", "end": f"{end}T00:00:00+00:00",
    "fee_rate": "0.0004",
}
r = subprocess.run([str(BIN)], input=json.dumps(payload), capture_output=True, text=True)
rep = json.loads(r.stdout)
positions = rep.get("positions", [])
orders = rep.get("orders", [])

# Analyze short positions
shorts = [p for p in positions if p.get("side") == "short"]
print(f"Total short positions: {len(shorts)}")
print(f"Short PnL: {sum(float(p.get('pnl',0)) for p in shorts):+,.0f}")
print()

# Show every short position
print(f"{'Entry':<20s} {'Exit':<20s} {'Entry$':>10s} {'Exit$':>10s} {'PnL':>10s} {'Reason':<30s}")
print("-" * 105)
for p in shorts:
    et = p.get("entry_time", "")[:19]
    xt = p.get("exit_time", "")[:19] if p.get("exit_time") else ""
    ep = p.get("entry_price", "?")
    xp = p.get("exit_price", "?") if p.get("exit_price") else ""
    pnl = float(p.get("pnl", 0))
    reason = p.get("rule_label", p.get("rule_id", "?"))
    print(f"{et:<20s} {xt:<20s} {ep:>10s} {xp:>10s} {pnl:>+10.0f} {reason:<30s}")

# Show exit reason breakdown
from collections import Counter
reasons = Counter(p.get("rule_label", p.get("rule_id", "?")) for p in shorts)
print(f"\nExit reasons:")
for r, c in reasons.most_common():
    pnl_sum = sum(float(p.get("pnl",0)) for p in shorts if p.get("rule_label", p.get("rule_id", "")) == r)
    print(f"  {r}: {c} trades, PnL={pnl_sum:+.0f}")

# Show long positions summary for comparison
longs = [p for p in positions if p.get("side") == "long"]
long_pnl = sum(float(p.get("pnl",0)) for p in longs)
print(f"\nLong: {len(longs)} trades, PnL={long_pnl:+.0f}")
