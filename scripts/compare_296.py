#!/usr/bin/env python3
"""Compare strategy 296 variants."""
import json
from pathlib import Path

HOME = Path.home() / "quant_backtest" / "strategies"

for label, fname in [("296_15m (selected)", "server_296_15m.json"), ("296_protected", "server_296_protected.json")]:
    c = json.loads((HOME / fname).read_text())
    print(f"=== {label} ===")
    print(f"  Signals:")
    for s in c.get("signals", []):
        sid = s.get("signal_id", "?")
        st = s.get("signal_type", "?")
        trig = s.get("trigger", "")
        expr = s.get("expression", "")
        indicator = s.get("indicator_id", "")
        interval = s.get("interval", "")
        w = s.get("window", "")
        cnd = s.get("conditions", "")
        if st == "composite":
            detail = f"op={s.get('operator','?')} conds={len(cnd)} w={w}"
        elif st == "position_atr" or st == "position_indicator":
            detail = f"ref={s.get('atr_reference','')} op={s.get('atr_operator','')} mult={s.get('atr_multiplier','')}"
        elif st == "expression":
            detail = f"{expr} {s.get('expression_operator','')} {s.get('expression_value','')}"
        else:
            detail = f"{indicator}/{interval} {trig}"
        print(f"    {sid}: {st} -> {detail}")
    
    print(f"  Long exits:")
    for r in c.get("long", {}).get("exit_rules", []):
        print(f"    p={r.get('priority','?')}  {r.get('exit_rule_id','?')}  action={r.get('exit_action','?')}  sig={r.get('trigger_signal','?')}")
    
    print(f"  Short exits:")
    for r in c.get("short", {}).get("exit_rules", []):
        print(f"    p={r.get('priority','?')}  {r.get('exit_rule_id','?')}  action={r.get('exit_action','?')}  sig={r.get('trigger_signal','?')}")
    
    print(f"  Risk rules:")
    for r in c.get("strategy_risk_rules", []):
        print(f"    {r.get('risk_rule_id','?')}: type={r.get('rule_type','?')}  val={r.get('value','?')}")
    print()
