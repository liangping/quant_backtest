#!/usr/bin/env python3
"""Run 296@15m continuously for 6 months, detailed report."""
import json, subprocess
from pathlib import Path
import pandas as pd

WORK = Path.home() / "quant_backtest"
BIN = Path.home() / "Documents/New project/rust/target/release/backtest-direct-runner"
if not BIN.exists(): BIN = Path.home() / "Documents/New project/rust/target/debug/backtest-direct-runner"
CACHE = Path.home() / "Documents/New project/data/local-market-cache/binance_um_futures"

import sys
strat = sys.argv[1] if len(sys.argv) > 1 else "server_296_15m"
config = json.loads((WORK / "strategies" / f"{strat}.json").read_text())
# Auto-detect interval from strategy signals
IV = "15m"
for s in config.get("signals", []):
    if s.get("interval") and s["interval"] != IV:
        IV = s["interval"]
        break
start, end = "2025-12-01", "2026-06-01"
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
s = rep["summary"]
positions = rep.get("positions", [])

pnls = [float(p.get("pnl", 0)) for p in positions]
sides = [str(p.get("side", "?")) for p in positions]
wins = sum(1 for x in pnls if x > 0)
losses = sum(1 for x in pnls if x < 0)
gp = sum(x for x in pnls if x > 0)
gl = sum(abs(x) for x in pnls if x < 0)
total = wins + losses
wr = (wins / total * 100) if total > 0 else 0
pf = (gp / gl) if gl > 0 else (999 if gp > 0 else 0)

long_pnls = [x for i, x in enumerate(pnls) if sides[i] == "long"]
short_pnls = [x for i, x in enumerate(pnls) if sides[i] == "short"]

# Monthly breakdown by exit_time
monthly = {}
for p in positions:
    et = (p.get("exit_time") or "")[:7]
    if et:
        monthly[et] = monthly.get(et, 0.0) + float(p.get("pnl", 0))

init_cap = float(s.get("initial_capital", 2000))
final_eq = float(s.get("final_equity", 2000))
total_pnl = final_eq - init_cap

print("=" * 60)
print(f"  策略 296@15m — 连续 6 个月回测")
print("=" * 60)
print(f"  周期:     {start} → {end}")
print(f"  K线:      {s.get('processed_bars', 0)} 根 (15m)")
print(f"  本金:     ${init_cap:,.0f}")
print(f"  最终权益: ${final_eq:,.0f}")
print(f"  总盈亏:   ${total_pnl:+,.0f}  ({total_pnl/init_cap*100:+.1f}%)")
print(f"  最大回撤: {s.get('max_drawdown_pct', '?')}")
print()
print(f"  交易:     {total} 笔 (胜 {wins} / 负 {losses})")
print(f"  胜率:     {wr:.1f}%")
print(f"  盈亏比:   {pf:.2f}")
print(f"  最大单笔盈: ${max(pnls):+,.0f}")
print(f"  最大单笔亏: ${min(pnls):+,.0f}")
print(f"  均笔盈亏:  ${sum(pnls)/total:+,.1f}" if total > 0 else "")
print()
print(f"  Long:  {len(long_pnls)} 笔  PnL={sum(long_pnls):+,.0f}")
print(f"  Short: {len(short_pnls)} 笔  PnL={sum(short_pnls):+,.0f}")
print()
print(f"  月度分布 (按退出时间):")
for m, v in sorted(monthly.items()):
    print(f"    {m}: ${v:+,.0f}")
print("=" * 60)

# Worst trades
worst = sorted(zip(pnls, sides), key=lambda x: x[0])[:5]
print(f"\n  最差 5 笔:")
for pnl, side in worst:
    print(f"    {side:5s} {pnl:+.0f}")
best = sorted(zip(pnls, sides), key=lambda x: x[0])[-5:]
print(f"  最佳 5 笔:")
for pnl, side in best:
    print(f"    {side:5s} {pnl:+.0f}")