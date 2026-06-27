# Quant Backtest Environment Setup & Testing Guide

## Quick Start

### 1. Start ClickHouse

**Option A — Docker (preferred):**

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

**Option B — Native install (when Docker is unavailable, e.g. cloud/CI environments):**

```bash
# Download and install packages
curl -fsSL 'https://packages.clickhouse.com/deb/pool/main/c/clickhouse/clickhouse-common-static_25.5.2.47_amd64.deb' -o /tmp/ch-common.deb
curl -fsSL 'https://packages.clickhouse.com/deb/pool/main/c/clickhouse/clickhouse-server_25.5.2.47_amd64.deb' -o /tmp/ch-server.deb
curl -fsSL 'https://packages.clickhouse.com/deb/pool/main/c/clickhouse/clickhouse-client_25.5.2.47_amd64.deb' -o /tmp/ch-client.deb
DEBIAN_FRONTEND=noninteractive dpkg -i /tmp/ch-common.deb /tmp/ch-server.deb /tmp/ch-client.deb

# Create the quant user
mkdir -p /etc/clickhouse-server/users.d
cat > /etc/clickhouse-server/users.d/quant.xml << 'EOF'
<clickhouse>
    <users>
        <quant>
            <password>quant</password>
            <networks><ip>::/0</ip></networks>
            <profile>default</profile>
            <quota>default</quota>
            <access_management>1</access_management>
        </quant>
    </users>
</clickhouse>
EOF

# Start and verify
clickhouse start
curl -s 'http://quant:quant@127.0.0.1:8123/?query=SELECT%201'
# Should return: 1

# Create the market database
curl -s -X POST 'http://quant:quant@127.0.0.1:8123/' --data 'CREATE DATABASE IF NOT EXISTS market'
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

Sync data from the data API into ClickHouse. **Always sync at least 1 year at a time** — the script skips days already present, so a wide window is safe and prevents repeated partial syncs.

```bash
# Sync all symbols with a 1-year window (recommended)
for symbol in BTCUSDT ETHUSDT SOLUSDT BCHUSDT; do
  python3 scripts/sync_data_api_klines.py \
    --data-api-url "$DATA_API_URL" \
    --exchange binance_um_futures \
    --symbol $symbol \
    --start 2025-06-01 \
    --end 2026-06-30 \
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

- **`ema_adaptive_regime_10x.json`** ⭐ RECOMMENDED (best overall)
  - Switch strategy: EMA50/EMA20 dual-regime crossovers + ADX trend filter
  - Entry: EMA50 cross (trending) OR EMA20 cross + EMA100 direction (choppy)
  - Exit: ATR trailing stops (1.5x high vol, 0.9x low vol) — adaptive by volatility
  - BTC: +30.82%, 16.26% DD, 25 positions (Jun 15 - Sep 2, 2025)
  - ETH: +32.75%, 38.79% DD, 127 positions (Jun 15 - Jun 6, 2026)

- **`ema_roc_adx_dual_switch_10x.json`** ⭐ BEST on BTCUSDT
  - Switch strategy: dual-regime with ROC direction instead of EMA100 filter
  - Entry: EMA50 cross + ADX≥30 (trending) OR EMA20 cross + ROC + ADX≥25 (momentum)
  - BTC: +35.03%, 18.21% DD, 28 positions (Jun 15 - Sep 2, 2025) — beats baseline
  - ETH: -4.28%, 70% DD (Jun 15 - Jun 6, 2026) — fails in bear market (ROC allows false longs)

### Testing & Research

- **`ema_adaptive_regime_5x_ethusdt.json`** - 5x leverage variant for ETH
- **`ema_adaptive_regime_3x_solusdt.json`** - 3x leverage variant for SOL
- **`ema_adaptive_regime_5x_bchusdt.json`** - 5x leverage variant for BCH
- **`ema_adaptive_regime_trend_filter_10x_bchusdt.json`** - Adds EMA200(1h) macro trend filter for BCH
- **`ema_adaptive_volatility_simple_10x.json`** - Volatility-adaptive exits (experimental)
- **`ema_adaptive_position_sizing_10x.json`** - Position sizing by volatility (experimental)

### Explored — Failed or Suboptimal (see Strategy Exploration Findings below)

---

## Data Availability

| Symbol | Date Range | Status |
|--------|-----------|--------|
| BTCUSDT | 2025-05-20 to 2025-09-03 | ✅ Available |
| ETHUSDT | 2025-06-15 to 2026-06-06 | ✅ Available |
| SOLUSDT | 2025-06-15 to 2026-06-06 | ✅ Available |
| BCHUSDT | 2025-06-15 to 2026-06-06 | ✅ Available |
| BTCUSDC | 2025-06-15 to 2025-09-02 | ✅ Available (poor performance) |

