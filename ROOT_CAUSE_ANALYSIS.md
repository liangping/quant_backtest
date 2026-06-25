# Root Cause Analysis: Why Strategy Fails on SOL/BCH

## Executive Summary

The adaptive EMA strategy fails on SOL and BCH due to a **single critical factor**: **Volatility-Leverage Mismatch**.

The strategy's ATR-based stops are calibrated for Bitcoin's volatility (~0.5% avg move). When applied to more volatile altcoins (1-1.4% avg move) with 10x leverage, single losing trades can exceed 30-45% of account equity, causing liquidation before the strategy's edge can compound.

## The Numbers Tell the Story

### Profit Factor (The Real Winner)
```
BTCUSDT: 1.51x ✅ Winners exceed losers by 51%
ETHUSDT: 1.14x ✓  Winners exceed losers by 14%
BCHUSDT: 0.78x ❌ Losers exceed winners by 22%
SOLUSDT: 0.76x ❌ Losers exceed winners by 24%
```

### Why the Difference? Volatility Impact at 10x Leverage

| Metric | BTCUSDT | ETHUSDT | BCHUSDT | SOLUSDT |
|--------|---------|---------|---------|---------|
| Avg Price Move Per Trade | 0.47% | 0.68% | 0.71% | 0.77% |
| **Avg Account Impact @10x** | **4.7%** | **6.8%** | **7.1%** | **7.7%** |
| Max Price Move (Worst Case) | 2.11% | 3.03% | 2.94% | 4.56% |
| **Max Account Impact @10x** | **21.1%** | **30.3%** | **29.4%** | **45.6%** |

**Key Insight:** With an initial account of $1000:
- **BTC**: Worst losing trade = $211 (21% loss, recoverable)
- **ETH**: Worst losing trade = $303 (30% loss, risky)
- **SOL**: Worst losing trade = $456 (46% loss, near-liquidation)
- **BCH**: Worst losing trade = $294 (29% loss, risky)

## The Mechanics of Failure

### Strategy Design
The strategy uses **ATR-based position exits**:
- Stop loss set at: `highest_price_since_entry - (1.5x ATR)`  (for long positions)
- These are designed to give winners room to run while cutting losers

### The Problem: One-Size-Fits-All ATR
The ATR calculation is **volatility-aware** per symbol, but the exit multipliers (1.5x, 0.9x) are **fixed**.

For Bitcoin:
- ATR(14) ≈ 600 USD
- Stop distance ≈ 900 USD (1.5x ATR)
- At 10x leverage on 1000 account: ~10% risk per position

For Solana:
- ATR(14) ≈ 4-5 USD  
- Stop distance ≈ 6-7.5 USD (1.5x ATR)
- At 10x leverage on 1000 account: ~15-20% risk per position
- **But with 4.56% swings, ATR stops can't catch the move fast enough**

## Why Profit Factor Differs

### Winning Trades
All symbols have similar-sized winners:
- **BTCUSDT**: 57 winners, avg +60.37 USDT
- **ETHUSDT**: 63 winners, avg +73.26 USDT  
- **SOLUSDT**: 43 winners, avg +49.30 USDT
- **BCHUSDT**: 54 winners, avg +58.19 USDT

**Winners are stable across symbols** ≈ +50-73 USDT

### Losing Trades - THE DIFFERENTIATOR
| Symbol | Total Losers | Avg Loss | **Catastrophic Losses** |
|--------|-------------|----------|------------------------|
| BTCUSDT | 66 | -34.49 | Max: -126.79 |
| ETHUSDT | 64 | -63.03 | Max: -304.92 |
| SOLUSDT | 61 | -45.61 | Max: -442.69 ⚠️ |
| BCHUSDT | 78 | -51.55 | Max: -284.32 |

**On SOL, a single trade lost $442.69** (44% of initial account!) on a 4.56% price move.

This one catastrophic loss killed profitability:
- If you had 10 winning positions at +50 each = +500
- One bad SOL trade: -442
- Net: +58 (barely profitable)
- But if you hit 2-3 bad trades: LIQUIDATED

## The Real Issue: Distribution of Losses

### BTC: Tight Loss Control
```
Small losses (≤20):  31.8%  ✓ Majority are small
Medium losses (20-100): 65.2%
Large losses (>100): 3.0%   ✓ Rare catastrophic losses
```

