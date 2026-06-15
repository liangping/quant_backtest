#!/usr/bin/env python3
"""Get rules from latest signal pipeline event."""
import json, subprocess
from pathlib import Path

OUT = Path.home() / "quant_backtest/data/rules_detail.txt"

r = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "ubuntu@43.167.10.218",
     'sudo docker exec quant_postgres psql -U quant -d quant_app -t -A -c "SELECT payload FROM live_robot_events WHERE event_type = \'live_signal_pipeline_snapshot\' ORDER BY received_at DESC LIMIT 1"'],
    capture_output=True, text=True, timeout=15,
)

data = json.loads(r.stdout.strip())
rules = data.get("rules", [])
indicators = data.get("indicators", [])

lines = []
lines.append(f"Robot: {data.get('robot_id')}  Symbol: {data.get('symbol')}")
lines.append(f"Status: {data.get('status')}  Skip: {data.get('skip_reason')}")
lines.append(f"")
lines.append(f"=== Rules ({len(rules)}) ===")
for rule in rules:
    lines.append(f"  {rule.get('entry_rule_id','?')}: matched={rule.get('matched')} trigger={rule.get('trigger_signal','?')} reason={rule.get('reason','?')}")
lines.append(f"")
lines.append(f"=== Indicators ({len(indicators)}) ===")
for ind in indicators[:3]:
    lines.append(f"  {ind.get('signal_id','?')}: ready={ind.get('ready')} matched={ind.get('matched')} signal={ind.get('signal','?')} reason={ind.get('reason','?')}")

OUT.write_text("\n".join(lines))
print("\n".join(lines))