For **additional symbols**, sync using at least a 1-year window (safe to re-run; skips existing days):
```bash
python3 scripts/sync_data_api_klines.py \
  --data-api-url https://data.becole.com \
  --exchange binance_um_futures \
  --symbol <SYMBOL> \
  --start 2025-06-01 \
  --end 2026-06-30 \
  --interval 1m \
  --limit 10000
```

---

## Strategy Performance Summary

### BTCUSDT (Jun 15 - Sep 2, 2025 — all-bull period)
| Strategy | Return | DD | Positions | Win Rate | Notes |
|----------|--------|-----|-----------|---------|-------|
| **ema_roc_adx_dual_switch_10x** | **+35.03%** | 18.21% | 28 | 50% | ⭐ Best BTC |
| ema_adaptive_regime_10x (baseline) | +30.82% | 16.26% | 25 | 52% | benchmark |
| ema_baseline_wider_exits_10x | +30.22% | 19.38% | 26 | 42% | wider exits hurt DD |
| ema_baseline_roc_filter_10x | +27.06% | 16.26% | 21 | 52% | ROC reduces entries |
| ema_roc_adx_dual_ema100_10x | +11.11% | 14.24% | 15 | 53% | ADX≥30 too strict |
| ema_baseline_strict_filter_10x | +5.33% | 17.80% | 19 | 47% | EMA100 in trending blocks recovery |
| ema_adaptive_regime_compound_10x | +33.33% | 21.79% | 25 | 52% | compound amplifies both directions |
| bb_breakout_long_10x | +26.97% | 13.76% | 16 | 50% | BB upper cross+EMA100+ADX; ETH blow-up |
| macd_abovezero_roc_ema200_long_10x | +20.7% | 20.4% | 16 | 44% | best long-only |
| With EMA200 filter | +1% | 13% | 15 | - | EMA200 too restrictive |
| bb_ema100_dip_long_10x | +2.54% | 8.83% | 4 | 50% | BB lower+EMA100; too few entries |

### ETHUSDT (Jun 15, 2025 - Jun 6, 2026 — bull+bear full year)
| Strategy | Return | DD | Positions | Win Rate | Notes |
|----------|--------|-----|-----------|---------|-------|
| **ema_adaptive_regime_10x (baseline)** | **+32.75%** | 38.79% | 127 | 50% | ⭐ Best ETH |
| ema_adaptive_regime_5x | +16.4% | 23.0% | 127 | - | lower leverage |
| ema_adaptive_regime_compound_10x | -25.16% | 65.19% | 127 | 50% | bull gains → bigger bear losses |
| ema_roc_adx_dual_switch_10x | -4.28% | 70% | 120 | 48% | ROC allows false longs in bear |
| ema_baseline_strict_filter_10x | -67.67% | 78.66% | 95 | 45% | blocks early recovery longs |
| ema_baseline_roc_filter_10x | -86.84% | 90.24% | 81 | 38% | ROC wrong for ETH |
| ema_baseline_wider_exits_10x | -90.21% | 100.54% | 120 | 39% | blow-up: 0.9x exit is essential |

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

### ⚡ 0. FAST VALIDATION: 30-Day Test (RECOMMENDED FIRST STEP)

**Test on recent 30 days FIRST before long-term backtest.** This quickly validates if strategy works in current market conditions.

```bash
export CLICKHOUSE_USER=quant
export CLICKHOUSE_PASSWORD=quant

# Determine recent 30-day window (adjust dates based on today)
# Example: if today is 2026-06-26, test 2026-05-27 to 2026-06-26

START_DATE="2026-05-27T00:00:00Z"
END_DATE="2026-06-26T23:59:00Z"
SYMBOL="BTCUSDT"

# Run 30-day test (takes ~1 minute)
./bin/backtest-live-runner clickhouse-bar-replay \
  --strategy strategies/ema_adaptive_regime_10x.json \
  --exchange binance_um_futures \
  --symbol $SYMBOL \
  --start $START_DATE \
  --end $END_DATE \
  --chunk-size 1000 \
  --report-jsonl /tmp/validation_30day.jsonl

# View results immediately
echo "=== 30-DAY VALIDATION RESULTS ==="
tail -1 /tmp/validation_30day.jsonl | jq '.summary | {
  return_pct: (.return_pct | tonumber * 100 | round),
  max_drawdown_pct: (.max_drawdown_pct | tonumber * 100 | round),
  position_count,
  win_rate: (.win_rate | tonumber | round),
  total_pnl: .realized_pnl
}'

# ✅ Go-Live Decision:
# - If return > 0% and DD < 50%: Likely safe to deploy
# - If return < 0%: Strategy failing in current market, needs investigation
# - If positions < 3: Insufficient sample, extend test window or adjust
```

