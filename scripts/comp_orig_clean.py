#!/usr/bin/env python3
"""Compare original vs cleaned 296."""
import json
from pathlib import Path

raw = (Path.home() / "quant_backtest/data/server_296.txt").read_text().strip()
parts = raw.split("|", 3)
if len(parts) >= 4:
    orig = json.loads(parts[3].strip())
else:
    orig = json.loads(raw)

cleaned = json.loads((Path.home() / "quant_backtest/strategies/server_296_15m.json").read_text())

print("=== ORIGINAL (from DB) ===")
print(f"  mode={orig.get('position_mode','?')} lev={orig.get('basic',{}).get('leverage','?')}x cap={orig.get('basic',{}).get('initial_capital','?')}")
print(f"  Signals: {len(orig.get('signals',[]))}")
for s in orig.get("signals", []):
    sid = s.get("signal_id", "?")
    interval = s.get("interval", "")
    trig = s.get("trigger", "")
    is_pos = s.get("signal_type") in ("position_indicator", "position_atr")
    if is_pos:
        detail = f"ref={s.get('atr_reference','')} op={s.get('atr_operator','')} mult={s.get('atr_multiplier','')}"
    else:
        detail = f"{interval} {trig}"
    print(f"    {sid}: {s.get('signal_type','?')} -> {detail}")

print(f"  Long exits ({len(orig.get('long',{}).get('exit_rules',[]))}):")
for r in orig.get("long", {}).get("exit_rules", []):
    print(f"    p{r.get('priority','?')} {r.get('exit_rule_id','?')} action={r.get('exit_action','?')} sig={r.get('trigger_signal','?')}")

print(f"  Short exits ({len(orig.get('short',{}).get('exit_rules',[]))}):")
for r in orig.get("short", {}).get("exit_rules", []):
    print(f"    p{r.get('priority','?')} {r.get('exit_rule_id','?')} action={r.get('exit_action','?')} sig={r.get('trigger_signal','?')}")

print(f"  Switch rules: {len(orig.get('switch_rules',[]))}")
for r in orig.get("switch_rules", []):
    print(f"    {r.get('from_side','?')} -> {r.get('to_side','?')}")

print()
print("=== CLEANED (server_296_15m) ===")
print(f"  mode={cleaned.get('position_mode','?')} lev={cleaned.get('basic',{}).get('leverage','?')}x cap={cleaned.get('basic',{}).get('initial_capital','?')}")
for side in ["long", "short"]:
    print(f"  {side} exits ({len(cleaned.get(side,{}).get('exit_rules',[]))}):")
    for r in cleaned.get(side, {}).get("exit_rules", []):
        print(f"    p{r.get('priority','?')} {r.get('exit_rule_id','?')} action={r.get('exit_action','?')} sig={r.get('trigger_signal','?')}")
print(f"  Switch rules: {len(cleaned.get('switch_rules',[]))}")
for r in cleaned.get("switch_rules", []):
    print(f"    {r.get('from_side','?')} -> {r.get('to_side','?')}")
