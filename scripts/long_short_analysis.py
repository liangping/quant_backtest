#!/usr/bin/env python3
"""Analyze long vs short performance for 296@15m."""
import json, subprocess
from pathlib import Path
import pandas as pd

WORK = Path.home() / "quant_backtest"
BIN = Path.home() / "Documents/New project/rust/target/release/backtest-direct-runner"
if not BIN.exists(): BIN = Path.home() / "Documents/New project/rust/target/debug/backtest-direct-runner"
CACHE = Path.home() / "Documents/New project/data/local-market-cache/binance_um_futures"

config = json.loads((WORK / "strategies/server_296_15m.json").read_text())
INTERVAL = "15m"
months = [("2025-12-01","2026-01-01"),("2026-01-01","2026-02-01"),("2026-02-01","2026-03-01"),
          ("2026-03-01","2026-04-01"),("2026-04-01","2026-05-01"),("2026-05-01","2026-06-01")]

print(f"{'Month':<8s} {'Side':>5s} {'Tr':>4s} {'W':>4s} {'L':>4s} {'Win%':>7s} {'PF':>7s} {'PnL':>10s}")
print("-"*60)

for start, end in months:
    label = start[:7]
    st, et = pd.Timestamp(start,tz="UTC"), pd.Timestamp(end,tz="UTC")
    dfs = []
    for pq in sorted((CACHE/"BTCUSDT"/INTERVAL).glob("*.parquet")):
        df = pd.read_parquet(pq)
        if "open_time" not in df.columns: continue
        df["open_time"] = pd.to_datetime(df["open_time"],utc=True)
        df = df[(df["open_time"]>=st)&(df["open_time"]<et)]
        if not df.empty: dfs.append(df)
    if not dfs: continue
    all_data = pd.concat(dfs).sort_values("open_time")
    rows = []
    for _, row in all_data.iterrows():
        rows.append({"exchange":"binance_um_futures","symbol":"BTCUSDT","interval":INTERVAL,
            "open_time":pd.Timestamp(row["open_time"]).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "close_time":pd.Timestamp(row["close_time"]).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "open":str(row.get("open",0)),"high":str(row.get("high",0)),
            "low":str(row.get("low",0)),"close":str(row.get("close",0)),
            "volume":str(row.get("volume",0)),"quote_volume":str(row.get("quote_volume",0)),
            "trade_count":int(row["trade_count"]) if not pd.isna(row.get("trade_count")) else None,
            "source_row_count":int(row["n_trades"]) if not pd.isna(row.get("n_trades")) else None})
    payload = {"strategy":config,"rows_by_interval":{INTERVAL:rows},
               "start":f"{start}T00:00:00+00:00","end":f"{end}T00:00:00+00:00","fee_rate":"0.0004"}
    r = subprocess.run([str(BIN)], input=json.dumps(payload), capture_output=True, text=True)
    rep = json.loads(r.stdout)
    positions = rep.get("positions", [])
    
    for side_name in ["Long", "Short"]:
        side_positions = [p for p in positions if p.get("side", "") == side_name]
        if not side_positions: continue
        pnls = [float(p.get("pnl",0)) for p in side_positions]
        wins = sum(1 for x in pnls if x > 0)
        losses = sum(1 for x in pnls if x < 0)
        gp = sum(x for x in pnls if x > 0)
        gl = sum(abs(x) for x in pnls if x < 0)
        total = wins + losses
        wr = (wins/total*100) if total > 0 else 0
        pf = (gp/gl) if gl > 0 else (999 if gp > 0 else 0)
        net = sum(pnls)
        # Show worst 3
        worst = sorted(pnls)[:3]
        best = sorted(pnls)[-3:]
        print(f"{label:<8s} {side_name:>5s} {total:>4d} {wins:>4d} {losses:>4d} {wr:>6.1f}% {pf:>6.2f} {net:>+10.1f}  worst={[f'{x:+.0f}' for x in worst]}  best={[f'{x:+.0f}' for x in best]}")