**Validation Checklist:**
- [ ] Positive return (ideally > 2% per 30 days)
- [ ] Drawdown < 50% of account
- [ ] At least 5+ positions (sample size)
- [ ] Win rate > 40%

**Example Recent Results:**
- ✅ BTCUSDT (Jun 15 - Sep 3, 2025): +30.82% return → Expected +2.5%/month
- ❌ BTCUSDT (May 27 - Jun 26, 2026): -7.82% return → Strategy failing in current market

---

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

### Why the Baseline Works
The `ema_adaptive_regime_10x` baseline has been extensively stress-tested against 20+ strategy variants. Its design is highly intentional:

1. **Dual-regime entries** (EMA50 trending + EMA20 choppy) generates many quality entries without over-filtering
2. **Asymmetric EMA100 filter**: choppy regime requires EMA100 direction (blocks bear-phase longs), trending regime does NOT (allows early recovery longs that are most profitable)
3. **0.9x ATR low-vol exit is critical** — widening this to 1.5x caused -90% ETH blow-up; the tight stop is the main drawdown protection in quiet markets
4. **`compound_profit: false`** — fixed $10k notional prevents bear-phase losses from compounding (compound_profit: true produced -25% on ETH vs +32.75%)
5. **ADX≥25 filter** — blocks entries in ranging/choppy markets without requiring directional filter

### Why Other Approaches Fail

**Adding EMA100 to trending regime** (`ema_baseline_strict_filter_10x`): In bull markets and recovering trends, price crosses EMA50 BEFORE recovering above EMA100. Adding EMA100 requirement blocks the most profitable early-recovery entries. BTC: +5.33% vs +30.82%.

**Using ROC in choppy regime** (`ema_roc_adx_dual_switch_10x`): ROC can be briefly positive during dead-cat bounces in bear markets → false longs that then fail. ETH: -4.28% vs +32.75%. (Note: this strategy is best for BTC bull markets: +35.03% vs +30.82%.)

**Wider exits**: The 0.9x ATR low-vol exit is protective, not restrictive. Changing to 1.5x caused ETH to blow up (-90.21%) because losses ran unchecked in quiet bear-market periods.

**Compound profit in bear markets**: `compound_profit: true` amplifies the sequence dependency — bull phase grows equity which means larger position sizes in the subsequent bear phase. ETH: -25.16% vs +32.75%.

**MACD cross signals**: Fire too frequently in crypto (38 positions vs 25 for EMA approach), even with directional filters, generating too many false entries.

**DI crossovers as primary signal**: Fire too rarely (2 positions on BTC over 2.5 months) — too few trades for meaningful returns.

### Return Display — Correct jq Formula
The raw `return_pct` in summary JSON is a decimal fraction (0.327 = 32.7%). Use this formula:
```bash
tail -1 result.jsonl | jq '.summary | {
  return_pct: (.return_pct | tonumber * 100 | (. * 100 | round) / 100),
  max_drawdown_pct: (.max_drawdown_pct | tonumber * 100 | (. * 100 | round) / 100),
  position_count,
  win_rate: (.win_rate | tonumber * 100 | round / 100)
}'
```
**Wrong** (off by 100x): `tonumber * 100 | round / 100` → shows "0.33" for 32.75%
**Correct**: `tonumber * 100 | (. * 100 | round) / 100` → shows "32.75"

### Parallel ETH Backtest Timeout
Running 4+ full-year ETH backtests simultaneously causes resource contention and timeouts at 600s. Run ETH full-year tests **sequentially** with `timeout 900`:
```bash
timeout 900 ./bin/backtest-live-runner clickhouse-bar-replay --strategy ... --symbol ETHUSDT --start 2025-06-15T00:00:00Z --end 2026-06-06T23:59:00Z ...
```

### When Strategy Works Well
✅ **Bull/Trending Markets** (BTC Jun-Sep 2025: +30.82%; ETH Jun-Jun: +32.75%)
✅ **EMA crossovers align with real trends** — ADX filter prevents false signals
✅ **Moderate volatility** — 0.9x ATR exit protects in low-vol, 1.5x gives room in high-vol

