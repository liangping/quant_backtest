#!/usr/bin/env python3
"""Get latest signal pipeline event."""
import json, subprocess
from pathlib import Path

OUT = Path.home() / "quant_backtest/data/latest_signal.txt"

r = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "ubuntu@43.167.10.218",
     'sudo docker exec quant_postgres psql -U quant -d quant_app -t -A -c "SELECT payload FROM live_robot_events WHERE event_type = \'live_signal_pipeline_snapshot\' ORDER BY received_at DESC LIMIT 1"'],
    capture_output=True, text=True, timeout=15,
)

payload_str = r.stdout.strip()
OUT.write_text(f"stdout: {repr(payload_str[:300])}\nstderr: {repr(r.stderr[:300])}\n")

if payload_str:
    try:
        data = json.loads(payload_str)
        info = {
            "robot_id": data.get("robot_id"),
            "status": data.get("status"),
            "skip_reason": data.get("skip_reason"),
            "indicator_count": data.get("indicator_count"),
            "indicators_len": len(data.get("indicators", [])),
            "rules_len": len(data.get("rules", [])),
            "config_version": data.get("config_version"),
        }
        OUT.write_text(json.dumps(info, indent=2, ensure_ascii=False))
        print(json.dumps(info, indent=2))
    except Exception as e:
        OUT.write_text(f"parse error: {e}\npayload: {payload_str[:200]}")
        print(f"parse error: {e}")
