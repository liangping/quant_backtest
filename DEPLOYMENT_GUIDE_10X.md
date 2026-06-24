# Live Trading Deployment Guide - 10x Leverage Strategy

## Strategy Summary
**File:** `strategies/ema20_adx_production_10x.json`

### Performance (Backtested Jun 2025 - Jun 2026)
- **Total Return:** +94.4%
- **Max Drawdown:** 34.1%
- **Profitable Months:** 10/13 (77%)
- **Win Rate:** 49.3% (37/75 positions)
- **Profit Factor:** 1.63x
- **Avg Position Size:** ~76 positions per year

### Strategy Logic
**Entry Signals:**
- EMA20 crosses above/below current price
- Price stays above/below EMA100 (trend filter)
- ADX > 25 (confirms strong trend)

**Exit Signals:**
- ATR pullback: 1.5× ATR from highest/lowest since entry
- Acts as trailing stop-loss for profit-taking

**Position Mode:** Switch (long/short bidirectional)
**Leverage:** 10x
**Timeframe:** 1-hour candles

## ⚠️ CRITICAL RISK WARNINGS

### Account Risk
- **34% max drawdown** means account could drop from $1000 → $660
- Higher leverage amplifies both gains AND losses
- A series of losing trades could liquidate the account

### Market Risk
- Strategy is optimized for 2025-2026 data
- Past performance ≠ future results
- Market conditions change; strategy may underperform

### Recommended Safeguards
1. **Start small:** Use only 10-25% of your capital initially
2. **Position limits:** Cap max open positions to 2-3
3. **Daily loss limit:** Consider stopping if loss >5% in one day
4. **Monitor daily:** Check performance at least once per day

## Deployment Instructions

### Prerequisites
1. Exchange account set up (Binance recommended)
2. API keys with trading enabled
3. ClickHouse database synced with latest price data
4. `backtest-live-runner` binary built and tested

### Step 1: Verify Strategy
```bash
python3 scripts/validate_strategy.py strategies/ema20_adx_production_10x.json
```

### Step 2: Test in Paper Trading (Recommended)
```bash
# Set up paper trading mode in your exchange
# Then run same command as live trading
bin/backtest-live-runner clickhouse-bar-replay \
  --strategy strategies/ema20_adx_production_10x.json \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --mode paper-trading \
  --report-jsonl ./paper_trading_report.jsonl
```

### Step 3: Go Live (When Ready)
```bash
bin/backtest-live-runner clickhouse-bar-replay \
  --strategy strategies/ema20_adx_production_10x.json \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --mode live-trading \
  --report-jsonl ./live_trading_report.jsonl
```

## Monitoring Checklist

### Daily Checks
- [ ] No liquidations or margin calls
- [ ] Positions being opened/closed correctly
- [ ] Unrealized P&L tracking as expected
- [ ] No API errors or connectivity issues

### Weekly Review
- [ ] Actual vs expected position count
- [ ] Win rate holding at ~49%
- [ ] Drawdown under 40%
- [ ] No strategy bugs or data issues

### Monthly Analysis
- [ ] Compare actual returns vs backtest
- [ ] Check for regime changes in market
- [ ] Review any losing months for patterns
- [ ] Document any adjustments needed

## Exit Strategy (When to Stop Trading)

**STOP IMMEDIATELY if:**
1. Max drawdown exceeds 40% (account down >40%)
2. Series of 5+ consecutive losing trades
3. Margin/liquidation warnings appear
4. Strategy performance diverges >20% from backtest
5. Exchange API/connectivity issues persist

## Backtest Comparison Data

### Monthly Breakdown (Expected)
```
Jun: +6.0%     Jul: -4.0%      Aug: +32.2%
Sep: -6.2%     Oct: +10.3%     Nov: +23.2%
Dec: +34.2%    Jan: +4.6%      Feb: +10.4%
Mar: +3.2%     Apr: +4.9%      May: -14.3%
Jun: +5.0%
```

### Position Statistics
- Total positions/year: ~75
- Winners: ~37 (49.3%)
- Losers: ~38 (50.7%)
- Avg winner: $80.35
- Avg loser: -$49.41
- Profit factor: 1.63x

## Questions to Ask Yourself

Before going live, honestly answer:

1. ✓ Can I afford to lose $340+ (34% drawdown)?
2. ✓ Can I handle watching -$300+ in a single bad day?
3. ✓ Will I stick with the strategy during losing months?
4. ✓ Do I have time to monitor daily?
5. ✓ Is this my risk tolerance, or am I being overconfident?

## Support & Documentation

- Backtest report: `data/backtest_reports/ema20_adx_opt_exit_1_5_lev_10x_btcusdt_*.jsonl`
- Strategy file: `strategies/ema20_adx_production_10x.json`
- Validation: `python3 scripts/validate_strategy.py`

## Timeline Recommendation

```
Week 1-2: Paper trading (risk-free)
   ↓
Week 3-4: Live trading with 1/3 capital
   ↓
Week 5-6: Increase to full capital if performing well
   ↓
Ongoing: Monitor & adjust as needed
```

---

**Last Updated:** June 24, 2026
**Strategy:** ema20_adx_production_10x.json
**Backtest Period:** Jun 2025 - Jun 2026
**Status:** Ready for deployment
