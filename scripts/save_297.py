#!/usr/bin/env python3
"""Save 297 strategy to server DB — with visible output to file."""
import json, subprocess, sys
from pathlib import Path

OUT = Path.home() / "quant_backtest/data/save_result.txt"

config = json.loads((Path.home() / "quant_backtest/data/297_clean.json").read_text())
name = config["name"]
sym = config["basic"]["symbol"]
js = json.dumps(config, ensure_ascii=False)
safe_js = js.replace("'", "''")

# Method 1: SQL via docker exec
sql = f"DELETE FROM strategy_configs WHERE name = '{name}'; INSERT INTO strategy_configs (name, strategy_type, symbol, config) VALUES ('{name}', 'streaming', '{sym}', '{safe_js}'::jsonb);"

r1 = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "ubuntu@43.167.10.218",
     f"echo '{sql}' | sudo docker exec -i quant_postgres psql -U quant -d quant_app"],
    capture_output=True, text=True, timeout=30,
)

# Method 2: Verify
r2 = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "ubuntu@43.167.10.218",
     f"sudo docker exec quant_postgres psql -U quant -d quant_app -t -A -c \"SELECT id, name FROM strategy_configs WHERE name = '{name}'\""],
    capture_output=True, text=True, timeout=10,
)

result = f"""SQL EXEC:
stdout: {r1.stdout}
stderr: {r1.stderr}
exit: {r1.returncode}

VERIFY:
stdout: {r2.stdout}
stderr: {r2.stderr}
exit: {r2.returncode}
"""
OUT.write_text(result)
print(f"Result written to {OUT}")
print(result[:500])
