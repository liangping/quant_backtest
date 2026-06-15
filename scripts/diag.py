#!/usr/bin/env python3
"""Diagnostic: run the validated streaming_functional_strategy_suite strategies
on the same monthly data to check if the runner has bugs."""
import json, subprocess, sys
from pathlib import Path
import pandas as pd

WORK = Path.home() / "quant_backtest"
RUST = Path.home() / "Documents/New project/rust/target/release/backtest-direct-runner"
if not RUST.exists():
    RUST = Path.home() / "Documents/New project/rust/target/debug/backtest-direct-runner"
CACHE = Path.home() / "Documents/New project/data/local-market-cache/binance_um_futures"

# Load the example suite
suite = json.loads((Path.home() / "Documents/New project/examples/streaming_functional_strategy_suite.json").read_text())
strategies = suite["strategies"]

# Pick the MACD cross strategy (first one) and extend its time range
strat = strategies[0].copy()  # ft_macd_cross_matrix_long
strat["basic"]["exchange"] = "binance_um_futures"
strat["basic"]["start_time"] = "2026-05-01T00:00:00Z"
strat["basic"]["end_time"] = "2026-06-01T00:00:00Z"
strat["basic"]["initial_capital"] = "1000"
strat["basic"]["leverage"] = "5"

# Ensure position_mode for new format
if "position_mode" not in strat:
    strat["position_mode"] = "long_only"
if "entry_rules" in strat and "long" not in strat:
    strat["long"] = {"entry_rules": strat.pop("entry_rules"), "exit_rules": strat.pop("exit_rules", [])}
for rule in strat["long"]["entry_rules"]:
    rule.pop("name", None); rule.pop("tags", None)
    if "weight" in rule: rule["position_pct"] = rule.pop("weight")
for rule in strat["long"]["exit_rules"]:
    rule.pop("name", None); rule.pop("lot_selection", None)
strat.pop("strategy_kind", None); strat.pop("universe", None); strat.pop("side", None)

# Also take the RSI strategy (second one)
strat2 = strategies[1].copy()  # ft_rsi_reversal_with_market_gate
strat2["basic"]["exchange"] = "binance_um_futures"
strat2["basic"]["start_time"] = "2026-05-01T00:00:00Z"
strat2["basic"]["end_time"] = "2026-06-01T00:00:00Z"
strat2["basic"]["initial_capital"] = "1000"
strat2["basic"]["leverage"] = "5"
if "position_mode" not in strat2:
    strat2["position_mode"] = "long_only"
if "entry_rules" in strat2 and "long" not in strat2:
    strat2["long"] = {"entry_rules": strat2.pop("entry_rules"), "exit_rules": strat2.pop("exit_rules", [])}
for rule in strat2["long"]["entry_rules"]:
    rule.pop("name", None); rule.pop("tags", None)
    if "weight" in rule: rule["position_pct"] = rule.pop("weight")
for rule in strat2["long"]["exit_rules"]:
    rule.pop("name", None); rule.pop("lot_selection", None)
strat2.pop("strategy_kind", None); strat2.pop("universe", None); strat2.pop("side", None)

# Load May 2026 data
INTERVAL = "5m"
SYMBOL = "BTCUSDT"
start_ts = pd.Timestamp("2026-05-01", tz="UTC")
end_ts = pd.Timestamp("2026-06-01", tz="UTC")
dfs = []
for pq in sorted((CACHE / SYMBOL / INTERVAL).glob("*.parquet")):
    df = pd.read_parquet(pq)
    if "open_time" not in df.columns: continue
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df = df[(df["open_time"] >= start_ts) & (df["open_time"] < end_ts)]
    if not df.empty: dfs.append(df)
all_data = pd.concat(dfs).sort_values("open_time")

rows = []
for _, row in all_data.iterrows():
    rows.append({
        "exchange": "binance_um_futures", "symbol": SYMBOL, "interval": INTERVAL,
        "open_time": pd.Timestamp(row["open_time"]).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "close_time": pd.Timestamp(row["close_time"]).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "open": str(row.get("open",0)), "high": str(row.get("high",0)),
        "low": str(row.get("low",0)), "close": str(row.get("close",0)),
        "volume": str(row.get("volume",0)), "quote_volume": str(row.get("quote_volume",0)),
        "trade_count": int(row["trade_count"]) if not pd.isna(row.get("trade_count")) else None,
        "source_row_count": int(row["n_trades"]) if not pd.isna(row.get("n_trades")) else None,
    })

print(f"Data: {len(rows)} bars ({SYMBOL} {INTERVAL})")
print()

for name, config in [("MACD matrix long", strat), ("RSI + market gate", strat2)]:
    payload = {"strategy": config, "rows_by_interval": {INTERVAL: rows},
               "start": "2026-05-01T00:00:00+00:00", "end": "2026-06-01T00:00:00+00:00",
               "fee_rate": "0.0004"}
    
    r = subprocess.run([str(RUST)], input=json.dumps(payload), capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  {name}: ERROR {r.stderr[:200]}")
        continue
    
    report = json.loads(r.stdout)
    s = report.get("summary", {})
    fills = s.get("fill_count", 0)
    pnl = float(s.get("total_pnl", 0))
    eq = float(s.get("final_equity", 0))
    pos = s.get("position_count", 0)
    
    print(f"  {name}: fills={fills} pos={pos} PnL={pnl:+.1f} equity={eq:.1f} ret={s.get('return_pct','?')} dd={s.get('max_drawdown_pct','?')}")
    
    # Show first few orders
    orders = report.get("orders", [])
    if orders:
        print(f"    First 3 orders:")
        for o in orders[:3]:
            print(f"      {o.get('side','?')} {o.get('rule_label','?')}: qty={o.get('quantity','?')[:12]} @ {o.get('price','?')}")
        print(f"    Last 3 orders:")
        for o in orders[-3:]:
            print(f"      {o.get('side','?')} {o.get('rule_label','?')}: qty={o.get('quantity','?')[:12]} @ {o.get('price','?')}")
        # PnL from orders
        buy_orders = [o for o in orders if o.get('side') == 'buy']
        sell_orders = [o for o in orders if o.get('side') == 'sell']
        total_buy = sum(float(o.get('quote_qty', 0) or 0) for o in buy_orders)
        total_sell = sum(float(o.get('quote_qty', 0) or 0) for o in sell_orders)
        print(f"    Total buy quote: {total_buy:.2f}, sell quote: {total_sell:.2f}, diff: {total_sell-total_buy:.2f}")
