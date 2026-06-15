#!/usr/bin/env python3
"""Insert strategy 297 (296@15m) into server database via piped SQL."""
import json, subprocess, sys
from pathlib import Path

config = json.loads((Path.home() / "quant_backtest/strategies/bb_rsi_protected.json").read_text())

for s in config["signals"]:
    if s.get("interval"):
        s["interval"] = "15m"

config["basic"]["initial_capital"] = "2000"
config["basic"]["leverage"] = "20"
for blk in ["long", "short"]:
    for r in config.get(blk, {}).get("entry_rules", []):
        r["position_pct"] = "100"

config.pop("strategy_kind", None)
config.pop("universe", None)
config.pop("side", None)
for s in config["signals"]:
    for k in list(s.keys()):
        if s[k] is None or (isinstance(s[k], list) and len(s[k]) == 0):
            del s[k]

config["name"] = "297_bb_rsi_protected_15m"
config["position_mode"] = config.get("position_mode", "switch")

strategy_json = json.dumps(config, ensure_ascii=False)
safe_json = strategy_json.replace("'", "''")
name = config["name"]
symbol = config["basic"]["symbol"]

sql = f"INSERT INTO strategy_configs (name, strategy_type, symbol, config) VALUES ('{name}', 'streaming', '{symbol}', '{safe_json}'::jsonb) ON CONFLICT (name, strategy_type) DO UPDATE SET config = EXCLUDED.config, symbol = EXCLUDED.symbol RETURNING id;\n"

print(f"Inserting {name} ({len(strategy_json)} bytes)...")

result = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "ubuntu@43.167.10.218",
     "sudo docker exec -i quant_postgres psql -U quant -d quant_app"],
    input=sql,
    capture_output=True, text=True,
)

if result.returncode != 0:
    print(f"ERROR: {result.stderr}")
    sys.exit(1)

print(f"OK: {result.stdout.strip()}")
