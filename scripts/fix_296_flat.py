#!/usr/bin/env python3
"""Check & fix strategy 296 flat rules."""
import json, subprocess
from pathlib import Path

OUT = Path.home() / "quant_backtest/data/296_status.txt"

r = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "ubuntu@43.167.10.218",
     'sudo docker exec quant_postgres psql -U quant -d quant_app -t -A -c "SELECT config FROM strategy_configs WHERE id = 296"'],
    capture_output=True, text=True, timeout=15,
)

config = json.loads(r.stdout.strip())
switch_rules = config.get("switch_rules", [])
has_flat = any(sr.get("from_side") == "flat" for sr in switch_rules)

lines = []
lines.append(f"Switch rules: {len(switch_rules)}")
for sr in switch_rules:
    lines.append(f"  {sr.get('from_side','?')} -> {sr.get('to_side','?')}")
lines.append(f"Has flat rules: {has_flat}")

if not has_flat:
    flat_rules = [
        {"switch_rule_id": "switch_flat_to_long", "enabled": True, "from_side": "flat", "to_side": "long", "trigger_signal": "long_entry_signal", "close_quantity": "full_position", "next_entry_sequence": 1, "open_policy": "wait_entry_signal", "priority": 100},
        {"switch_rule_id": "switch_flat_to_short", "enabled": True, "from_side": "flat", "to_side": "short", "trigger_signal": "short_entry_signal", "close_quantity": "full_position", "next_entry_sequence": 1, "open_policy": "wait_entry_signal", "priority": 100},
    ]
    config["switch_rules"] = flat_rules + switch_rules
    js = json.dumps(config, ensure_ascii=False).replace("'", "''")
    sql = f"UPDATE strategy_configs SET config = '{js}'::jsonb WHERE id = 296"
    
    r2 = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "ubuntu@43.167.10.218",
         f"sudo docker exec quant_postgres psql -U quant -d quant_app -c \"{sql}\""],
        capture_output=True, text=True, timeout=15,
    )
    lines.append(f"\nUPDATE result: {r2.stdout.strip()} {r2.stderr.strip()}")
    
    # Verify
    r3 = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "ubuntu@43.167.10.218",
         'sudo docker exec quant_postgres psql -U quant -d quant_app -t -A -c "SELECT config->\'switch_rules\' FROM strategy_configs WHERE id = 296"'],
        capture_output=True, text=True, timeout=15,
    )
    sr_after = json.loads(r3.stdout.strip()) if r3.stdout.strip() else []
    lines.append(f"Switch rules after: {len(sr_after)}")
    for sr in sr_after:
        lines.append(f"  {sr.get('from_side','?')} -> {sr.get('to_side','?')}")

OUT.write_text("\n".join(lines))
print("\n".join(lines))
