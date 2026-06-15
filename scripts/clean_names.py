#!/usr/bin/env python3
"""Clean up strategy names — rename key strategies, archive the rest."""
import json, shutil
from pathlib import Path

S = Path.home() / "quant_backtest/strategies"
ARCHIVE = S / "_archive"
ARCHIVE.mkdir(exist_ok=True)

# === KEY STRATEGIES (keep, rename clearly) ===
RENAMES = {
    "server_296_protected.json": "bb_rsi_protected.json",     # OpenAI 296
    "server_294_macd_atr.json": "macd_atr_trend.json",        # 294 MACD+ATR
    "ema_trend_simple.json": "ema_trend_follow.json",         # EMA cross
    "bb_rsi_15m_switch.json": "bb_rsi_switch.json",           # BB+RSI mean-rev
    "selected.json": None,  # delete — it's a duplicate
}

# === ARCHIVE (move to _archive) ===
ARCHIVE_LIST = [
    "adx_bb_zscore_mean_reversion.json",
    "bb_breakout.json",
    "bb_cross_simple.json",
    "bb_rsi_2k_50pct.json",
    "bb_rsi_atr_cooldown.json",
    "bb_rsi_cooldown_only.json",
    "bb_rsi_ema_atr.json",
    "bb_rsi_mean_reversion.json",
    "bb_zscore_switch.json",
    "ema_adx_switch.json",
    "ema_trend.json",
    "ema_trend_switch.json",
    "hybrid.json",
    "macd_atr_short.json",
    "macd_bidir.json",
    "server_246.json",
    "server_246_cd3.json",
    "server_246_long.json",
    "server_246_nocd.json",
    "server_246_pct25.json",
    "server_246_pct50.json",
    "server_294_macd_gc.json",
    "server_296_15m.json",
    "server_296_dynamic_sizing.json",
    "server_296_fast_trend.json",
    "server_296_trend.json",
    "state_trend.json",
]

for src, dst in RENAMES.items():
    sp = S / src
    if dst is None:
        if sp.exists():
            sp.unlink()
            print(f"Deleted: {src}")
        continue
    dp = S / dst
    if sp.exists():
        sp.rename(dp)
        print(f"Renamed: {src} → {dst}")

for fname in ARCHIVE_LIST:
    sp = S / fname
    if sp.exists():
        shutil.move(str(sp), str(ARCHIVE / fname))
        print(f"Archived: {fname}")

# Show remaining
print("\n=== Active strategies ===")
for f in sorted(S.glob("*.json")):
    c = json.loads(f.read_text())
    name = c.get("name", "?")
    mode = c.get("position_mode", "?")
    cap = c.get("basic", {}).get("initial_capital", "?")
    lev = c.get("basic", {}).get("leverage", "?")
    print(f"  {f.name}: {name} ({mode} cap={cap} lev={lev}x)")
