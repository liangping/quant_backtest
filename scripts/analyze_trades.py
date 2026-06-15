#!/usr/bin/env python3
"""Analyze trades for a specific month."""

import json, subprocess, pandas as pd, sys
from pathlib import Path
from datetime import datetime, timedelta

WORK = Path(__file__).resolve().parent.parent
STRATEGY = WORK / 'strategies' / 'ema7_50_trend.json'
RUST_BINARY = Path.home() / 'Documents/New project/rust/target/release/backtest-direct-runner'
PARQUET_CACHE = Path.home() / 'Documents/New project/data/local-market-cache/binance_um_futures'


def load_data(symbol, interval, start, end):
    cache = PARQUET_CACHE / symbol / interval
    start_ts = pd.Timestamp(start, tz='UTC')
    end_ts = pd.Timestamp(end, tz='UTC')

    dfs = []
    for pq in sorted(cache.glob('*.parquet')):
        df = pd.read_parquet(pq)
        if 'open_time' not in df.columns:
            continue
        df['open_time'] = pd.to_datetime(df['open_time'], utc=True)
        df = df[(df['open_time'] >= start_ts) & (df['open_time'] < end_ts)]
        if not df.empty:
            dfs.append(df)

    if not dfs:
        return []

    all_data = pd.concat(dfs).sort_values('open_time')
    rows = []
    for _, row in all_data.iterrows():
        rows.append({
            'exchange': 'binance_um_futures', 'symbol': symbol, 'interval': interval,
            'open_time': pd.Timestamp(row['open_time']).strftime('%Y-%m-%dT%H:%M:%S+00:00'),
            'close_time': pd.Timestamp(row['close_time']).strftime('%Y-%m-%dT%H:%M:%S+00:00'),
            'open': str(row.get('open', 0)), 'high': str(row.get('high', 0)),
            'low': str(row.get('low', 0)), 'close': str(row.get('close', 0)),
            'volume': str(row.get('volume', 0)), 'quote_volume': str(row.get('quote_volume', 0)),
            'trade_count': int(row['trade_count']) if not pd.isna(row.get('trade_count')) else None,
            'source_row_count': int(row['n_trades']) if not pd.isna(row.get('n_trades')) else None,
        })
    return rows


def analyze_month(month_str, config):
    start = f"{month_str}-01"
    end_dt = datetime.strptime(month_str, '%Y-%m').replace(day=28) + timedelta(days=4)
    end = end_dt.replace(day=1).strftime('%Y-%m-%d')

    rows = load_data('BTCUSDT', '1h', start, end)
    if not rows:
        print(f"No data for {month_str}")
        return

    payload = {
        'strategy': config,
        'rows_by_interval': {'1h': rows},
        'start': f'{start}T00:00:00+00:00',
        'end': f'{end}T00:00:00+00:00',
        'fee_rate': '0.0004',
    }

    r = subprocess.run([str(RUST_BINARY)], input=json.dumps(payload), capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Error: {r.stderr[:200]}")
        return

    result = json.loads(r.stdout)

    print(f"\n{'='*100}")
    print(f"{month_str} Analysis")
    print(f"{'='*100}")

    summary = result.get('summary', {})
    print(f"Bars: {summary.get('processed_bars', 0)}, Fills: {summary.get('fill_count', 0)}")
    print(f"PnL: ${float(summary.get('total_pnl', 0)):.2f}")
    print(f"Equity: ${float(summary.get('final_equity', 0)):.2f}")

    # Analyze fills
    fills = result.get('fills', [])
    print(f"\nTotal fills: {len(fills)}")

    # Group fills by position cycles
    positions = []
    current_position = None

    for fill in fills:
        action = fill.get('action', '')
        side = fill.get('side', '')
        fill_time = fill.get('fill_time', '')[:16]
        price = float(fill.get('price', 0))
        quantity = float(fill.get('quantity', 0))
        pnl = float(fill.get('pnl', 0))
        pnl_pct = float(fill.get('pnl_pct', 0))

        if action == 'open' and current_position is None:
            current_position = {
                'entry_time': fill_time,
                'entry_price': price,
                'side': side,
                'fills': [fill]
            }
        elif current_position is not None:
            current_position['fills'].append(fill)
            if action in ['close', 'stop_loss']:
                current_position['exit_time'] = fill_time
                current_position['exit_price'] = price
                current_position['total_pnl'] = pnl
                current_position['total_pnl_pct'] = pnl_pct
                positions.append(current_position)
                current_position = None

    if current_position is not None:
        positions.append(current_position)

    print(f"\nPosition Cycles: {len(positions)}")

    wins = [p for p in positions if p.get('total_pnl', 0) > 0]
    losses = [p for p in positions if p.get('total_pnl', 0) <= 0]

    print(f"Wins: {len(wins)}, Losses: {len(losses)}")

    total_pnl = sum(p.get('total_pnl', 0) for p in positions)
    avg_win = sum(p.get('total_pnl', 0) for p in wins) / len(wins) if wins else 0
    avg_loss = sum(p.get('total_pnl', 0) for p in losses) / len(losses) if losses else 0

    print(f"Total PnL from positions: ${total_pnl:.2f}")
    print(f"Avg Win: ${avg_win:.2f}, Avg Loss: ${avg_loss:.2f}")

    print(f"\nDetailed Positions:")
    for i, pos in enumerate(positions, 1):
        entry_time = pos.get('entry_time', '?')[5:]
        exit_time = pos.get('exit_time', '?')[5:]
        side = pos.get('side', '?')
        entry_price = pos.get('entry_price', 0)
        exit_price = pos.get('exit_price', 0)
        pnl = pos.get('total_pnl', 0)
        pnl_pct = pos.get('total_pnl_pct', 0)

        # Determine exit reason
        exit_fill = pos['fills'][-1]
        exit_action = exit_fill.get('action', '?')
        trigger_signal = exit_fill.get('trigger_signal_id', '?')

        print(f"  {i:2d}. {side:5s} | Entry: {entry_price:>10.2f} @ {entry_time} | "
              f"Exit: {exit_price:>10.2f} @ {exit_time} | "
              f"PnL: {pnl:+>10.2f} ({pnl_pct:+.2f}%) | "
              f"Exit: {exit_action}/{trigger_signal}")


if __name__ == '__main__':
    config = json.loads(STRATEGY.read_text())

    months_to_analyze = ['2026-01', '2026-04', '2026-05']
    for month in months_to_analyze:
        analyze_month(month, config)
