#!/usr/bin/env python3
"""Export server strategy 294 to ~/quant_backtest/strategies/"""
import json, sys
from pathlib import Path

STRATEGIES = Path.home() / "quant_backtest" / "strategies"

raw = (Path.home() / "quant_backtest" / "data" / "server_294.txt").read_text().strip()
parts = raw.split("|", 3)
config = json.loads(parts[3].strip())

# Cleanup
config.pop("strategy_kind", None)
config.pop("universe", None)
config.pop("side", None)
config["basic"]["symbol"] = "BTCUSDT"

for block in ["long", "short"]:
    for rule in config.get(block, {}).get("entry_rules", []):
        rule.pop("name", None)
        rule.pop("tags", None)
        if "weight" in rule:
            rule["position_pct"] = rule.pop("weight")
    for rule in config.get(block, {}).get("exit_rules", []):
        rule.pop("name", None)
        rule.pop("lot_selection", None)

for s in config.get("signals", []):
    to_del = [k for k, v in s.items() if v is None or (isinstance(v, list) and len(v) == 0)]
    for k in to_del:
        del s[k]

config["name"] = "server_294_macd_gc"

out = STRATEGIES / "server_294_macd_gc.json"
out.write_text(json.dumps(config, indent=2))
print(f"Saved: {out}")
