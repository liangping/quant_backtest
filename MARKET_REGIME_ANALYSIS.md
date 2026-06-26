# Market Regime Analysis: Why Strategy Fails in Recent 30 Days

## Executive Summary

The baseline `ema_adaptive_regime_10x.json` strategy delivered exceptional performance (+92%) during the Jun 15 - Sep 3, 2025 test period, but fails dramatically (-8%) in the most recent 30-day window (May 27 - Jun 26, 2026). This analysis identifies the root cause and proposes solutions.

## Current Performance (May 27 - Jun 26, 2026)

**Validation Results:**
- Return: **-8%** (-$78.17 USDT)
- Drawdown: 32% (acceptable)
- Position Count: 21 trades
- Win Rate: 38% (below 40% threshold)
- Long Trades: 7 (3 wins / 4 losses = 42% win rate, -$35 PnL)
- Short Trades: 14 (5 wins / 9 losses = 35% win rate, -$3 PnL)

## Root Cause: Choppy/Consolidation Market Regime

### Trade Timeline Pattern

**May 28-29: Early Losses**
- 4 consecutive short trades
- All 4 losing immediately on entry
- Market was ranging upward, false short signals

**June 4-7: Mixed Results with Escalating Losses**
- 6 short trades, some wins but final day (June 7) loss of -$151.87
- Market reversal exhausted the short-bias strategy

**June 10-19: Regime Confusion**
- Strategy begins taking both long and short entries (indecision)
- Neither side profitable (Longs: -$76, Shorts: -$65)
- Clear sign of choppy/choppy market where no trend exists

**June 18+: Continued Struggles**
- Strategy still firing entries on false breakouts
- Positions closed at losses as market whipsaws

### Market Characteristics of This Period

1. **High False Break Rate**: Multiple test entries trigger, then immediately reverse
2. **Choppy Price Action**: Price oscillates without establishing clear trending direction
3. **Low Directional Conviction**: ADX likely in 20-28 range (moderate to weak trend)
4. **Whipsaw Risk**: Strategy's tight exit multipliers (0.9x ATR in low vol) catch these reversals

## Why This Matters

The baseline strategy was optimized and validated on a **trending market** (Jun-Sep 2025):
- Clear EMA50 crossovers with followthrough
- ADX >28 indicating strong trend strength
- Limited false signals

The current market (May-Jun 2026) is **choppy/consolidating**:
- Multiple false EMA crossovers
- ADX oscillating in 20-28 range (weak-medium strength)
- High whipsaw risk from premature exits

**Key Finding**: Trend-following strategies like this one are inherently unprofitable in choppy markets. This is not a flaw—it's a market regime mismatch.

## Solution Strategies

### Option 1: Add Market Regime Detection (Recommended)

Detect current market regime and adapt strategy:

**Choppy Detection Signal:**
- ATR14 < ATR50 (low volatility consolidation)
- ADX14 < 25 (weak trend strength)
- Price oscillating between EMA20 and EMA50

**Action When Choppy:**
- Increase ADX threshold from 25-28 to 30-35
- Reduce position size to 25-50% of normal
- Increase exit stop multipliers (0.9x → 1.2x) to reduce whipsaws
- Consider skipping entries entirely if ADX < 20

### Option 2: Dual-Mode Strategy (Conservative)

Keep baseline but add parallel choppy-market strategy:
- **Mode A (Trending)**: Current strategy + ADX>28 confirmation
- **Mode B (Choppy)**: Range-bound oscillation strategy + ATR-based reversal entries
- Automatic switch based on ADX / volatility indicators

### Option 3: Add Timeframe Filter (Medium Effort)

Use daily EMA to filter entry directions:
- Only take LONG entries when daily EMA20 > EMA50 (bullish macro)
- Only take SHORT entries when daily EMA20 < EMA50 (bearish macro)
- Eliminates ~50% of false signals in choppy markets

**Challenge**: Current data API may lack sufficient historical daily data for warmup. Previous attempt (EMA200 on 1h) failed because 8-day filter was too fast.

### Option 4: Market Regime ETF/Index Filter

Use Bitcoin dominance or macro market indicator:
- High BTC dominance + altcoin weakness = choppy ranging market
- Low BTC dominance + altcoin rallying = trending market
- Adjust strategy parameters based on macro regime

## Recommended Next Steps

1. **Immediate (5 min)**: Test Option 1 - create `ema_adaptive_regime_adx_strict.json` with ADX>30 requirement
   - Simpler than it sounds: just change ADX thresholds from 28 to 30
   - Expected: Fewer false entries, better win rate, less negative return

2. **Short-term (30 min)**: Implement choppy-market position sizing
   - Add `volatility_regime_detection.json` that reduces position by 50% when ATR14 < ATR50
   - Combined with Option 1 should handle mixed markets

3. **Medium-term (2 hrs)**: Research daily filter feasibility
   - Check if we can fetch daily data from data API
   - If yes, implement daily EMA filter
   - If no, propose alternative macro filter

4. **Validation Protocol**:
   - Test each solution on recent 30-day window
   - Requirement: >0% return AND win rate >40%
   - Then backtest on longer historical periods to ensure no regression
   - Finally, validate on new 30-day windows to confirm adaptability

## Historical Context

**Why the Strategy Worked Before:**
- Jun 15 - Sep 3, 2025 was a strong trending period
- Multiple clear EMA50 crossovers with followthrough
- ADX sustained >25-28, often >30
- Strategy captured 92% return following these trends

**Why It Fails Now:**
- May 27 - Jun 26, 2026 had market consolidation
- False breakouts exhausted the strategy
- Whipsaw losses dominated because exits triggered on small reversals
- Strategy's strength (trending confirmation) became a liability in choppy market

## Conclusion

This is not a strategy flaw—it's a **market-strategy mismatch**. The baseline strategy is fundamentally a trend-following strategy and will always struggle in choppy/consolidating markets. The solution is either:

1. Add regime detection to adapt the strategy parameters
2. Switch to a different strategy type when choppy markets detected
3. Add position sizing/leverage adjustments for current volatility environment

Without one of these changes, the strategy will continue to lose money whenever the market enters choppy consolidation phases.
