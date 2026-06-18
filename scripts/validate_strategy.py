#!/usr/bin/env python3
"""Validate a strategy JSON against capabilities exported by the runner."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation
import subprocess
import sys
from pathlib import Path

from run import RUNNER

WORK = Path(__file__).resolve().parent.parent


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001 - command-line diagnostic
        raise SystemExit(f"invalid JSON {path}: {exc}") from exc


def load_catalog(runner: Path) -> dict:
    proc = subprocess.run(
        [str(runner), "catalog", "--format", "json"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise SystemExit(
            f"runner catalog failed: {runner}\n{detail}\n"
            "Update bin/backtest-live-runner to a version that supports `catalog`."
        )
    try:
        catalog = json.loads(proc.stdout)
    except Exception as exc:  # noqa: BLE001 - command-line diagnostic
        raise SystemExit(f"runner catalog did not return JSON: {exc}") from exc
    if "strategy_capabilities" not in catalog or "indicator_catalog" not in catalog:
        raise SystemExit("runner catalog missing strategy_capabilities or indicator_catalog")
    return catalog


def as_set(catalog: dict, key: str) -> set[str]:
    return set(catalog["strategy_capabilities"].get(key, []))


def validate(path: Path, catalog: dict) -> list[str]:
    strategy = load_json(path)
    if not isinstance(strategy, dict):
        return ["strategy root must be a JSON object"]

    errors: list[str] = []
    indicators = {
        item["indicator_id"]: item
        for item in catalog.get("indicator_catalog", {}).get("entries", [])
        if isinstance(item, dict) and item.get("indicator_id")
    }
    schema = catalog["strategy_capabilities"]

    signal_types = as_set(catalog, "signal_types")
    condition_operators = as_set(catalog, "condition_operators")
    composite_operators = as_set(catalog, "signal_operators")
    ref_types = as_set(catalog, "condition_ref_types")
    exit_actions = as_set(catalog, "exit_actions")
    exit_quantities = as_set(catalog, "exit_quantities")
    risk_rule_types = as_set(catalog, "risk_rule_types")
    atr_references = as_set(catalog, "atr_references")
    atr_operators = as_set(catalog, "atr_operators")
    position_metrics = as_set(catalog, "position_metrics")
    position_references = as_set(catalog, "position_references")

    position_mode = strategy.get("position_mode", "long_only")
    if position_mode not in set(schema["position_modes"]):
        errors.append(f"unknown position_mode: {position_mode}")

    signals = strategy.get("signals", [])
    if not isinstance(signals, list):
        return ["signals must be a list"]

    signal_ids: set[str] = set()
    for index, signal in enumerate(signals):
        label = f"signals[{index}]"
        if not isinstance(signal, dict):
            errors.append(f"{label} must be an object")
            continue

        signal_id = signal.get("signal_id")
        if not signal_id:
            errors.append(f"{label} missing signal_id")
        elif signal_id in signal_ids:
            errors.append(f"duplicate signal_id: {signal_id}")
        else:
            signal_ids.add(signal_id)

        signal_type = signal.get("signal_type", "single")
        if signal_type not in signal_types:
            errors.append(f"{label} unknown signal_type: {signal_type}")
            continue

        operator = signal.get("condition_operator")
        if operator is not None and operator not in condition_operators:
            errors.append(f"{label} unknown condition_operator: {operator}")

        if signal_type == "single":
            indicator_id = signal.get("indicator_id")
            if indicator_id not in indicators:
                errors.append(f"{label} unknown indicator_id: {indicator_id}")
                continue
            trigger = signal.get("trigger")
            triggers = {
                item.get("trigger_id")
                for item in indicators[indicator_id].get("triggers", [])
                if isinstance(item, dict)
            }
            if trigger and trigger not in triggers:
                errors.append(f"{label} invalid trigger for {indicator_id}: {trigger}")
        elif signal_type == "composite":
            op = signal.get("operator", "all")
            if op not in composite_operators:
                errors.append(f"{label} unknown composite operator: {op}")
            for condition in signal.get("conditions", []):
                ref = condition.get("ref")
                ref_type = condition.get("ref_type")
                if ref_type not in ref_types:
                    errors.append(f"{label} unknown condition ref_type: {ref_type}")
                if ref_type == "user_signal" and ref not in signal_ids:
                    errors.append(f"{label} references unknown prior signal: {ref}")
        elif signal_type in {"position_atr", "position_indicator"}:
            metric = signal.get("position_metric", "atr" if signal_type == "position_atr" else None)
            if signal_type == "position_indicator" and metric not in position_metrics:
                errors.append(f"{label} unknown position_metric: {metric}")
            if metric == "atr" or signal_type == "position_atr":
                atr_signal = signal.get("atr_signal")
                if atr_signal not in signal_ids:
                    errors.append(f"{label} references unknown atr_signal: {atr_signal}")
                if signal.get("atr_reference") not in atr_references:
                    errors.append(f"{label} invalid atr_reference: {signal.get('atr_reference')}")
                if signal.get("atr_operator") not in atr_operators:
                    errors.append(f"{label} invalid atr_operator: {signal.get('atr_operator')}")
                if signal.get("atr_multiplier") is None:
                    errors.append(f"{label} missing atr_multiplier")
            if metric == "percent":
                if signal.get("position_reference") not in position_references:
                    errors.append(f"{label} invalid position_reference: {signal.get('position_reference')}")
                if signal.get("position_operator") not in atr_operators:
                    errors.append(f"{label} invalid position_operator: {signal.get('position_operator')}")
                if signal.get("position_percent") is None:
                    errors.append(f"{label} missing position_percent")
        elif signal_type == "expression":
            if not signal.get("expression"):
                errors.append(f"{label} missing expression")
            op = signal.get("expression_operator")
            if op not in condition_operators:
                errors.append(f"{label} unknown expression_operator: {op}")

    for side in ("long", "short"):
        block = strategy.get(side, {})
        total_position_pct = Decimal("0")
        for rule in block.get("entry_rules", []):
            ref = rule.get("trigger_signal")
            if ref not in signal_ids:
                errors.append(f"{side}.entry_rules references unknown trigger_signal: {ref}")
            try:
                position_pct = Decimal(str(rule.get("position_pct", "0")))
            except (InvalidOperation, ValueError):
                errors.append(f"{side}.entry_rules invalid position_pct: {rule.get('position_pct')}")
                continue
            if position_pct <= Decimal("0"):
                errors.append(f"{side}.entry_rules position_pct must be greater than zero")
            total_position_pct += position_pct
        if block.get("entry_rules") and (
            total_position_pct <= Decimal("1") or total_position_pct > Decimal("100")
        ):
            errors.append(
                f"{side}.entry_rules position_pct total must be greater than 1 "
                "and less than or equal to 100"
            )
        for rule in block.get("exit_rules", []):
            ref = rule.get("trigger_signal")
            if ref not in signal_ids:
                errors.append(f"{side}.exit_rules references unknown trigger_signal: {ref}")
            if rule.get("exit_action", "take_profit") not in exit_actions:
                errors.append(f"{side}.exit_rules unknown exit_action: {rule.get('exit_action')}")
            if rule.get("quantity") not in exit_quantities:
                errors.append(f"{side}.exit_rules unknown quantity: {rule.get('quantity')}")
            if rule.get("quantity") == "percentage" and rule.get("percentage") is None:
                errors.append(f"{side}.exit_rules percentage quantity requires percentage")

    for rule in strategy.get("switch_rules", []):
        ref = rule.get("trigger_signal")
        if ref not in signal_ids:
            errors.append(f"switch_rules references unknown trigger_signal: {ref}")

    for rule in strategy.get("strategy_risk_rules", []):
        rule_type = rule.get("rule_type")
        if rule_type not in risk_rule_types:
            errors.append(f"strategy_risk_rules unknown rule_type: {rule_type}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("strategy", help="Path to a strategy JSON file")
    parser.add_argument("--runner", default=RUNNER, type=Path)
    args = parser.parse_args()

    catalog = load_catalog(args.runner)
    errors = validate(Path(args.strategy), catalog)
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        raise SystemExit(1)
    print(f"OK   {args.strategy} matches runner catalog from {args.runner}")


if __name__ == "__main__":
    main()
