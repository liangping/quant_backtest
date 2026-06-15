#!/usr/bin/env python3
"""Check event counts and sample a signal pipeline event."""
import subprocess
from pathlib import Path

OUT = Path.home() / "quant_backtest/data/event_check.txt"

def ssh(sql):
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "ubuntu@43.167.10.218",
         f"sudo docker exec quant_postgres psql -U quant -d quant_app -c \"{sql}\""],
        capture_output=True, text=True, timeout=15,
    )
    return r.stdout + "\n" + r.stderr

result = "=== Event counts (last 2h) ===\n"
result += ssh("SELECT event_type, count(*) FROM live_robot_events WHERE received_at > now() - interval '2 hours' GROUP BY event_type ORDER BY count(*) DESC")

result += "\n=== Latest signal_pipeline events ===\n"
result += ssh("SELECT event_id, left(payload::text, 300) FROM live_robot_events WHERE event_type = 'live_signal_pipeline_snapshot' ORDER BY received_at DESC LIMIT 3")

result += "\n=== Latest events of any type ===\n"
result += ssh("SELECT event_id, event_type, robot_id FROM live_robot_events ORDER BY received_at DESC LIMIT 10")

result += "\n=== signal_debug_events setting check ===\n"
result += "From logs: signal_debug_events=Important (only publishes when signal signature changes or action generated)"

OUT.write_text(result)
print(f"Written to {OUT}")
print(result[:1500])
