#!/bin/bash
# Quick start script for local ClickHouse + backtest setup
# Run this after cloning: bash scripts/quickstart.sh

set -e

echo "🚀 Quant Backtest Local Setup"
echo "=============================="

# Check prerequisites
echo ""
echo "📋 Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found. Install from https://www.docker.com/products/docker-desktop"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose not found"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 not found"; exit 1; }

python_version=$(python3 --version | cut -d' ' -f2)
echo "✅ Docker installed"
echo "✅ Python $python_version installed"

# Start ClickHouse
echo ""
echo "🗄️  Starting ClickHouse..."
docker-compose up -d
echo "⏳ Waiting for ClickHouse to be healthy..."
sleep 10

if docker-compose ps | grep -q "healthy"; then
    echo "✅ ClickHouse is running and healthy"
else
    echo "⚠️  ClickHouse starting (may take up to 30 seconds)"
    docker-compose logs clickhouse | tail -5
fi

# Setup .env
echo ""
echo "⚙️  Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env from .env.example"
else
    echo "✅ .env already exists"
fi

# Run doctor
echo ""
echo "🏥 Running environment check..."
if python3 scripts/doctor.py; then
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "📚 Next steps:"
    echo "  1. Sync market data:"
    echo "     python3 scripts/sync_data_api_klines.py --exchange binance_um_futures --symbol BTCUSDT --start 2026-06-10 --end 2026-06-11"
    echo ""
    echo "  2. Run a backtest:"
    echo "     python3 scripts/run.py single --strategy macd_atr_pullback_er_filter --start 2026-06-10 --end 2026-06-10T06:00:00Z"
    echo ""
    echo "  3. Run monthly diagnostics:"
    echo "     python3 scripts/run.py monthly --strategy macd_atr_pullback_er_filter"
    echo ""
else
    echo "❌ Environment check failed"
    echo ""
    echo "Troubleshooting:"
    echo "  - Ensure ClickHouse is running: docker-compose logs clickhouse"
    echo "  - Restart if needed: docker-compose restart clickhouse"
    echo "  - See LOCAL_SETUP.md for more help"
fi
