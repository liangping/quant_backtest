#!/bin/bash
# Automated smoke test: BTC 7-day window
# Usage: bash scripts/smoke_test.sh

set -e

echo "🧪 Quant Backtest Smoke Test - 7 Days BTC"
echo "=========================================="

# Configuration
EXCHANGE="binance_um_futures"
SYMBOL="BTCUSDT"
START="2026-06-03T00:00:00Z"
END="2026-06-10T00:00:00Z"
STRATEGY="macd_atr_pullback_er_filter"
INTERVAL="15m"

# Check prerequisites
echo ""
echo "📋 Checking prerequisites..."
python3 --version || { echo "❌ Python 3 not found"; exit 1; }

# Check ClickHouse connectivity
echo ""
echo "🗄️  Checking ClickHouse connection..."
python3 -c "
import urllib.request
try:
    resp = urllib.request.urlopen('http://localhost:8123/ping', timeout=2)
    if resp.status == 200:
        print('✅ ClickHouse is running')
    exit(0)
except Exception as e:
    print(f'❌ ClickHouse not reachable: {e}')
    print('   Start it with: docker-compose up -d')
    exit(1)
" || exit 1

# Sync market data
echo ""
echo "📊 Syncing 7 days of $SYMBOL data ($START to $END)..."
python3 scripts/sync_data_api_klines.py \
  --exchange "$EXCHANGE" \
  --symbol "$SYMBOL" \
  --start "$START" \
  --end "$END" \
  || { echo "❌ Data sync failed"; exit 1; }
echo "✅ Data synced"

# Run backtest
echo ""
echo "⚙️  Running backtest ($STRATEGY, $INTERVAL, 7 days)..."
python3 scripts/run.py single \
  --strategy "$STRATEGY" \
  --exchange "$EXCHANGE" \
  --symbol "$SYMBOL" \
  --interval "$INTERVAL" \
  --start "$START" \
  --end "$END" \
  || { echo "❌ Backtest failed"; exit 1; }

echo ""
echo "✅ Smoke test complete!"
echo ""
echo "📈 Review the results:"
echo "   - Check output above for PnL, return %, and max drawdown"
echo "   - View detailed report: tail -1 data/backtest_reports/*.jsonl | python3 -m json.tool"
echo ""
echo "🔄 Try variations:"
echo "   - Different interval: --interval 5m"
echo "   - Different strategy: --strategy bb_rsi_mean_reversion"
echo "   - Different period: --start 2026-05-01T00:00:00Z --end 2026-06-01T00:00:00Z"
echo ""
