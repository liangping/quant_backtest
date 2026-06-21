# Smoke Test: BTC 7-Day Window

Quick validation that backtesting infrastructure works end-to-end.

## Prerequisites
- ClickHouse running locally (see [LOCAL_SETUP.md](LOCAL_SETUP.md))
- Linux binary in `bin/backtest-live-runner`
- Python 3.10+ with scripts available

## Run on Your Local Machine

### Step 1: Start ClickHouse (if not already running)
```bash
docker-compose up -d
```

Wait for health check to pass:
```bash
docker-compose logs clickhouse | grep "Ready to serve"
```

### Step 2: Sync 7 days of BTCUSDT data
This fetches 1m OHLC bars from 2026-06-03 to 2026-06-10:

```bash
python3 scripts/sync_data_api_klines.py \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --start 2026-06-03T00:00:00Z \
  --end 2026-06-10T00:00:00Z
```

Expected output:
```
Syncing binance_um_futures BTCUSDT from 2026-06-03 to 2026-06-10
Checking local ClickHouse coverage...
Fetching missing days from data API...
[Day 1/7] 2026-06-03: inserted 1440 bars
[Day 2/7] 2026-06-04: inserted 1440 bars
...
[Day 7/7] 2026-06-10: inserted 1440 bars
Sync complete: 10080 bars (7 days)
```

### Step 3: Run single 7-day continuous backtest
```bash
python3 scripts/run.py single \
  --strategy macd_atr_pullback_er_filter \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --interval 15m \
  --start 2026-06-03T00:00:00Z \
  --end 2026-06-10T00:00:00Z
```

Expected output:
```
Strategy: macd_atr_pullback_er_filter  binance_um_futures:BTCUSDT  2026-06-03 -> 2026-06-10  chart=15m
  2026-06-03 bars=10080 fills=8 positions=4 PnL=+125.3456 equity=1125.3456 ret=+12.53% dd=-3.21%
  report: data/backtest_reports/macd_atr_pullback_er_filter_btcusdt_2026_06_03_2026_06_10.jsonl
```

### Step 4: Examine the report
```bash
# View last line (summary)
tail -1 data/backtest_reports/macd_atr_pullback_er_filter_btcusdt_2026_06_03_2026_06_10.jsonl | python3 -m json.tool

# View all trades
cat data/backtest_reports/macd_atr_pullback_er_filter_btcusdt_2026_06_03_2026_06_10.jsonl | python3 -m json.tool
```

### Step 5 (Optional): Run monthly split to see regime differences
```bash
# This resets state each month boundary (diagnostic, not realistic)
python3 scripts/run.py monthly \
  --strategy macd_atr_pullback_er_filter \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --interval 15m
```

Expected output:
```
Strategy: macd_atr_pullback_er_filter  binance_um_futures:BTCUSDT  monthly
  2025-12    bars= 7200 fills=4 positions=2 PnL=+87.1234  equity=1087.1234 ret=+8.71% dd=-2.15%
  2026-01    bars= 7440 fills=5 positions=3 PnL=+98.5678  equity=1186.1789 ret=+9.85% dd=-3.40%
  ...
  2026-06    bars= 2880 fills=2 positions=1 PnL=+45.2345  equity=1231.4134 ret=+4.52% dd=-1.80%
  TOTAL      PnL=+400.1234
```

## Interpreting Results

### Key Metrics
- **bars**: 1-minute candles processed (≈ 1440/day)
- **fills**: Trade executions (entries + exits)
- **positions**: Distinct open/close cycles
- **PnL**: Total profit/loss in quote currency (USDT)
- **equity**: Starting capital + PnL
- **ret%**: (PnL / initial_capital) * 100
- **dd%**: Maximum intra-period drawdown

### Expected Ranges for Baseline Strategy
- **fills**: 5-15 (BTC volatility dependent)
- **positions**: 2-8 (entries are 200% notional, position_pct)
- **PnL**: -100 to +300 USDT (highly market dependent)
- **ret%**: -10% to +30% (7 days is short)
- **dd%**: -2% to -8% (sharp reversals)

## Troubleshooting

### "ClickHouse/runner smoke failed"
ClickHouse not running:
```bash
docker-compose ps
docker-compose logs clickhouse
docker-compose restart clickhouse
```

### "No bars in result"
Market data not synced or mismatched dates:
```bash
# Re-sync with wider window
python3 scripts/sync_data_api_klines.py \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --start 2026-06-01T00:00:00Z \
  --end 2026-06-11T00:00:00Z
```

### "Query failed"
Check ClickHouse logs:
```bash
docker exec quant_clickhouse clickhouse-client \
  -u quant --password quant \
  -q "SELECT COUNT(*) FROM market.klines_1m WHERE symbol='BTCUSDT'"
```

Should return a row count > 10000.

### Network/certificate errors during sync
Use insecure mode:
```bash
python3 scripts/sync_data_api_klines.py \
  --insecure \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --start 2026-06-03T00:00:00Z \
  --end 2026-06-10T00:00:00Z
```

## Next Steps

1. **Edit the strategy**: Modify `strategies/macd_atr_pullback_er_filter.json`
2. **Validate changes**: `python3 scripts/validate_strategy.py strategies/macd_atr_pullback_er_filter.json`
3. **Re-run backtest**: Run Step 3 above with the same date range
4. **Compare results**: Check `data/backtest_reports/` directory

See [CLAUDE.md](CLAUDE.md) and [AI_STRATEGY_GUIDE.md](docs/AI_STRATEGY_GUIDE.md) for strategy design best practices.
