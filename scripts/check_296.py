#!/usr/bin/env python3
import json, subprocess
from pathlib import Path

OUT = Path.home() / "quant_backtest/data/296_switch_rules.txt"

r = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "ubuntu@43.167.10.218",
     "sudo docker exec quant_postgres psql -U quant -d quant_app -t -A -c \"SELECT config FROM strategy_configs WHERE id = 296\""],
    capture_output=True, text=True, timeout=15,
)

config = json.loads(r.stdout.strip())

lines = []
lines.append(f"position_mode: {config.get('position_mode')}")
lines.append(f"switch_rules: {len(config.get('switch_rules', []))}")
for sr in config.get("switch_rules", []):
    lines.append(f"  {sr.get('from_side','?')} -> {sr.get('to_side','?')}: {sr.get('switch_rule_id','?')}")
lines.append(f"long entries: {len(config.get('long',{}).get('entry_rules',[]))}")
lines.append(f"short entries: {len(config.get('short',{}).get('entry_rules',[]))}")

OUT.write_text("\n".join(lines))
print("\n".join(lines))
