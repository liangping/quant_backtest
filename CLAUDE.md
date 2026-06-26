# Quant Backtest Environment Setup & Testing Guide

## Quick Start

### 1. Start ClickHouse Docker Container

```bash
docker run -d \
  --name clickhouse-service \
  -p 8123:8123 \
  -p 9000:9000 \
  -p 9009:9009 \
  -e CLICKHOUSE_USER=quant \
  -e CLICKHOUSE_PASSWORD=quant \
  -v clickhouse_data:/var/lib/clickhouse \
  clickhouse/clickhouse-server:latest
```

Verify it's running:
```bash
docker ps | grep clickhouse
curl -s 'http://quant:quant@127.0.0.1:8123/?query=SELECT%201'
# Should return: 1
```

### 2. Environment Variables

Set these in your shell or `.env` file:

```bash
# ClickHouse Database
export CLICKHOUSE_URL=http://127.0.0.1:8123
export CLICKHOUSE_DATABASE=market
export CLICKHOUSE_USER=quant
export CLICKHOUSE_PASSWORD=quant

# Data API for syncing historical data
export DATA_API_URL=https://data.becole.com

# Backtest Configuration
export BACKTEST_EXCHANGE=binance_um_futures
export BACKTEST_SYMBOL=BTCUSDT
```

### 3. Sync Historical Data

Sync data from the data API into ClickHouse:

```bash
# Sync BTCUSDT (example: Jun 15 - Sep 3, 2025)
python3 scripts/sync_data_api_klines.py \
  --data-api-url "$DATA_API_URL" \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --start 2025-06-15 \
  --end 2025-09-03 \
  --interval 1m \
  --limit 10000

# For full year testing (requires multiple syncs)
for symbol in ETHUSDT SOLUSDT BCHUSDT; do
  python3 scripts/sync_data_api_klines.py \
    --data-api-url "$DATA_API_URL" \
    --exchange binance_um_futures \
    --symbol $symbol \
    --start 2025-06-15 \
    --end 2026-06-06 \
    --interval 1m \
    --limit 10000
done
```

### 4. Run Backtests

Single symbol test (2-3 minutes):
```bash
export CLICKHOUSE_USER=quant
export CLICKHOUSE_PASSWORD=quant

./bin/backtest-live-runner clickhouse-bar-replay \
  --strategy strategies/ema_adaptive_regime_10x.json \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --start 2025-06-15T00:00:00Z \
  --end 2025-09-03T23:59:00Z \
  --chunk-size 1000 \
  --report-jsonl /tmp/backtest_result.jsonl
```

View results:
```bash
tail -1 /tmp/backtest_result.jsonl | jq '.summary'
```

---

## Strategies Available

### Production Ready

- **`ema_adaptive_regime_10x.json`** ⭐ RECOMMENDED for BTCUSDT
  - Entry: EMA50/EMA20 crossovers + ADX trend confirmation
  - Exit: ATR-based trailing stops (1.5x high vol, 0.9x low vol)
  - Performance: +30.82% on BTCUSDT (Jun-Sep 2025)
  - Best for: Bull/trending markets

### Testing & Research

- **`ema_adaptive_regime_5x_ethusdt.json`** - 5x leverage variant for ETH
- **`ema_adaptive_regime_3x_solusdt.json`** - 3x leverage variant for SOL
- **`ema_adaptive_regime_5x_bchusdt.json`** - 5x leverage variant for BCH
- **`ema_adaptive_regime_trend_filter_10x_bchusdt.json`** - Adds EMA200(1h) macro trend filter for BCH
- **`ema_adaptive_volatility_simple_10x.json`** - Volatility-adaptive exits (experimental)
- **`ema_adaptive_position_sizing_10x.json`** - Position sizing by volatility (experimental)

---

## Data Availability

| Symbol | Date Range | Status |
|--------|-----------|--------|
| BTCUSDT | 2025-05-20 to 2025-09-03 | ✅ Available |
| ETHUSDT | 2025-06-15 to 2026-06-06 | ✅ Available |
| SOLUSDT | 2025-06-15 to 2026-06-06 | ✅ Available |
| BCHUSDT | 2025-06-15 to 2026-06-06 | ✅ Available |
| BTCUSDC | 2025-06-15 to 2025-09-02 | ✅ Available (poor performance) |