### When Strategy Fails
❌ **Sustained bear markets** (BCH Dec 2025 → Jun 2026: -108%)
❌ **High volatility altcoins** (SOL at 10x: -78.6%)
❌ **Choppy/sideways markets** (false breakouts, frequent EMA20 crosses)

### How to Improve
🔧 **Use `ema_roc_adx_dual_switch_10x` for BTC**: +35% vs +30.82% baseline (+4.2%)
🔧 **Reduce leverage** for high-volatility symbols (SOL 3x instead of 10x)
🔧 **Add macro trend filter** (EMA200 on 1h) for BCH-type assets in persistent bear markets

---

## Strategy Exploration Findings

Extensive exploration (20+ strategies tested) of novel indicator combinations. No strategy beat the baseline on both BTC and ETH simultaneously.

### Explored Signal Combinations
| Strategy File | Key Idea | BTC | ETH | Verdict |
|--------------|---------|-----|-----|---------|
| ema_roc_adx_dual_switch_10x | ROC replace EMA100 in choppy | **+35%** | -4.3% | Best BTC only |
| ema_baseline_strict_filter_10x | EMA100 in trending regime too | +5.3% | -67.7% | Too restrictive |
| ema_baseline_wider_exits_10x | 2.0x/1.5x ATR exits | +30.2% | -90.2% | ETH blow-up |
| ema_baseline_roc_filter_10x | ROC in both regimes | +27.1% | -86.8% | ROC wrong for ETH |
| ema_dual_adx30_ema100_10x | ADX≥30 trending + EMA100 choppy | +11.1% | - | ADX≥30 too strict |
| chop_ema50_roc_switch_10x | CHOP trending state + EMA50 + ROC | -2% (3 pos) | - | Too few entries |
| ema50_di_ema100_switch_10x | DI direction + EMA50 cross | -53% | -82% | - |
| di_cross_ema100_adx_switch_10x | DI crossover as primary entry | -2.4% (2 pos) | - | Too few entries |
| macd_di_ema100_switch_10x | MACD cross + DI direction | -48.4% (38 pos) | - | Too frequent |
| macd_golden_ema100_adx_switch_10x | MACD cross + EMA100 + ADX | -32% all-short | - | ADX directional bias |
| roc_cross_adx_switch_10x | ROC zero cross + EMA100 + ADX | -21% all-long | - | No short signal |
| macd_abovezero_ema200_di_switch_10x | MACD above-zero cross + DI | -90% all-short | -100% | above_zero cross too rare |
| bb_rsi_long_only_10x | BB lower cross edge + RSI oversold (≤30) + EMA100 | 0% (0 pos) | +4.83% (1 pos) | RSI≤30 never fires in BTC bull |
| bb_ema100_dip_long_10x | BB lower cross + EMA100 (no RSI) | +2.54% (4 pos) | -63.3% (40 pos) | Too few BTC entries; mean reversion fails bear ETH |
| bb_breakout_long_10x | BB upper breakout + EMA100 + ADX | +26.97% (16 pos) | -96.2% (84 pos) | Bear-market rallies give false upper breakouts |

### Key Signal Learnings
- **MACD `above_zero_golden_cross`**: Never fires in sustained uptrends (MACD stays above signal)
- **MACD `golden_cross`**: Fires too frequently (38 trades per 2.5 months on BTC)
- **ADX `trend_strong` (ADX≥25)**: Direction-neutral — biases toward shorts in bull markets when used alone
- **DI crossovers** (`plus_di_cross_above`): Too rare — 2 trades on BTC in 2.5 months
- **ROC `positive/negative` state**: Good directional filter in trending markets; fails in bear market dead-cat bounces
- **CHOP `trending` state**: Too rarely true in crypto — only 3 entries on BTC in 2.5 months
- **`compound_profit: true`**: Amplifies sequence dependency — avoid in multi-regime markets
- **BB lower band (2 stddev) at 1h**: Only breached 4 times on BTC in 2.5 months — too rare for a standalone strategy
- **RSI oversold (≤30) at 1h**: Essentially never fires in bull markets (BTC Jun-Sep 2025 = 0 events) — useless as a primary filter
- **BB upper breakout at 1h**: Good BTC bull signal (+27%) but ETH bear-market rallies create false entries → account blow-up (-96%); needs a stronger macro bear filter than EMA100
- **BB mean reversion (long only)**: ETH generates 40 entries but -63% return — downtrend continuation beats mean reversion; EMA100 filter is insufficient for bear market
- **BB strategies at 1h**: Structurally inferior to EMA crossovers for this dataset — EMA signals align with medium-term directional trends while BB extremes measure short-term deviation that can persist indefinitely in trending markets

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
