# PostgreSQL in Cloud Environment

PostgreSQL 16 is pre-installed and available in this cloud execution environment.

## Status

**Current**: PostgreSQL 16.13 is running and accepting connections on `localhost:5432`

Check status:
```bash
pg_isready -h localhost
```

Should output:
```
localhost:5432 - accepting connections
```

## Connection Details

**Default superuser account**:
- Host: `localhost`
- Port: `5432`
- User: `postgres`
- Database: `postgres`
- Password: (no password, socket authentication)

Connect:
```bash
sudo -u postgres psql
```

## Create Application Database

For quant strategy metadata or analysis results:

```bash
sudo -u postgres psql -c "CREATE DATABASE quant_data OWNER postgres;"
sudo -u postgres psql -c "CREATE USER quant WITH PASSWORD 'quant_secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE quant_data TO quant;"
```

Then connect as user `quant`:
```bash
psql -h localhost -U quant -d quant_data
```

## Use Cases

PostgreSQL can be used for:

1. **Strategy metadata** — Store strategy definitions, parameters, edit history
2. **Backtest results** — Archive and query historical backtest reports
3. **Trade journal** — Log strategy performance, notes, configuration changes
4. **Risk analysis** — Aggregate drawdown, Sharpe ratio, win rates across runs
5. **Data versioning** — Track which market data versions were used per backtest

## Example: Strategy Metadata Table

```sql
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    json_config TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active'
);

CREATE TABLE backtest_runs (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id),
    exchange VARCHAR(50),
    symbol VARCHAR(20),
    start_date DATE,
    end_date DATE,
    initial_capital DECIMAL(15, 2),
    final_equity DECIMAL(15, 2),
    total_pnl DECIMAL(15, 2),
    return_pct DECIMAL(10, 2),
    max_drawdown_pct DECIMAL(10, 2),
    fills INTEGER,
    positions INTEGER,
    run_id VARCHAR(255) UNIQUE,
    report_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Integration with Python Scripts

Example Python connection:

```python
import psycopg2
from pathlib import Path
import json

def save_backtest_to_postgres(strategy_name, exchange, symbol, start_date, end_date, report_dict):
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="quant_data",
        user="quant",
        password="quant_secure_password"
    )
    cur = conn.cursor()
    
    summary = report_dict.get('summary', {})
    
    cur.execute("""
        INSERT INTO backtest_runs 
        (strategy_id, exchange, symbol, start_date, end_date, initial_capital, 
         final_equity, total_pnl, return_pct, max_drawdown_pct, fills, positions, run_id, report_path)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        1,  # strategy_id (lookup from strategies table)
        exchange,
        symbol,
        start_date,
        end_date,
        1000.0,  # initial_capital
        summary.get('final_equity', 0),
        summary.get('total_pnl', 0),
        summary.get('return_pct', 0),
        summary.get('max_drawdown_pct', 0),
        summary.get('fill_count', 0),
        summary.get('position_count', 0),
        report_dict.get('run_id', 'unknown'),
        report_dict.get('_report_path', '')
    ))
    
    conn.commit()
    cur.close()
    conn.close()
```

## Starting PostgreSQL (if stopped)

```bash
sudo -u postgres /usr/lib/postgresql/16/bin/postgres \
  -D /var/lib/postgresql/16/main \
  -c config_file=/etc/postgresql/16/main/postgresql.conf &> /tmp/pg.log &
```

## Stopping PostgreSQL

```bash
sudo -u postgres /usr/lib/postgresql/16/bin/pg_ctl stop \
  -D /var/lib/postgresql/16/main -m fast
```

Or kill the process:
```bash
pkill -f "postgres -D"
```

## Differences from Local Setup

| Feature | Cloud | Local |
|---------|-------|-------|
| **PostgreSQL** | Available (16.13) | Install via Homebrew/apt |
| **ClickHouse** | Blocked (network restrictions) | Via docker-compose |
| **Connection** | `localhost:5432` | `localhost:5432` |
| **Best for** | Metadata, analysis, archival | Metadata, analysis, archival |

## Notes

- PostgreSQL persists data across session restarts (stored in `/var/lib/postgresql/`)
- Socket-based authentication works without passwords for `postgres` user
- Data is ephemeral when the cloud container terminates
- Export important data before session ends: `pg_dump quant_data > backup.sql`
