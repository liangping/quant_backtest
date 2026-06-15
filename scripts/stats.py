#!/usr/bin/env python3
"""Run EMA+ADX strategy monthly with detailed trade stats."""
import json, subprocess
from pathlib import Path
import pandas as pd

WORK = Path.home() / "quant_backtest"
BIN = Path.home() / "Documents/New project/rust/target/release/backtest-direct-runner"
if not BIN.exists(): BIN = Path.home() / "Documents/New project/rust/target/debug/backtest-direct-runner"
CACHE = Path.home() / "Documents/New project/data/local-market-cache/binance_um_futures"

config = json.loads((WORK / "strategies/ema_adx_switch.json").read_text())
months = [("2025-12-01","2026-01-01"),("2026-01-01","2026-02-01"),("2026-02-01","2026-03-01"),
          ("2026-03-01","2026-04-01"),("2026-04-01","2026-05-01"),("2026-05-01","2026-06-01")]

print(f"{'Month':<10s} {'Trades':>7s} {'Win':>5s} {'Loss':>5s} {'Win%':>7s} {'PF':>7s} {'PnL':>10s} {'Eq':>10s}")
print("-"*70)

for start, end in months:
    label = start[:7]
    st, et = pd.Timestamp(start,tz="UTC"), pd.Timestamp(end,tz="UTC")
    dfs = []
    for pq in sorted((CACHE/"BTCUSDT"/"15m").glob("*.parquet")):
        df = pd.read_parquet(pq)
        if "open_time" not in df.columns: continue
        df["open_time"] = pd.to_datetime(df["open_time"],utc=True)
        df = df[(df["open_time"]>=st)&(df["open_time"]<et)]
        if not df.empty: dfs.append(df)
    if not dfs: continue
    all_data = pd.concat(dfs).sort_values("open_time")
    rows = []
    for _, row in all_data.iterrows():
        rows.append({"exchange":"binance_um_futures","symbol":"BTCUSDT","interval":"15m",
            "open_time":pd.Timestamp(row["open_time"]).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "close_time":pd.Timestamp(row["close_time"]).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "open":str(row.get("open",0)),"high":str(row.get("high",0)),
            "low":str(row.get("low",0)),"close":str(row.get("close",0)),
            "volume":str(row.get("volume",0)),"quote_volume":str(row.get("quote_volume",0)),
            "trade_count":int(row["trade_count"]) if not pd.isna(row.get("trade_count")) else None,
            "source_row_count":int(row["n_trades"]) if not pd.isna(row.get("n_trades")) else None})
    
    payload = {"strategy":config,"rows_by_interval":{"15m":rows},
               "start":f"{start}T00:00:00+00:00","end":f"{end}T00:00:00+00:00","fee_rate":"0.0004"}
    r = subprocess.run([str(BIN)], input=json.dumps(payload), capture_output=True, text=True)
    if r.returncode != 0: continue
    rep = json.loads(r.stdout)
    s = rep["summary"]
    orders = rep.get("orders", [])
    
    # Pair orders into round trips
    opens = [o for o in orders if o.get("action") == "Open"]
    # Group by intent_id pattern or just pair sequentially
    wins = 0; losses = 0; gross_profit = 0.0; gross_loss = 0.0
    
    # Get PnL from fills
    fills = orders  # all orders are fills in backtest
    buy_fills = [f for f in fills if f.get("side") == "Long"]
    sell_fills = [f for f in fills if f.get("side") == "Short"]
    
    # Simpler: use position snapshots
    positions = rep.get("positions", [])
    for p in positions:
        pnl = float(p.get("pnl", 0))
        if pnl > 0:
            wins += 1
            gross_profit += pnl
        elif pnl < 0:
            losses += 1
            gross_loss += abs(pnl)
    
    total_trades = wins + losses
    win_rate = (wins/total_trades*100) if total_trades > 0 else 0
    pf = (gross_profit/gross_loss) if gross_loss > 0 else (999 if gross_profit > 0 else 0)
    pnl = float(s.get("total_pnl", 0))
    eq = float(s.get("final_equity", 0))
    
    print(f"{label:<10s} {total_trades:>7d} {wins:>5d} {losses:>5d} {win_rate:>6.1f}% {pf:>6.2f} {pnl:>+10.1f} {eq:>10.1f}")
    
    # Show position sequence for pattern analysis
    if positions:
        pnls = [float(p.get("pnl",0)) for p in positions]
        streaks = []
        current = 1
        for i in range(1, len(pnls)):
            if (pnls[i] > 0) == (pnls[i-1] > 0):
                current += 1
            else:
                streaks.append(current)
                current = 1
        streaks.append(current)
        max_loss_streak = max((s for s,p in zip(streaks, [pnls[0]]+pnls) if p < 0), default=0)
        print(f"  {'':10s} PnL seq: {[f'{x:+.0f}' for x in pnls[:12]]}{'...' if len(pnls)>12 else ''}  max L streak: {max_loss_streak}")
