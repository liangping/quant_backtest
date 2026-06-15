# Bug Report: cash_basis Calculation Error in StreamingStrategyCore

## Summary
The `cash_basis` calculation in `StreamingStrategyCore` has a critical bug that causes incorrect `realized_pnl` and `final_equity` values in the backtest summary.

## Location
File: `rust/crates/quant-core/src/streaming.rs`
Lines: 2744, 2751-2752

## Problem Description

### Current Implementation
When opening a position (line 2744):
```rust
self.cash_basis -= fill.price * fill.quantity / self.config.basic.leverage;
```

When closing a position (lines 2751-2752):
```rust
self.cash_basis += closed_pnl
    + fill.price * fill.quantity / self.config.basic.leverage;
```

### The Bug
The margin is calculated using **different prices** for open vs close operations:
- Open margin = `open_price * quantity / leverage`
- Close margin = `close_price * quantity / leverage`

For a SHORT position with a loss:
- If entry_price < exit_price (loss for short)
- Then close_margin > open_margin
- The difference exactly equals the PnL amount

This causes the margin changes to **cancel out** the PnL, making `cash_basis` return to near its initial value after each complete trade cycle.

### Example (Jan 2026 data)
Position 1 (Short):
- Open: cash_basis -= $10,000.00 → cash_basis = -$9,000
- Close: cash_basis += (-$95.21) + $10,095.21 → cash_basis = $1,000

After the complete cycle, cash_basis returns to $1,000 (the initial value), effectively losing track of the -$95.21 PnL.

### Impact
After all positions are closed:
- Expected cash_basis: $1,000 + sum(PnLs) = $1,091.71
- Actual cash_basis: ~$1,000 (due to margin cancellation)
- Realized PnL should be: +$59.72 (after fees)
- But summary shows: -$132.88 (incorrect)
- Difference: $192.60

## Root Cause Analysis

According to the memory specification:
> "cash_basis始终追踪实际已实现PnL，不在平仓后重置"

The current implementation violates this principle by deducting margin on open and adding it back on close using different prices, which effectively resets cash_basis after each trade.

## Proposed Fix

### Option 1: Remove margin tracking from cash_basis (Recommended)
Since cash_basis should only track realized PnL, remove the margin deduction/addition logic:

```rust
// On open (line 2744): Remove this line entirely
// self.cash_basis -= fill.price * fill.quantity / self.config.basic.leverage;

// On close (lines 2751-2752): Only add PnL
self.cash_basis += closed_pnl;
```

### Option 2: Store and reuse the exact margin amount
Store the margin used when opening, and release the same amount when closing:

```rust
// In OpenLot struct, add a field:
// margin_used: Decimal

// On open:
let margin = fill.price * fill.quantity / leverage;
self.cash_basis -= margin;
lot.margin_used = margin;

// On close:
self.cash_basis += closed_pnl + lot.margin_used;  // Use stored margin, not recalculated
```

## Test Case
Run backtest with strategy `ema7_50_trend` on Jan 2026:
- Expected realized_pnl: +$59.72
- Actual (buggy) realized_pnl: -$132.88
- After fix: Should match expected value

## Additional Notes
The comment on line 146 states:
> "StreamingStrategyCore.cash_basis does not deduct fees."

This is correct - fees are tracked separately in `total_fees`. However, the margin tracking issue is separate from fee tracking and needs to be fixed independently.
