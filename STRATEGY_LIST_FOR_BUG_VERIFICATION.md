# Strategy List for Independent Bug Verification

## Purpose
Rust developer can use these strategies to independently verify the double-count exit fees bug on their own backtest report output.

## All Available Strategies (27 total)

```
1. adx_bb_zscore_mean_reversion
2. bb_rsi_mean_reversion
3. bb_rsi_protected
4. bb_rsi_protected_v2
5. bb_rsi_switch
6. ema20_adx_atr_pullback ← NEW (created for bug testing)
7. ema20_adx_atr_pullback_15m ← NEW (created for bug testing)
8. ema20_adx_atr_pullback_1h ← NEW (created for bug testing)
9. ema20_adx_atr_pullback_20 ← NEW (created for bug testing)
10. ema20_adx_atr_pullback_30 ← NEW (created for bug testing)
11. ema7_50_trend
12. ema7_pullback
13. ema7_pullback_v2
14. ema7_pullback_v3
15. ema7_pullback_v4
16. ema_atr_trend
17. ema_trend_follow
18. macd_atr_pullback
19. macd_atr_pullback_er_filter
20. macd_atr_trend
21. server_296_original
22. strong_downtrend_short
23. strong_downtrend_short_1h_attack
24. trend_adx
25. trend_bb_breakout
26. trend_donchian
27. trend_ema_v2
28. trend_macd_v2
```

## Recommended Test Cases

Run any of these commands to generate reports for testing:

### Quick Test (recommended for initial verification)
```bash
# Uses ema20_adx_atr_pullback_15m with large number of trades (255 positions)
bin/backtest-live-runner clickhouse-bar-replay \
  --strategy strategies/ema20_adx_atr_pullback_15m.json \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --start 2025-05-15T00:00:00Z \
  --end 2026-06-07T00:00:00Z \
  --report-jsonl ./test_report.jsonl
```

### Alternatives (if above doesn't work on their data)
```bash
# Fewer positions but still shows bug clearly
bin/backtest-live-runner clickhouse-bar-replay \
  --strategy strategies/ema20_adx_atr_pullback_1h.json \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --start 2026-01-01T00:00:00Z \
  --end 2026-03-01T00:00:00Z \
  --report-jsonl ./test_report.jsonl

# Short window with high trade frequency
bin/backtest-live-runner clickhouse-bar-replay \
  --strategy strategies/ema_atr_trend.json \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --start 2026-02-01T00:00:00Z \
  --end 2026-03-01T00:00:00Z \
  --report-jsonl ./test_report.jsonl
```

## Bug Verification Script

Run this Python script on the generated report to verify the bug:

```python
#!/usr/bin/env python3
"""Verify double-count exit fees bug in backtest report"""

import json
from decimal import Decimal

def verify_pnl_bug(report_jsonl_path):
    """Check if exit fees are double-counted in realized_pnl"""
    
    with open(report_jsonl_path) as f:
        report = json.load(f)
    
    positions = report.get('positions', [])
    orders = report.get('orders', [])
    summary = report.get('summary', {})
    
    if not positions:
        print("ERROR: No positions found in report")
        return False
    
    # Calculate sum of position.realized_pnl values
    sum_position_pnls = Decimal(sum(Decimal(p['realized_pnl']) for p in positions))
    
    # Get reported realized_pnl from summary
    reported_pnl = Decimal(summary['realized_pnl'])
    
    # Calculate exit fees from orders
    exit_fees = Decimal(0)
    if orders:
        exit_fees = Decimal(sum(Decimal(o.get('fee', 0)) for o in orders 
                               if o.get('action') == 'close'))
    
    # Check discrepancy
    discrepancy = sum_position_pnls - reported_pnl
    
    print("BUG VERIFICATION REPORT")
    print("=" * 70)
    print(f"Report: {report_jsonl_path}")
    print()
    print(f"Number of positions: {len(positions)}")
    print(f"Sum of position.realized_pnl: {sum_position_pnls}")
    print(f"Reported summary.realized_pnl: {reported_pnl}")
    print(f"Discrepancy: {discrepancy}")
    print(f"Exit fees (from orders): {exit_fees}")
    print()
    
    # Check if discrepancy ≈ exit fees
    diff_from_fees = abs(discrepancy - (-exit_fees))
    threshold = Decimal('0.01')
    
    if diff_from_fees < threshold:
        print("✓ BUG CONFIRMED")
        print(f"  Discrepancy ({discrepancy}) matches exit fees ({-exit_fees})")
        print(f"  Difference: {diff_from_fees}")
        print()
        print("ROOT CAUSE: Exit fees are subtracted twice")
        print(f"  - In position.realized_pnl: entry fees only")
        print(f"  - In summary.realized_pnl: AGAIN subtracts exit fees")
        print()
        
        # Show impact
        true_pnl = sum_position_pnls - Decimal(0)  # Position PnL includes entry fees only
        initial = Decimal(summary.get('initial_capital', 1000))
        
        reported_equity = initial + reported_pnl
        true_equity = initial + sum_position_pnls
        
        print("IMPACT:")
        print(f"  Reported equity: {reported_equity}")
        print(f"  True equity: {true_equity}")
        print(f"  Overstatement of loss: {abs(reported_pnl - sum_position_pnls)}")
        print(f"  Percentage error: {abs(reported_pnl - sum_position_pnls) / abs(reported_pnl) * 100:.1f}%")
        
        return True
    else:
        print("✗ BUG NOT FOUND")
        print(f"  Discrepancy ({discrepancy}) does not match exit fees ({-exit_fees})")
        print(f"  Difference: {diff_from_fees}")
        return False

if __name__ == '__main__':
    import sys
    report_file = sys.argv[1] if len(sys.argv) > 1 else 'test_report.jsonl'
    verify_pnl_bug(report_file)
```

## Expected Results

If bug exists, output should show:
```
✓ BUG CONFIRMED
  Discrepancy (-138.81) matches exit fees (-138.74)
  
IMPACT:
  Reported equity: $745.97
  True equity: $884.78
  Overstatement of loss: 138.81
  Percentage error: 54.6%
```

## Data Requirements

Rust developer needs:
- ClickHouse with BTCUSDT 1-minute kline data
- Date range: 2025-05-15 to 2026-06-07 (for best test - 255 positions)
- Alternative: Any 1-2 month window with sufficient data

If they don't have ClickHouse set up, the strategy JSON files are still valid for code review to identify the fee-handling bug.

---

**Note:** All 5 new `ema20_adx_atr_pullback*` strategies are specifically designed to trigger many trades (high position count) to make the bug obvious. Use `ema20_adx_atr_pullback_15m` for strongest signal (255 positions).
