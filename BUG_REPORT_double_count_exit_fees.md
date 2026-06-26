# Bug Report: Double-Counting Exit Fees in Realized PnL Calculation

## Summary
The backtest engine double-counts exit fees when calculating `realized_pnl`, causing all strategies to appear to lose significantly more than they actually do. Exit fees are subtracted once at the position level and again when aggregating the summary, resulting in **54% overstatement of losses**.

## Impact
- All backtest results show inflated losses
- Actual losses are ~1.5x better than reported (e.g., −25.4% reported = −11.5% actual)
- Makes unprofitable strategies appear worse than reality
- Makes the engine unsuitable for strategy evaluation until fixed

## Root Cause
The fee calculation has an architectural mismatch between position-level and summary-level fee handling:

### Position-Level Calculation
Each closed position's `realized_pnl` includes **entry fees only**:
```
position.realized_pnl = (exit_price - entry_price) * quantity - entry_fee
```
**Exit fees are NOT included in position.realized_pnl**

### Summary-Level Calculation  
The reported `realized_pnl` subtracts exit fees AGAIN:
```
summary.realized_pnl = sum(all position.realized_pnl) - sum(all exit fees)
```

### Result: Double Deduction
- Entry fees: subtracted once ✓ (correct)
- Exit fees: subtracted twice ✗ (BUG)

## Verification with Real Data

### Test Case: ema20_adx_atr_pullback_15m Strategy (May-June 2026)

**From backtest report:**
- 255 closed positions
- Entry fees (255): $138.81
- Exit fees (255): $138.74
- Sum of position.realized_pnl values: **−$115.22**
- Reported summary.realized_pnl: **−$254.03**

**Analysis:**
```
Expected realized_pnl = sum(position.realized_pnl)
                      = −$115.22

Actual reported realized_pnl = −$254.03

Difference = −$254.03 − (−$115.22) = −$138.81
           ≈ exit fees ($138.74)
           
Conclusion: Exit fees subtracted twice
```

**True equity:**
- Reported: $745.97 (loss of −25.4%)
- Actual: $884.78 (loss of −11.5%)
- Overstatement: 54%

### Sample Position Verification

Position 1 (SHORT):
```
Entry Price: 102284.3
Exit Price:  102439.5
Quantity:    0.02933004
Entry Fee:   $0.6000
Exit Fee:    $0.6009

Price Diff PnL = (102284.3 - 102439.5) * 0.02933004 = −$4.552
Expected position.realized_pnl = −$4.552 − $0.6000 = −$5.152
Reported position.realized_pnl = −$5.153 ✓ (entry fee only)

But when summing 255 positions:
Sum = −$115.22 (includes all entry fees, no exit fees)

Then summary calculates:
summary.realized_pnl = −$115.22 − $138.74 (exit fees) = −$253.96 ≈ −$254.03 ✗
```

## Affected Code Location
Based on BUG_REPORT_cash_basis.md reference and fee handling patterns:
- File: `rust/crates/quant-core/src/streaming.rs` (likely)
- Sections handling:
  - `position.realized_pnl` calculation (position close event)
  - `summary.realized_pnl` aggregation (backtest finalization)

## Proposed Fix

### Option 1: Include Exit Fees in Position PnL (Recommended)
```rust
// When closing a position:
position.realized_pnl = (price_diff * quantity) - entry_fee - exit_fee

// When calculating summary:
summary.realized_pnl = sum(all position.realized_pnl)
// Do NOT subtract fees again
```

### Option 2: Exclude Both Fees from Position, Track Separately
```rust
// Position level (gross PnL):
position.realized_pnl = price_diff * quantity
position.entry_fee = entry_fee
position.exit_fee = exit_fee

// Summary level:
summary.realized_pnl = sum(price_diff * qty) - sum(entry_fees) - sum(exit_fees)
// Fees subtracted ONCE at summary level only
```

## Reproduction Steps

1. Run any backtest with switch_mode strategy (uses many entries/exits)
2. Extract the report JSON
3. Calculate: `sum(position.realized_pnl for all positions)`
4. Compare to: `summary.realized_pnl`
5. Difference should be approximately equal to sum of all exit fees
6. If difference ≈ exit fees, bug is confirmed

### Test Command
```bash
python3 scripts/run.py single \
  --strategy ema20_adx_atr_pullback_15m \
  --symbol BTCUSDT \
  --start 2025-05-15 \
  --end 2026-06-07
  
# Extract report: data/backtest_reports/ema20_adx_atr_pullback_15m_btcusdt_2025_05_15_2026_06_07.jsonl
```

## Validation After Fix
```python
# Script to validate fix:
import json
from decimal import Decimal

with open('report.jsonl') as f:
    data = json.load(f)

positions = data['positions']
summary = data['summary']

# After fix, these should be equal (within rounding):
sum_pnls = Decimal(sum(Decimal(p['realized_pnl']) for p in positions))
reported_pnl = Decimal(summary['realized_pnl'])

assert abs(sum_pnls - reported_pnl) < Decimal('0.01'), f"Mismatch: {sum_pnls} vs {reported_pnl}"
print("✓ Fee calculation bug is FIXED")
```

## Related Issues
- BUG_REPORT_cash_basis.md mentions similar margin calculation issues
- Both bugs affect the accuracy of PnL reporting
- May be caused by the same underlying fee-handling architecture

## Severity
**CRITICAL** — All backtested results are mathematically incorrect and unsuitable for strategy evaluation until this is fixed.

---

**Report Generated:** 2026-06-22  
**Test Data:** BTCUSDT 1-minute klines, May 11 2025 - June 7 2026  
**Affected Binary:** `/home/user/quant_backtest/bin/backtest-live-runner`
