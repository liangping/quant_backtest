# Multi-Symbol Testing Guide for Adaptive EMA Strategy

## Current Status

The adaptive EMA regime detection strategy has been validated on **BTCUSDT** with excellent results:
- **+92% annual return** (2025-06-01 to 2026-06-06)
- Outperforms pure EMA50 (+48.2%) and baseline EMA20/EMA100 (+36.7%)
- Properly adapts between trending (EMA50) and choppy (EMA20+EMA100) regimes

## Strategy Files Created

For testing on other symbols, the following strategy files have been pre-created:

1. **strategies/ema_adaptive_regime_10x_ethusdt.json** - For Ethereum
2. **strategies/ema_adaptive_regime_10x_solusdt.json** - For Solana  
3. **strategies/ema_adaptive_regime_10x_bchusdt.json** - For Bitcoin Cash

These are identical to the BTCUSDT version but with symbol-specific configuration.

## How to Test Other Symbols

### Step 1: Fetch Market Data

```bash
# For ETH (adjust dates as needed)
python3 scripts/sync_data_api_klines.py \
  --exchange binance_um_futures \
  --symbol ETHUSDT \
  --start 2025-06-01T00:00:00Z \
  --end 2026-06-06T00:00:00Z

# For SOL
python3 scripts/sync_data_api_klines.py \
  --exchange binance_um_futures \
  --symbol SOLUSDT \
  --start 2025-06-01T00:00:00Z \
  --end 2026-06-06T00:00:00Z

# For BCH
python3 scripts/sync_data_api_klines.py \
  --exchange binance_um_futures \
  --symbol BCHUSDT \
  --start 2025-06-01T00:00:00Z \
  --end 2026-06-06T00:00:00Z
```

### Step 2: Validate Strategies

```bash
python3 scripts/validate_strategy.py strategies/ema_adaptive_regime_10x_ethusdt.json
python3 scripts/validate_strategy.py strategies/ema_adaptive_regime_10x_solusdt.json
python3 scripts/validate_strategy.py strategies/ema_adaptive_regime_10x_bchusdt.json
```

### Step 3: Run Backtests

```bash
# Full year test for ETH
python3 scripts/run.py single \
  --strategy ema_adaptive_regime_10x_ethusdt \
  --start 2025-06-01 \
  --end 2026-06-06

# Monthly breakdown for ETH
python3 scripts/run.py monthly --strategy ema_adaptive_regime_10x_ethusdt

# Repeat for SOL and BCH
```

## Expected Variations by Symbol

Different symbols may show different performance characteristics:

| Symbol | Expected Characteristic | Reasoning |
|--------|-------------------------|-----------|
| **ETHUSDT** | Similar to BTC | Highly correlated with BTC, strong institutional trading |
| **SOLUSDT** | More volatile | Smaller market cap, higher volatility, regime changes more frequent |
| **BCHUSDT** | Lower correlation | Weaker correlation with BTC, may benefit from independent regime analysis |

## Key Metrics to Track

When testing other symbols, compare against BTCUSDT baseline:

1. **Total Return**: Should be >25% for strategy to be competitive
2. **Monthly Consistency**: Check if adaptive logic works across all regimes
3. **Drawdown**: Should be <50% (BTCUSDT had 39.9%)
4. **Win Rate**: Compare positions with profitable exits
5. **Regime Detection**: Verify ADX thresholds work for each symbol

## Troubleshooting

### Data Fetch Fails
- Ensure ClickHouse is running: `docker ps | grep clickhouse`
- Verify network connectivity to https://data.becole.com
- Check credentials in `.env` file

### Backtest Crashes
- Validate strategy JSON syntax
- Ensure all required indicators are supported
- Check ClickHouse has data for the symbol/period

### Unexpected Results
- Check if leverage settings need adjustment (currently 10x)
- Verify initial capital consistency (1000 USDT)
- Compare entry/exit signal counts across symbols

## Notes

- All symbols use 1h timeframe (same as BTCUSDT baseline)
- Leverage is fixed at 10x (Binance USDT futures standard)
- Initial capital is 1000 USDT (consistent for comparison)
- Volatility-adaptive exits are active (0.9x/1.5x ATR)
- Position mode is "switch" (can hold long/short/flat)

## Next Steps

After testing confirms performance on other symbols:
1. Consider parameter optimization per symbol
2. Evaluate portfolio approach (long BTC + long ETH simultaneously)
3. Test longer time periods (2+ years if data available)
4. Compare against other regime detection methods (MACD, Bollinger Bands)
