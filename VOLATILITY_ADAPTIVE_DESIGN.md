# Volatility-Adaptive Strategy Design

## Problem Statement

The adaptive EMA strategy works excellently on BTCUSDT (+92%) and reasonably on ETHUSDT (+32.8%), but fails catastrophically on SOLUSDT (-78.6%) and BCHUSDT (-108.4%).

**Root Cause:** Volatility-Leverage Mismatch
- BTC: 0.47% average price move per trade → 4.7% account impact at 10x leverage
- SOL: 0.77% average price move per trade → 7.7% account impact at 10x leverage
- **Worst case losses:** BTC = 21% of account, SOL = 46% of account

With fixed ATR-based stops designed for BTC's volatility, altcoins experience tail-risk losses (8.2% of trades >100 USD loss vs 3% for BTC) that overwhelm the strategy's edge.

## Solution: Volatility Tiers

The strategy adapts dynamically by detecting market volatility and adjusting:
1. Entry requirements (ADX thresholds)
2. Exit multipliers (ATR stop distances)
3. Position sizing (percentage of capital)

### Volatility Detection

Use ATR(14) vs ATR(50) comparison:
- **Low Volatility:** ATR14 < ATR50 (stable, sustained trends)
- **High Volatility:** ATR14 >= ATR50 (choppy, spike periods)

This binary detection works with existing signal framework.

### Tier-Based Rules

#### Tier 1: Low Volatility (ATR14 < ATR50)
**Characteristics:** BTC-like conditions, stable trends
```
Entry Requirements:
  - EMA50 crossover + ADX > 25 (trending regime) OR
  - EMA20 crossover + EMA100 confirmation + ADX > 25 (choppy regime)

Exit Logic:
  - Trailing stop: 1.5x ATR (let winners run)
  - Defensive stop: 0.9x ATR (quick exit in reversals)

Position Size: 100% (full position)
```

**Rationale:** Stable volatility allows standard sized positions with generous stops.

#### Tier 2: High Volatility (ATR14 >= ATR50)
**Characteristics:** SOL-like conditions, spike periods
```
Entry Requirements:
  - EMA50 crossover ONLY + ADX > 28 (higher threshold)
  - Disable EMA20 choppy regime (too many whipsaws)

Exit Logic:
  - Trailing stop: 0.8x ATR (tighter, protect capital)
  - Defensive stop: 0.5x ATR (exit immediately on reversal)

Position Size: 25-50% (reduced position)
```

**Rationale:**
- Higher ADX threshold filters out false signals in noise
- Tighter stops prevent catastrophic losses
- Smaller positions limit downside in volatility spikes
- EMA20 disabled - more prone to whipsaws when volatility is high

## Implementation Strategy

### Current Best Approach
**Adaptive Exit Multipliers Only** (simplest, lowest complexity)
```json
{
  "signal_id": "long_exit_tight",
  "atr_multiplier": "0.8"  // Used in high volatility
}
{
  "signal_id": "long_exit_normal", 
  "atr_multiplier": "1.5"  // Used in low volatility
}
```

The strategy already has `high_volatility` and `low_volatility` signals based on ATR comparison.
Just map exit rules to these conditions.

### Optional Advanced Approach
**Entry Filtering by Volatility** (adds signal quality filtering)
```json
{
  "signal_id": "long_entry_ema50_high_vol",
  "conditions": [
    "ema50_cross_up",
    "adx_medium_strong",  // ADX >= 28 instead of 25
    "high_volatility"
  ]
}
```

Requires additional signals but significantly improves entry quality in volatile periods.

## Expected Impact

### BTCUSDT (Low Vol)
- **Current:** +92% (baseline excellent)
- **After:** +90-95% (minimal change, already optimized)
- **Logic:** Stays in Tier 1, uses standard 1.5x/0.9x exits

### ETHUSDT (Med Vol)
- **Current:** +32.8% (good)
- **After:** +35-40% (slight improvement)
- **Logic:** Some high vol periods trigger tighter 0.8x stops, reducing whipsaws

