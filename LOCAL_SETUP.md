# Local Development Setup

This guide walks through setting up ClickHouse locally for strategy backtesting.

## Quick Start with Docker Compose

### Prerequisites
- Docker and Docker Compose installed
- 2+ GB disk space for ClickHouse data

### Setup

1. **Start ClickHouse**:
```bash
docker-compose up -d
```

Wait for it to be healthy (30 seconds):
```bash
docker-compose logs -f clickhouse
# Look for: "Ready to serve requests"
```

2. **Copy environment config**:
```bash
cp .env.example .env
```

The defaults in `.env.example` are already set for local Docker ClickHouse:
- `CLICKHOUSE_URL=http://127.0.0.1:8123`
- `CLICKHOUSE_USER=quant`
- `CLICKHOUSE_PASSWORD=quant`
- `CLICKHOUSE_DATABASE=market`

3. **Verify setup**:
```bash
python3 scripts/doctor.py
```

Should see:
```
OK   Python 3.11.15
OK   runner: ./bin/backtest-live-runner
OK   runner catalog exported 17 indicators
OK   23 strategy files parse
OK   ClickHouse smoke query succeeded
```

4. **Sync market data** (one symbol/window at a time):
```bash
python3 scripts/sync_data_api_klines.py \
  --exchange binance_um_futures \
  --symbol BTCUSDT \
  --start 2026-06-10T00:00:00Z \
  --end 2026-06-10T06:00:00Z
```

5. **Run a backtest**:
```bash
python3 scripts/run.py single \
  --strategy macd_atr_pullback_er_filter \
  --start 2026-06-10T00:00:00Z \
  --end 2026-06-10T06:00:00Z
```

## Troubleshooting

### ClickHouse won't start
```bash
# Check logs
docker-compose logs clickhouse

# Restart
docker-compose restart clickhouse

# Full reset (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

### Can't connect to ClickHouse
```bash
# Test connection
curl http://localhost:8123/ping

# Check environment variables
cat .env | grep CLICKHOUSE
```

### Data sync fails with TLS errors
If certificate validation fails:
```bash
# Either in .env:
DATA_API_SSL_VERIFY=false

# Or on the command line:
python3 scripts/sync_data_api_klines.py --insecure --exchange ... --symbol ...
```

### Out of disk space
```bash
# Check ClickHouse data volume
docker exec quant_clickhouse df -h

# Clean old reports (doesn't affect ClickHouse data)
rm -f data/backtest_reports/*.jsonl
```

## Alternative: System Package (macOS)

If using Homebrew:

```bash
brew install clickhouse

# Start server in background
clickhouse-server &

# Or run in foreground
clickhouse-server --console
```

Default connection: `http://localhost:8123`

## Alternative: System Package (Linux)

Download from [official repo](https://clickhouse.com/docs/en/install):

```bash
# Debian/Ubuntu
sudo apt-get install clickhouse-client clickhouse-server

# Start
sudo systemctl start clickhouse-server

# Check status
sudo systemctl status clickhouse-server
```

## Stopping ClickHouse

```bash
# Docker Compose
docker-compose down

# Homebrew (Ctrl+C if running in foreground)
brew services stop clickhouse

# Linux
sudo systemctl stop clickhouse-server
```

## Next Steps

Once ClickHouse is running and data is synced:

1. Run monthly diagnostics:
```bash
python3 scripts/run.py monthly --strategy macd_atr_pullback_er_filter
```

2. Run continuous realistic test:
```bash
python3 scripts/run_suite.py --mode continuous --strategy macd_atr_pullback_er_filter
```

3. Analyze results:
```bash
python3 scripts/analyze_trades.py
```

See `CLAUDE.md` for full workflow documentation.
