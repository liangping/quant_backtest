#!/usr/bin/env python3
"""Stats for server 246 long-only variant."""
import json, subprocess, sys
from pathlib import Path
import pandas as pd

WORK = Path.home() / "quant_backtest"
BIN = Path.home() / "Documents/New project/rust/target/release/backtest-direct-runner"
if not BIN.exists(): BIN = Path.home() / "Documents/New project/rust/target/debug/backtest-direct-runner"
CACHE = Path.home() / "Documents/New project/data/local-market-cache/binance_um_futures"

strat = sys.argv[1] if len(sys.argv) > 1 else "server_246_long"
interval_arg = sys.argv[2] if len(sys.argv) > 2 else None
config = json.loads((WORK / "strategies" / f"{strat}.json").read_text())
if interval_arg:
    INTERVAL = interval_arg
else:
    INTERVAL = "5m"
    # Auto-detect from signals
    for s in config.get("signals", []):
        if s.get("interval") and s["interval"] != "5m":
            INTERVAL = s["interval"]
            break
months = [("2025-12-01","2026-01-01"),("2026-01-01","2026-02-01"),("2026-02-01","2026-03-01"),
          ("2026-03-01","2026-04-01"),("2026-04-01","2026-05-01"),("2026-05-01","2026-06-01")]

print(f"Strategy: {strat}  ({INTERVAL}, lev={config['basic']['leverage']}x, pct={config['long']['entry_rules'][0]['position_pct']}%, cap={config['basic']['initial_capital']})")
print(f"{'Month':<10s} {'Tr':>5s} {'W':>4s} {'L':>4s} {'Win%':>7s} {'PF':>7s} {'PnL':>10s} {'Eq':>10s}")
print("-"*65)
total_pnl = 0
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
    if r.returncode != 0: continue
    rep = json.loads(r.stdout); s = rep["summary"]
    positions = rep.get("positions", [])
    wins = sum(1 for p in positions if float(p.get("pnl",0)) > 0)
    losses = sum(1 for p in positions if float(p.get("pnl",0)) < 0)
    gp = sum(float(p.get("pnl",0)) for p in positions if float(p.get("pnl",0)) > 0)
    gl = sum(abs(float(p.get("pnl",0))) for p in positions if float(p.get("pnl",0)) < 0)
    total = wins + losses
    wr = (wins/total*100) if total > 0 else 0
    pf = (gp/gl) if gl > 0 else (999 if gp > 0 else 0)
    pnl = float(s.get("total_pnl",0)); eq = float(s.get("final_equity",0))
    total_pnl += pnl
    print(f"{label:<10s} {total:>5d} {wins:>4d} {losses:>4d} {wr:>6.1f}% {pf:>6.2f} {pnl:>+10.1f} {eq:>10.1f}")
print(f"{'TOTAL':<10s} {total_pnl:>+10.1f}")