### SOLUSDT (High Vol)
- **Current:** -78.6% (catastrophic failure)
- **After:** -15% to +5% (breakeven to slight profit)
- **Impact:** Max loss reduced from 45.6% to ~15%, enables survival
- **Logic:** Tight 0.8x ATR stops prevent catastrophic single-trade losses

### BCHUSDT (Med-High Vol)
- **Current:** -108.4% (liquidation)
- **After:** -10% to +10% (trading-ready)
- **Impact:** Tighter stops, reduced position frequency in spikes
- **Logic:** Similar to SOL - volatility tiers prevent ruin

## Multi-Strategy Portfolio

Rather than one adaptive strategy, consider:

```
BTCUSDT:  ema_adaptive_regime_10x (10x leverage, original settings)
ETHUSDT:  ema_adaptive_regime_10x (7x leverage, tighter stops)
SOLUSDT:  ema_adaptive_regime_10x (3x leverage, Tier 2 rules)
BCHUSDT:  ema_adaptive_regime_10x (5x leverage, Tier 2 rules)
```

**Rationale:** Leverage adjustment is simpler than complex conditional logic, and equally effective:
- 3x leverage on SOL: Max loss = 13.7% (safe)
- 5x leverage on BCH: Max loss = 14.7% (safe)

## Signal Design Notes

### Volatility Tier Detection
The framework already provides:
- `high_volatility`: `atr14 >= atr50`
- `low_volatility`: `atr14 < atr50`

These can directly condition exit rule selection.

### Entry Filtering (Optional)
Add ADX expression signals:
```json
{
  "signal_id": "adx_medium_strong",
  "expression": "adx14",
  "expression_operator": "gte",
  "expression_value": "28"
}
```

Then create volatility-specific entry signals:
```json
{
  "signal_id": "long_entry_trending_adaptive",
  "conditions": [
    "ema50_cross_up",
    "adx_medium_strong",  // Tier 2 requires higher threshold
    "high_volatility"
  ]
}
```

### Exit Multiplier Calibration
Current approach uses fixed ATR multipliers. Volatility-adaptive approach:
- **Low Vol:** 1.5x (allow 1.5 × $600 = $900 loss on BTC = 9% account)
- **High Vol:** 0.8x (allow 0.8 × $5 = $4 loss on SOL = 0.4% account)

For consistent risk sizing:
```
Target max loss = 15% of account
Exit multiplier = (0.15 × account) / (10x leverage × atr14)
```

## Implementation Roadmap

### Phase 1: Exit Multiplier Adaptation (Immediate)
- Add high_vol/low_vol conditional exit rules
- Use existing `high_volatility` and `low_volatility` signals
- Test on all symbols
- **Expected: Moderate improvement** (+5-15%)

### Phase 2: Entry Filtering (Optional)
- Add ADX expression signals for Tier 2 (ADX >= 28)
- Create volatility-specific entry composites
- Disable EMA20 regime in high volatility
- **Expected: Significant improvement** (+20-30%)

### Phase 3: Leverage Adjustment (Alternative)
- Keep strategy unchanged
- Adjust leverage per symbol (3x SOL, 5x BCH, 10x BTC/ETH)
- Simpler than signal modifications
- **Expected: Same result, different approach**

## Conclusion

Volatility-adaptive rules transform the strategy from a one-size-fits-all approach to one that respects market microstructure. By tightening stops and filtering entries during volatile periods, catastrophic losses that occur on altcoins become manageable tail-risk events.

The key insight: **Profitability depends on profit factor (ratio of wins to losses).** With fixed stops on high-volatility assets, losses become too large relative to wins. Adaptive stops maintain the critical 1.2x-1.5x win-to-loss ratio across all market conditions.

Recommendation: Start with Phase 1 (exit multiplier adaptation) as it requires minimal strategy changes and provides immediate protection against volatility spikes. If additional edge is needed, progress to Phase 2 or Phase 3.
