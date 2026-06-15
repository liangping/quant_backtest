#!/usr/bin/env python3
"""Deep dive: show every position's PnL, side, and size for server_246_pct50."""
import json, subprocess
from pathlib import Path
import pandas as pd

WORK = Path.home() / "quant_backtest"
BIN = Path.home() / "Documents/New project/rust/target/release/backtest-direct-runner"
if not BIN.exists(): BIN = Path.home() / "Documents/New project/rust/target/debug/backtest-direct-runner"
CACHE = Path.home() / "Documents/New project/data/local-market-cache/binance_um_futures"

config = json.loads((WORK / "strategies/server_246_pct50.json").read_text())
INTERVAL = "5m"
months = [("2025-12-01","2026-01-01"),("2026-01-01","2026-02-01"),("2026-02-01","2026-03-01"),
          ("2026-03-01","2026-04-01"),("2026-04-01","2026-05-01"),("2026-05-01","2026-06-01")]

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
    rep = json.loads(r.stdout); s = rep["summary"]
    positions = rep.get("positions", [])
    
    # Analyze loss distribution
    pnls = [float(p.get("pnl",0)) for p in positions]
    sides = [p.get("side","?") for p in positions]
    
    total_loss = sum(x for x in pnls if x < 0)
    total_win = sum(x for x in pnls if x > 0)
    big_losses = sorted([(x, sides[i]) for i,x in enumerate(pnls) if x < -50], key=lambda x: x[0])
    
    loss_long = sum(x for i,x in enumerate(pnls) if x < 0 and sides[i] == "Long")
    loss_short = sum(x for i,x in enumerate(pnls) if x < 0 and sides[i] == "Short")
    win_long = sum(x for i,x in enumerate(pnls) if x > 0 and sides[i] == "Long")
    win_short = sum(x for i,x in enumerate(pnls) if x > 0 and sides[i] == "Short")
    
    print(f"\n{'='*60}")
    print(f"  {label}  —  PnL={float(s.get('total_pnl',0)):+.1f}  Trades={len(positions)}")
    print(f"  Win: +{total_win:.0f} (Long: +{win_long:.0f}  Short: +{win_short:.0f})")
    print(f"  Loss: {total_loss:.0f} (Long: {loss_long:.0f}  Short: {loss_short:.0f})")
    
    if big_losses:
        print(f"  Big losers (>$50):")
        for pnl, side in big_losses:
            print(f"    {side:5s} {pnl:+.0f}")
    
    # Show worst 5 and best 5
    sorted_pnls = sorted(zip(pnls, sides), key=lambda x: x[0])
    print(f"  Worst 5: {[f'{s}={p:+.0f}' for p,s in sorted_pnls[:5]]}")
    print(f"  Best 5:  {[f'{s}={p:+.0f}' for p,s in sorted_pnls[-5:]]}")
