#!/bin/bash
# Start ClickHouse 24.3 in the cloud environment.
# ClickHouse does not auto-start; run this at the beginning of each session.
#
# Usage: bash scripts/start_clickhouse.sh

set -e

if clickhouse-client --query "SELECT 1" &>/dev/null 2>&1; then
    echo "ClickHouse is already running ($(clickhouse-client --query 'SELECT version()'))"
    exit 0
fi

echo "Starting ClickHouse 24.3..."
sudo -u clickhouse /usr/bin/clickhouse-server \
  --config-file /etc/clickhouse-server/config.xml \
  &>/tmp/clickhouse-server.log &

# Wait up to 15s for the server to accept connections
for i in $(seq 1 15); do
    if clickhouse-client --query "SELECT 1" &>/dev/null 2>&1; then
        echo "ClickHouse started ($(clickhouse-client --query 'SELECT version()'))"
        exit 0
    fi
    sleep 1
done

echo "ClickHouse failed to start. Check /tmp/clickhouse-server.log"
exit 1