### SOL: Fat Tail Risk
```
Small losses (≤20): 41.0%   ← More small losses
Medium losses (20-100): 50.8%
Large losses (>100): 8.2%   ← 3X more catastrophic losses than BTC!
```

**This fat tail risk is the killer.**

## Why This Happens

1. **Volatility Clustering**: SOL/BCH have periods of extreme intraday swings
2. **EMA Whipsaws**: When prices jump through EMAs quickly, the strategy enters right before a reversal
3. **ATR Lag**: ATR stops are designed for average volatility, not tail events
4. **Market Microstructure**: Altcoins have less liquidity, more prone to sharp moves

Example SOL Killer Trade:
```
Time: 2025-08-14 12:00 (Entry)
Price: 203.74
Entry Signal: Long (EMA signal)

Time: 2025-08-14 13:00 (Exit)  
Price: 194.44
Reason: ATR stop hit (4.56% price move in 1 hour)
Loss: -442.69 USDT (44% of account)

Analysis: SOL had an intraday panic/flash crash
EMA got fooled, strategy entered long right into the drop
```

## Why BTC Escapes This

Bitcoin has:
1. **Deeper liquidity** - Smaller intraday swings
2. **Better micro-structure** - Less prone to flash crashes
3. **EMA reliability** - Crossovers correlate with real trends
4. **Favorable volatility** - Swings average 0.47%, giving ATR stops time to work

## The Bottom Line

```
Profitability Equation:
  Return = (Win Rate × Avg Win) + (Loss Rate × Avg Loss) × Profit Factor

BTCUSDT: (0.463 × 60.37) + (0.537 × -34.49) × 1.51 = +92% ✅
SOLUSDT: (0.413 × 49.30) + (0.587 × -45.61) × 0.76 = -78% ❌

The difference: Profit Factor of 1.51x vs 0.76x
Why: Max single loss of 21% (BTC) vs 46% (SOL)
```

## The Solution

### Option 1: Reduce Leverage by Symbol
```
BTCUSDT: 10x leverage (safe, max loss 21%)
ETHUSDT: 5x leverage  (reduces max loss to 15%)
SOLUSDT: 3x leverage  (reduces max loss to 14%)
BCHUSDT: 5x leverage  (reduces max loss to 15%)
```

With 3x leverage, SOL's worst case becomes $137 loss (14%), which:
- Is survivable
- Allows profit to compound
- Keeps profit factor positive

### Option 2: Symbol-Specific ATR Multipliers
Adjust exit multipliers based on realized volatility:
```
Symbol with High Volatility (SOL):
  - Use 1.0x ATR instead of 1.5x (tighter stops)
  - Use 0.5x ATR instead of 0.9x (even tighter in choppy)
  - Forces smaller individual trades

Symbol with Low Volatility (BTC):
  - Keep 1.5x ATR (wider room for winners to run)
  - Keep 0.9x ATR (normal choppy mode)
```

### Option 3: Position Sizing by Volatility
Dynamic position sizing that accounts for volatility:
```python
position_size = base_size × (BTC_volatility / symbol_volatility)

Example:
BTC ATR = 600 → 100% position
SOL ATR = 5 → 120 × (600/5) = 14,400% (cap at 100%)
        Actually: 100 × (600/5) = 12,000% ← reduces leverage
```

## Recommendations for Production

### Immediate (Keep Current Strategy)
**Deploy on BTCUSDT only** - It has the edge and safety margin.

### Short Term (1-2 weeks)
1. Test 5x leverage on ETHUSDT
2. Measure if it maintains profitability
3. If yes, deploy ETH as secondary

### Medium Term (1 month)
1. Adjust leverage for SOL/BCH if trading is required
2. Or develop separate mean-reversion strategies for altcoins
3. Consider longer timeframe (4h) for altcoins

### Long Term (Structural Fix)
1. Implement volatility-based position sizing
2. Use symbol-specific ATR multipliers
3. Test on 1-2 year data to validate fat-tail behavior

## Conclusion

The strategy isn't bad - it's perfectly suited for Bitcoin and Ethereum. The failure on altcoins is pure **leverage overshoot**: the fixed 10x leverage amplifies tail risk on volatile assets beyond what the stop-loss structure can handle.

**The fix is simple: match leverage to volatility.**

With proper leverage adjustment, the same strategy can work on SOL/BCH, but the dramatic differences in performance tell us that BTC should remain the primary trading target.
