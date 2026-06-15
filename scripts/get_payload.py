#!/usr/bin/env python3
"""Get full signal pipeline event payload."""
import subprocess, json
from pathlib import Path

OUT = Path.home() / "quant_backtest/data/signal_event.json"

r = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "ubuntu@43.167.10.218",
     "sudo docker exec quant_postgres psql -U quant -d quant_app -t -A -c \"SELECT payload FROM live_robot_events WHERE event_type = 'live_signal_pipeline_snapshot' ORDER BY received_at DESC LIMIT 1\""],
    capture_output=True, text=True, timeout=15,
)

payload_str = r.stdout.strip()
if not payload_str:
    print(f"No signal pipeline events found")
    print(f"stderr: {r.stderr}")
    exit(1)

data = json.loads(payload_str)
indicator_count = data.get("indicator_count", "MISSING")
indicators = data.get("indicators", [])
rules = data.get("rules", [])
status = data.get("status", "?")

print(f"Status: {status}")
print(f"Robot: {data.get('robot_id', '?')}")
print(f"Symbol: {data.get('symbol', '?')}")
print(f"Interval: {data.get('interval', '?')}")
print(f"indicator_count: {indicator_count}")
print(f"indicators array length: {len(indicators)}")
print(f"rules array length: {len(rules)}")
print(f"action_generated: {data.get('action_generated', '?')}")

if indicators:
    print("\nFirst 3 indicators:")
    for i in indicators[:3]:
        sid = i.get("signal_id", "?")
        ready = i.get("ready", "?")
        matched = i.get("matched", "?")
        values = i.get("values", {})
        signal = i.get("signal", "")
        conditions = i.get("conditions", [])
        reason = i.get("reason", "")
        print(f"  {sid}: ready={ready} matched={matched} signal={signal} values={json.dumps(values)[:80]} reason={reason}")

OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
print(f"\nFull payload saved to {OUT}")
