#!/usr/bin/env python3
"""Clean strategy 296, run monthly stats."""
import json, subprocess
from pathlib import Path
import pandas as pd

WORK = Path.home() / "quant_backtest"
BIN = Path.home() / "Documents/New project/rust/target/release/backtest-direct-runner"
if not BIN.exists(): BIN = Path.home() / "Documents/New project/rust/target/debug/backtest-direct-runner"
CACHE = Path.home() / "Documents/New project/data/local-market-cache/binance_um_futures"

# Load and clean
raw = (Path.home() / "quant_backtest/data/server_296.txt").read_text().strip()
parts = raw.split("|", 3)
config = json.loads(parts[3].strip()) if len(parts) >= 4 else json.loads(raw)

config.pop("strategy_kind", None)
config.pop("universe", None)
config.pop("side", None)

for block in ["long", "short"]:
    for rule in config.get(block, {}).get("entry_rules", []):
        rule.pop("name", None); rule.pop("tags", None)
    for rule in config.get(block, {}).get("exit_rules", []):
        rule.pop("name", None); rule.pop("lot_selection", None)

for s in config.get("signals", []):
    to_del = [k for k, v in s.items() if v is None or (isinstance(v, list) and len(v) == 0)]
    for k in to_del: del s[k]

config["basic"]["exchange"] = "binance_um_futures"
config["basic"]["initial_capital"] = "2000"
config["basic"]["leverage"] = "5"

for block in ["long", "short"]:
    for rule in config.get(block, {}).get("entry_rules", []):
        rule["position_pct"] = "50"

# Flat switch rules
flat_rules = [
    {"switch_rule_id":"sw_flat_long","enabled":True,"from_side":"flat","to_side":"long",
     "trigger_signal":"long_entry_signal","close_quantity":"full_position","next_entry_sequence":1,
     "open_policy":"wait_entry_signal","priority":100},
    {"switch_rule_id":"sw_flat_short","enabled":True,"from_side":"flat","to_side":"short",
     "trigger_signal":"short_entry_signal","close_quantity":"full_position","next_entry_sequence":1,
     "open_policy":"wait_entry_signal","priority":100},
]
config["switch_rules"] = flat_rules + config.get("switch_rules", [])

for r in config.get("strategy_risk_rules", []):
    if r.get("rule_type") == "cooldown_bars":
        r["value"] = 6

config["name"] = "server_296_protected"
out = WORK / "strategies/server_296_protected.json"
out.write_text(json.dumps(config, indent=2))
print(f"Saved: {out.name}")

# Run
INTERVAL = "5m"
months = [("2025-12-01","2026-01-01"),("2026-01-01","2026-02-01"),("2026-02-01","2026-03-01"),
          ("2026-03-01","2026-04-01"),("2026-04-01","2026-05-01"),("2026-05-01","2026-06-01")]

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
