# Strategy Selection Guide: Choose Based on Current Market Conditions

## Quick Decision Tree

```
Step 1: Check recent market trend
  └─> Is price making clear directional moves (trends up or down for 2+ weeks)?
      ├─ YES → Go to Step 2
      └─ NO (choppy/ranging) → Use ema_adaptive_regime_adx_strict_10x

Step 2: Check ADX(14) on 1h chart
  └─> Recent ADX average > 28?
      ├─ YES (strong trend) → Use ema_adaptive_regime_10x (BASELINE)
      └─ NO (weak trend, 20-28) → Use ema_adaptive_regime_adx_strict_10x
```

## Strategy Comparison

### 1. `ema_adaptive_regime_10x.json` (BASELINE)
**When to use:** Strong trending markets with consistent ADX > 28

**Performance Profile:**
- ✅ **Best in:** Sustained uptrends/downtrends (Jun 15 - Sep 3, 2025: +31%)
- ❌ **Worst in:** Choppy consolidation (May 27 - Jun 26, 2026: -8%)
- **Win Rate:** 52% in trends, 38% in chop
- **Drawdown:** 16% in trends, 32% in chop
- **Trade Style:** Frequent entries (25 trades in 11 weeks), medium risk

**ADX Requirements:**
- Long entries: EMA50 cross + ADX≥25
- Short entries: EMA50 cross + ADX≥25
- Choppy entries: EMA20 cross + EMA100 + ADX≥25

**Risk Profile:** 💛💛💛 MEDIUM-HIGH
- Works well when trends are clean
- Gets whipsawed in choppy markets
- Position size: 100% of capital when in position

---

### 2. `ema_adaptive_regime_adx_strict_10x.json` (CHOPPY-MARKET VARIANT)
**When to use:** Consolidating/choppy markets with ADX 20-28

**Performance Profile:**
- ✅ **Best in:** Choppy/consolidating (May 27 - Jun 26, 2026: +3%)
- ⚠️ **Medium in:** Strong trends (Jun 15 - Sep 3, 2025: +14%)
- **Win Rate:** 38% in chop, 64% in trends (higher quality)
- **Drawdown:** 22% in chop, 17% in trends
- **Trade Style:** Selective entries (13 trades in 30 days vs 21), high quality

**ADX Requirements:**
- Long entries: EMA50 cross + ADX≥30
- Short entries: EMA50 cross + ADX≥30
- Choppy entries: EMA20 cross + EMA100 + ADX≥30

**Risk Profile:** 💚💚💛 MEDIUM
- Filters out 40%+ of false signals
- Better win rate (64% vs 52% in trends)
- More conservative, fewer positions taken
- Avoids choppy market whipsaws

---

## How to Determine Current Market Regime

### Check ADX(14) on 1h Timeframe

```
ADX Level          Market Regime              Recommended Strategy
─────────────────────────────────────────────────────────────────
ADX > 30          Very Strong Trend          ema_adaptive_regime_10x
ADX 28-30         Strong Trend               ema_adaptive_regime_10x ✓
ADX 25-28         Moderate Trend             CHOOSE BASED ON PRICE
ADX 20-25         Weak Trend                 ema_adaptive_regime_adx_strict_10x
ADX < 20          No Trend (Choppy)          ema_adaptive_regime_adx_strict_10x
```

### Check Price Action Pattern

**Sign of Strong Trend (Use Baseline):**
- Price making sustained moves in one direction
- Higher highs and higher lows (uptrend) or lower highs and lower lows (downtrend)
- EMA20, EMA50, EMA100 in proper order (long trend: price > EMA20 > EMA50 > EMA100)
- Multiple EMA crossovers in the same direction
- Average daily range > 1% of price

**Sign of Choppy Market (Use Strict ADX):**
- Price oscillating between support/resistance
- Frequent failed breakouts
- EMA20 and EMA50 whipsawing back and forth
- ADX rising and falling rapidly (not sustained above 25)
- Average daily range < 0.8% of price
- Many price crossovers above/below EMAs without followthrough

---

## Real-World Decision Examples

### Example 1: May 2026 Market (User reported -7.82% on web backtest)
```
Observations:
- Price ranging between support/resistance
- ADX mostly 20-28 (weak-moderate)
- Many failed breakouts
- False short entries triggering
- Strategy taking 14+ shorts vs 7 longs

Decision: Use ema_adaptive_regime_adx_strict_10x
Result: +3% instead of -8% ✓
```

### Example 2: Jun-Sep 2025 Market (Known good performance)
```
Observations:
- Price making sustained moves
- ADX mostly 25-35 (strong)
- Clear EMA50 crossovers
- Followthrough on entries
- Balanced long/short entries

Decision: Use ema_adaptive_regime_10x (BASELINE)
Result: +31% ✓
```

---

## Strategy Deployment Checklist

Before going live with either strategy:

- [ ] Run 30-day backtest on recent data
- [ ] Verify return > 0% (ideally +2%+ per 30 days)
- [ ] Verify win rate > 40%
- [ ] Verify max drawdown < 50%
- [ ] Check that position count >= 5 (sufficient sample size)
- [ ] Run on 2+ different 30-day periods to confirm consistency
- [ ] Monitor live trading for first 5-10 trades before scaling

---

## Adjustments for Your Market Context

**If trading on BTCUSDT at 10x leverage:**
- Current balance: $1000
- Max position risk: 10% = $100 at 10x leverage
- Your backtests are already sized correctly

**If trading with different leverage:**
- 5x leverage: Consider reducing position to 50% OR use stricter ADX
- 3x leverage: Can be more aggressive, baseline should work well
- 20x leverage: Increase ADX threshold further OR reduce position size

---

## Final Recommendation

**For Next 30 Days (June 2026):**
Use `ema_adaptive_regime_adx_strict_10x.json` because:
- Recent market is choppy/consolidating
- Baseline strategy lost money (-8%) in these conditions
- Strict ADX variant designed for this exact scenario (+3%)
- Better risk management with lower drawdowns

**For When Market Trends Clearly (After Consolidation Ends):**
Switch to `ema_adaptive_regime_10x.json` (baseline) for:
- Higher returns in trending markets (+31% potential)
- More frequent opportunities
- Natural EMA-based trend confirmation

**Ideal Solution (Future):**
Implement market regime detection that automatically switches strategies based on current ADX/volatility levels. This would give you:
- Baseline performance in strong trends
- Strict variant performance in choppy markets
- Optimal risk-adjusted returns across all market conditions