For **longer historical data** or **different symbols**, sync using:
```bash
python3 scripts/sync_data_api_klines.py \
  --data-api-url https://data.becole.com \
  --exchange binance_um_futures \
  --symbol <SYMBOL> \
  --start <START_DATE> \
  --end <END_DATE> \
  --interval 1m \
  --limit 10000
```

---

## Strategy Performance Summary

### BTCUSDT (Best Performer)
| Strategy | Period | Return | DD | Positions |
|----------|--------|--------|----|----|
| ema_adaptive_regime_10x (baseline) | Jun 15 - Sep 3, 2025 | +30.82% | 16.26% | 25 |
| With EMA200 filter | (6-15 - Sep 3, 2025 | +1% | 13% | 15 |

### ETHUSDT (Good Performer)
| Strategy | Period | Return | DD | Positions |
|----------|--------|--------|----|----|
| ema_adaptive_regime_10x (baseline) | Jun 15 - Jun 6, 2026 | +32.7% | 38.8% | 127 |
| ema_adaptive_regime_5x | Jun 15 - Jun 6, 2026 | +16.4% | 23.0% | 127 |

### SOLUSDT (Poor Fit - High Volatility)
| Strategy | Period | Return | DD | Positions |
|----------|--------|--------|----|----|
| ema_adaptive_regime_10x (baseline) | Jun 15 - Jun 6, 2026 | -78.6% | 91.0% | 104 |
| ema_adaptive_regime_3x | Jun 15 - Jun 6, 2026 | -21.4% | 33.0% | 104 |

### BCHUSDT (Needs Macro Filter)
| Strategy | Period | Return | DD | Positions |
|----------|--------|--------|----|----|
| ema_adaptive_regime_10x (baseline) | Jun 15 - Jun 6, 2026 | -108.4% | 106.0% | 132 |
| With EMA200(1h) filter | Jun 15 - Jun 6, 2026 | +4.7% | 64% | 85 |

---

## Troubleshooting

### ClickHouse Connection Error
```
Error: query ClickHouse returned error... HTTP status client error (401 Unauthorized)
```
**Solution:** Ensure environment variables are set:
```bash
export CLICKHOUSE_USER=quant
export CLICKHOUSE_PASSWORD=quant
```

### Warmup Data Insufficient
```
Error: ClickHouse warmup data is incomplete... loaded 0 of 300 bars
```
**Solution:** You need at least 300 bars (for 1h candles) or 300 days (for 1d candles) before your test start date. Either:
- Sync earlier historical data
- Start your backtest later (e.g., 2025-07-01 instead of 2025-06-15)

### Docker Container Won't Start
```bash
# Check logs
docker logs clickhouse-service

# Restart
docker restart clickhouse-service
docker ps  # Verify it's running
```

### "Too Many Open Files" Error
```
ClickHouse filesystem error: Too many open files
```
**Solution:** Restart ClickHouse container:
```bash
docker stop clickhouse-service
docker start clickhouse-service
sleep 10
```

---

## Testing Workflow

### 1. Quick Test (Single Symbol, Short Period)
```bash
./bin/backtest-live-runner clickhouse-bar-replay \
  --strategy strategies/ema_adaptive_regime_10x.json \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --start 2025-07-01T00:00:00Z \
  --end 2025-08-01T00:00:00Z \
  --chunk-size 1000 \
  --report-jsonl /tmp/test.jsonl

# Results in 1-2 minutes
tail -1 /tmp/test.jsonl | jq '.summary | {return_pct, max_drawdown_pct, position_count, win_rate}'
```

### 2. Full Backtest (Full Year, All Symbols)
```bash
for SYMBOL in BTCUSDT ETHUSDT SOLUSDT BCHUSDT; do
  timeout 300 ./bin/backtest-live-runner clickhouse-bar-replay \
    --strategy strategies/ema_adaptive_regime_10x.json \
    --exchange binance_um_futures \
    --symbol $SYMBOL \
    --start 2025-06-15T00:00:00Z \
    --end 2026-06-06T00:00:00Z \
    --chunk-size 1000 \
    --report-jsonl /tmp/${SYMBOL}_backtest.jsonl &
done
wait

# View results
for SYMBOL in BTCUSDT ETHUSDT SOLUSDT BCHUSDT; do
  echo "=== $SYMBOL ===" 
  tail -1 /tmp/${SYMBOL}_backtest.jsonl | jq '.summary | {return_pct, max_drawdown_pct, position_count}'
done
```

### 3. Compare Strategies
```bash
# Test multiple strategies on same symbol/period
for STRATEGY in ema_adaptive_regime_10x ema_adaptive_regime_trend_filter_10x_bchusdt; do
  ./bin/backtest-live-runner clickhouse-bar-replay \
    --strategy strategies/${STRATEGY}.json \
    --exchange binance_um_futures \
    --symbol BCHUSDT \
    --start 2025-06-15T00:00:00Z \
    --end 2026-06-06T00:00:00Z \
    --report-jsonl /tmp/${STRATEGY}.jsonl &
done
wait

# Compare
echo "Baseline:" && tail -1 /tmp/ema_adaptive_regime_10x.jsonl | jq '.summary.return_pct'
echo "With Filter:" && tail -1 /tmp/ema_adaptive_regime_trend_filter_10x_bchusdt.jsonl | jq '.summary.return_pct'
```

---

## Key Insights

### When Strategy Works Well
✅ **Bull/Trending Markets** (BTC Jun-Sep 2025: +30.82%)
✅ **EMA crossovers line up with real trends** (ETHUSDT: +32.7%)
✅ **Moderate volatility** (ADX trend detection reliable)

### When Strategy Fails
❌ **Sustained bear markets** (BCH Dec 2025 → Jun 2026: -108%)
❌ **High volatility altcoins** (SOL at 10x: -78.6%)
❌ **Choppy/sideways markets** (false breakouts hurt entry quality)

### How to Improve
🔧 **Add macro trend filter** (EMA200 on 1h or daily EMA50)
🔧 **Reduce leverage** for high-volatility symbols (SOL 3x instead of 10x)
🔧 **Adjust for market regime** (don't trade bear markets, or use tighter stops)

---

## Files Structure

```
quant_backtest/
├── CLAUDE.md                    # This file
├── strategies/
│   ├── ema_adaptive_regime_10x.json          # ⭐ Baseline
│   ├── ema_adaptive_regime_*x_*.json         # Leverage variants
│   ├── ema_adaptive_regime_trend_filter_*.json
│   └── ema_adaptive_volatility_*.json        # Experimental variants
├── scripts/
│   ├── sync_data_api_klines.py               # Data sync script
│   └── (other analysis scripts)
├── bin/
│   └── backtest-live-runner                  # Backtest engine binary
├── data/
│   └── backtest_reports/                     # Historical test results
├── ROOT_CAUSE_ANALYSIS.md                    # Why strategy fails on SOL/BCH
├── VOLATILITY_ADAPTIVE_DESIGN.md             # Design doc for volatility tiers
└── MULTI_SYMBOL_RESULTS.md                   # Performance comparison table
```

---

## Next Steps for Agent

1. **Verify environment**: `export CLICKHOUSE_USER=quant && curl -s 'http://quant:quant@127.0.0.1:8123/?query=SELECT%201'`
2. **Check data availability**: Query ClickHouse for symbol/date range needed
3. **Sync data if needed**: Use `sync_data_api_klines.py` with appropriate dates
4. **Run backtest**: Use `clickhouse-bar-replay` command with strategy JSON
5. **Analyze results**: Parse JSON output with `jq` or Python

---

## Support

- **ClickHouse issues**: Check docker logs with `docker logs clickhouse-service`
- **Backtest crashes**: Ensure adequate warmup data (300+ bars before test start)
- **Data gaps**: Sync using `sync_data_api_klines.py` with broader date range
- **Strategy questions**: See ROOT_CAUSE_ANALYSIS.md and VOLATILITY_ADAPTIVE_DESIGN.md
