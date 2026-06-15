#!/usr/bin/env python3
"""Run all 3 active strategies on $1k/10x/100%/false and compare."""
import json, subprocess, sys
from pathlib import Path
import pandas as pd

PROJ = Path.home() / "quant_backtest"
RUST = Path.home() / "Documents/New project/rust/target/release/backtest-direct-runner"
if not RUST.exists():
    RUST = Path.home() / "Documents/New project/rust/target/debug/backtest-direct-runner"
CACHE = Path.home() / "Documents/New project/data/local-market-cache/binance_um_futures"

STRATEGIES = [
    ("bb_rsi_protected", "BB+RSI Protected (296)", "5m", {"position_mode": "switch", "name": "bb_rsi_protected"}),
    ("ema_trend_follow", "EMA Trend Follow", "15m", {"position_mode": "switch", "name": "ema_trend_follow"}),
    ("macd_atr_trend", "MACD+ATR Trend (294)", "15m", {"position_mode": "long_only", "name": "macd_atr_trend"}),
]

BASE_PARAMS = {
    "initial_capital": "1000",
    "leverage": "10",
    "compound_profit": False,
    "position_pct": "100",
}

MONTHS = [
    ("2025-12-01", "2026-01-01", "Dec"),
    ("2026-01-01", "2026-02-01", "Jan"),
    ("2026-02-01", "2026-03-01", "Feb"),
    ("2026-03-01", "2026-04-01", "Mar"),
    ("2026-04-01", "2026-05-01", "Apr"),
    ("2026-05-01", "2026-06-01", "May"),
]

for fname, label, default_iv, meta in STRATEGIES:
    sp = PROJ / "strategies" / f"{fname}.json"
    config = json.loads(sp.read_text())
    config["basic"]["initial_capital"] = BASE_PARAMS["initial_capital"]
    config["basic"]["leverage"] = BASE_PARAMS["leverage"]
    config["basic"]["compound_profit"] = BASE_PARAMS["compound_profit"]
    for block in ["long", "short"]:
        for rule in config.get(block, {}).get("entry_rules", []):
            rule["position_pct"] = BASE_PARAMS["position_pct"]
    sp.write_text(json.dumps(config, indent=2))
    
    # Detect intervals from signals
    intervals = set()
    for s in config.get("signals", []):
        if s.get("interval"):
            intervals.add(s["interval"])
    if not intervals:
        intervals = {default_iv}
    
    print(f"\n{'='*70}")
    print(f"  {label}  intervals={sorted(intervals)}  cap={BASE_PARAMS['initial_capital']}  lev={BASE_PARAMS['leverage']}x  pct={BASE_PARAMS['position_pct']}%")
    print(f"{'='*70}")
    
    grand_pnl = 0.0
    grand_fills = 0
    for start, end, mlabel in MONTHS:
        start_ts = pd.Timestamp(start, tz="UTC")
        end_ts = pd.Timestamp(end, tz="UTC")
        rows_by_iv = {}
        for iv in sorted(intervals):
            dfs = []
            for pq in sorted((CACHE / "BTCUSDT" / iv).glob("*.parquet")):
                df = pd.read_parquet(pq)
                if "open_time" not in df.columns:
                    continue
                df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
                df = df[(df["open_time"] >= start_ts) & (df["open_time"] < end_ts)]
                if not df.empty:
                    dfs.append(df)
            if dfs:
                all_data = pd.concat(dfs).sort_values("open_time")
                rows = []
                for _, row in all_data.iterrows():
                    rows.append({
                        "exchange": "binance_um_futures", "symbol": "BTCUSDT", "interval": iv,
                        "open_time": pd.Timestamp(row["open_time"]).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        "close_time": pd.Timestamp(row["close_time"]).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        "open": str(row.get("open", 0)), "high": str(row.get("high", 0)),
                        "low": str(row.get("low", 0)), "close": str(row.get("close", 0)),
                        "volume": str(row.get("volume", 0)), "quote_volume": str(row.get("quote_volume", 0)),
                        "trade_count": int(row["trade_count"]) if not pd.isna(row.get("trade_count")) else None,
                        "source_row_count": int(row["n_trades"]) if not pd.isna(row.get("n_trades")) else None,
                    })
                rows_by_iv[iv] = rows
        
        if not rows_by_iv:
            print(f"  {mlabel}: no data")
            continue
        
        payload = {
            "strategy": config,
            "rows_by_interval": rows_by_iv,
            "start": f"{start}T00:00:00+00:00",
            "end": f"{end}T00:00:00+00:00",
            "fee_rate": "0.0004",
        }
        
        r = subprocess.run([str(RUST)], input=json.dumps(payload), capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  {mlabel}: ERROR {r.stderr[:120]}")
            continue
        
        report = json.loads(r.stdout)
        s = report.get("summary", {})
        fills = s.get("fill_count", 0)
        pnl = float(s.get("total_pnl", 0))
        eq = float(s.get("final_equity", 0))
        ret = s.get("return_pct", "?")
        dd = s.get("max_drawdown_pct", "?")
        grand_pnl += pnl
        grand_fills += fills
        print(f"  {mlabel}: fills={fills:>4d}  PnL={pnl:>+8.1f}  equity={eq:>8.1f}  ret={ret:>8s}  dd={dd:>8s}")
    
    print(f"  {'TOTAL':>6s}: fills={grand_fills:>4d}  PnL={grand_pnl:>+8.1f}")
