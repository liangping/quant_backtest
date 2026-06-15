#!/usr/bin/env python3
"""Run 296 and 294 side by side: $1k/10x/100%/false, monthly breakdown."""
import json, subprocess
from pathlib import Path
import pandas as pd

BIN = Path.home() / "Documents/New project/rust/target/release/backtest-direct-runner"
if not BIN.exists():
    BIN = Path.home() / "Documents/New project/rust/target/debug/backtest-direct-runner"
CACHE = Path.home() / "Documents/New project/data/local-market-cache/binance_um_futures"
STRATS = Path.home() / "quant_backtest/strategies"

MN = [("2025-12","2026-01"),("2026-01","2026-02"),("2026-02","2026-03"),
      ("2026-03","2026-04"),("2026-04","2026-05"),("2026-05","2026-06")]

for fname, label in [("bb_rsi_protected","296:BB+RSI Protected"),("macd_atr_trend","294:MACD+ATR")]:
    c = json.loads((STRATS / f"{fname}.json").read_text())
    c["basic"]["initial_capital"] = "1000"
    c["basic"]["leverage"] = "10"
    c["basic"]["compound_profit"] = False
    for blk in ["long","short"]:
        for r in c.get(blk,{}).get("entry_rules",[]): r["position_pct"] = "100"
    
    ivs = set()
    for s in c.get("signals",[]):
        if s.get("interval"): ivs.add(s["interval"])
    if not ivs: ivs = {"15m"}
    
    print(f"\n{'='*60}")
    print(f"  {label}  {sorted(ivs)}")
    print(f"{'='*60}")
    print(f"  {'Month':<8s} {'Fills':>5s} {'PnL':>10s} {'Equity':>10s} {'Return':>8s} {'MaxDD':>8s}")
    print(f"  {'-'*52}")
    
    gpnl = gfills = 0.0
    for ms, me in MN:
        st = pd.Timestamp(f"{ms}-01", tz="UTC")
        et = pd.Timestamp(f"{me}-01", tz="UTC")
        rows_iv = {}
        for iv in sorted(ivs):
            dfs = []
            for pq in sorted((CACHE / "BTCUSDT" / iv).glob("*.parquet")):
                df = pd.read_parquet(pq)
                if "open_time" not in df.columns: continue
                df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
                df = df[(df["open_time"] >= st) & (df["open_time"] < et)]
                if not df.empty: dfs.append(df)
            if dfs:
                ad = pd.concat(dfs).sort_values("open_time")
                rows = []
                for _, rw in ad.iterrows():
                    rows.append(dict(exchange="binance_um_futures",symbol="BTCUSDT",interval=iv,
                        open_time=pd.Timestamp(rw["open_time"]).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        close_time=pd.Timestamp(rw["close_time"]).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        open=str(rw.get("open",0)),high=str(rw.get("high",0)),
                        low=str(rw.get("low",0)),close=str(rw.get("close",0)),
                        volume=str(rw.get("volume",0)),quote_volume=str(rw.get("quote_volume",0)),
                        trade_count=int(rw["trade_count"]) if not pd.isna(rw.get("trade_count")) else None,
                        source_row_count=int(rw["n_trades"]) if not pd.isna(rw.get("n_trades")) else None))
                rows_iv[iv] = rows
        if not rows_iv:
            print(f"  {ms:<8s} no data")
            continue
        pl = dict(strategy=c,rows_by_interval=rows_iv,
                  start=f"{ms}-01T00:00:00+00:00",end=f"{me}-01T00:00:00+00:00",fee_rate="0.0004")
        r = subprocess.run([str(BIN)],input=json.dumps(pl),capture_output=True,text=True)
        if r.returncode != 0:
            print(f"  {ms:<8s} ERROR {r.stderr[:80]}")
            continue
        rep = json.loads(r.stdout)
        s = rep.get("summary",{})
        f = s.get("fill_count",0)
        p = float(s.get("total_pnl",0))
        e = float(s.get("final_equity",0))
        rt = s.get("return_pct","?")
        dd = s.get("max_drawdown_pct","?")
        gpnl += p; gfills += f
        print(f"  {ms:<8s} {f:>5d} {p:>+10.1f} {e:>10.1f} {rt:>8s} {dd:>8s}")
    print(f"  {'-'*52}")
    print(f"  {'TOTAL':<8s} {gfills:>5d} {gpnl:>+10.1f}")
