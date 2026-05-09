"""
data_manager.py — Stock Data Downloader & Manager
==================================================
Fetches, stores and resamples historical stock OHLCV data from Flattrade.

5 Capabilities:
  1. Search stock by name → get symbol and token
  2. Get live quote (LTP, OHLC, volume, change%)
  3. Get historical data and show in terminal
  4. Bulk search + download multiple stocks at once (saves CSVs)
  5. Resample stored 1-min data to any interval (2min, 5min, 15min...)

Data is stored in:  data/<SYMBOL>.csv
Resampled data in:  data/<SYMBOL>_<N>min.csv
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta
from api_helper import NorenApiPy
from config import DATA_DIR


def _init_api(userid, usersession):
    api = NorenApiPy()
    api.set_session(userid=userid, password='', usertoken=usersession)
    return api


# ══════════════════════════════════════════════════════════════
# 1. SEARCH STOCK
# ══════════════════════════════════════════════════════════════
def search_stock(api, query, exchange='NSE'):
    """Search for a stock by name. Returns list of matching symbols."""
    ret = api.searchscrip(exchange=exchange, searchtext=query)
    if ret and 'values' in ret:
        print(f"\n  Results for '{query}':")
        print(f"  {'#':<4} {'Symbol':<25} {'Token':<10} Description")
        print(f"  {'-'*65}")
        for i, s in enumerate(ret['values'][:10]):
            print(f"  [{i}]  {s['tsym']:<25} {s['token']:<10} {s.get('cname','')}")
        return ret['values']
    print(f"  ❌ No results for '{query}'")
    return []


# ══════════════════════════════════════════════════════════════
# 2. LIVE QUOTE
# ══════════════════════════════════════════════════════════════
def get_live_quote(api, exchange, token):
    """Fetch and display the live quote for a stock."""
    ret = api.get_quotes(exchange=exchange, token=token)
    if ret and ret.get('stat') == 'Ok':
        chg = float(ret.get('pc', 0))
        arrow = '▲' if chg >= 0 else '▼'
        print(f"\n  ╔══════════════════════════════╗")
        print(f"  ║  📈 {ret.get('tsym','N/A'):<24} ║")
        print(f"  ╠══════════════════════════════╣")
        print(f"  ║  LTP    : ₹{ret.get('lp','N/A'):<19}║")
        print(f"  ║  Open   : ₹{ret.get('o','N/A'):<19}║")
        print(f"  ║  High   : ₹{ret.get('h','N/A'):<19}║")
        print(f"  ║  Low    : ₹{ret.get('l','N/A'):<19}║")
        print(f"  ║  Close  : ₹{ret.get('c','N/A'):<19}║")
        print(f"  ║  Volume : {ret.get('v','N/A'):<20}║")
        print(f"  ║  Change : {arrow} {chg:+.2f}%{'':<15}║")
        print(f"  ╚══════════════════════════════╝\n")
    else:
        print(f"  ❌ Could not fetch quote: {ret}")


# ══════════════════════════════════════════════════════════════
# 3. HISTORICAL DATA (display in terminal)
# ══════════════════════════════════════════════════════════════
def get_historical_data(api, exchange, token, days=30):
    """Fetch and display historical OHLCV data for the last N days."""
    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=days)
    ret = api.get_time_price_series(
        exchange=exchange, token=token,
        starttime=int(start_dt.timestamp()), endtime=int(end_dt.timestamp()))
    if ret:
        df = pd.DataFrame(ret)
        cols = {c: {'into':'open','inth':'high','intl':'low','intc':'close',
                     'intv':'volume','time':'datetime'}.get(c, c) for c in df.columns}
        df.rename(columns=cols, inplace=True)
        for col in ['open','high','low','close','volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'], format='%d-%m-%Y %H:%M:%S', errors='coerce')
        df.sort_values('datetime', inplace=True)
        print(f"\n  📊 Historical Data — last {days} days ({len(df)} records)")
        print(f"  {df[['datetime','open','high','low','close','volume']].to_string(index=False)}\n")
        return df
    print("  ❌ No historical data returned")
    return None


# ══════════════════════════════════════════════════════════════
# 4. BULK DOWNLOAD (saves CSV per stock)
# ══════════════════════════════════════════════════════════════
def _fetch_chunk(api, exchange, token, start_dt, end_dt):
    try:
        ret = api.get_time_price_series(
            exchange=exchange, token=token,
            starttime=int(start_dt.timestamp()), endtime=int(end_dt.timestamp()))
        if not ret:
            return None
        df = pd.DataFrame(ret)
        rename = {'time':'datetime','into':'open','inth':'high','intl':'low',
                  'intc':'close','intv':'volume','intvwap':'vwap'}
        df.rename(columns={k:v for k,v in rename.items() if k in df.columns}, inplace=True)
        for col in ['open','high','low','close','volume','vwap']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'], format='%d-%m-%Y %H:%M:%S', errors='coerce')
        df.dropna(subset=['datetime'], inplace=True)
        df.sort_values('datetime', inplace=True)
        return df
    except Exception as e:
        print(f"    ⚠ Chunk error: {e}")
        return None


def download_stock(api, symbol, exchange, token, days=365, chunk_days=50):
    """Download historical data for a stock, saving/updating its CSV."""
    os.makedirs(DATA_DIR, exist_ok=True)
    csv_path   = os.path.join(DATA_DIR, f"{symbol.replace('/','_')}.csv")
    end_dt     = datetime.now().replace(hour=23, minute=59, second=59)
    all_frames = []

    if os.path.exists(csv_path):
        existing  = pd.read_csv(csv_path, parse_dates=['datetime'])
        last_date = existing['datetime'].max()
        start_dt  = last_date + timedelta(minutes=1)
        print(f"  📂 Existing data found up to {last_date.date()}. Fetching new data only...")
        all_frames.append(existing)
    else:
        start_dt = end_dt - timedelta(days=days)
        print(f"  🆕 No existing data. Fetching {days} days from {start_dt.date()}...")

    if start_dt >= end_dt:
        print(f"  ✅ {symbol} already up to date!")
        return

    chunk_start, total_new = start_dt, 0
    while chunk_start < end_dt:
        chunk_end = min(chunk_start + timedelta(days=chunk_days), end_dt)
        print(f"    → {chunk_start.date()} to {chunk_end.date()}...", end=' ', flush=True)
        df_chunk = _fetch_chunk(api, exchange, token, chunk_start, chunk_end)
        if df_chunk is not None and not df_chunk.empty:
            total_new += len(df_chunk)
            all_frames.append(df_chunk)
            print(f"{len(df_chunk)} records")
        else:
            print("no data")
        chunk_start = chunk_end + timedelta(minutes=1)
        time.sleep(0.3)

    if not all_frames:
        print(f"  ❌ No data returned for {symbol}")
        return

    combined = pd.concat(all_frames, ignore_index=True)
    combined.drop_duplicates(subset=['datetime'], keep='last', inplace=True)
    combined.sort_values('datetime', inplace=True)
    combined.to_csv(csv_path, index=False)
    print(f"\n  ✅ {symbol}: {len(combined)} total records | +{total_new} new | → {csv_path}")
    print(f"     Range: {combined['datetime'].min().date()} → {combined['datetime'].max().date()}\n")


def bulk_search_and_download(api, stock_names, exchange='NSE', days=365):
    """Search multiple stocks by name and download their data automatically."""
    found, missing = [], []
    print(f"\n  🔍 Searching {len(stock_names)} stock(s)...\n")
    for name in stock_names:
        name = name.strip().upper()
        ret  = api.searchscrip(exchange=exchange, searchtext=name)
        time.sleep(0.2)
        if ret and 'values' in ret:
            values = ret['values']
            chosen = next((s for s in values if s['tsym'].upper() == f"{name}-EQ"), None)
            if not chosen:
                chosen = next((s for s in values if '-EQ' in s['tsym'].upper()), None)
            if not chosen:
                chosen = values[0]
            print(f"  ✅ {name:<15} → {chosen['tsym']:<20} Token: {chosen['token']}")
            found.append((chosen['tsym'], exchange, chosen['token']))
        else:
            print(f"  ❌ {name:<15} → Not found")
            missing.append(name)
        time.sleep(0.2)

    if missing:
        print(f"\n  ⚠ Not found: {', '.join(missing)}")
    if not found:
        print("\n  No stocks to download.")
        return

    print(f"\n  📥 Downloading {days} days for {len(found)} stock(s)...\n")
    for symbol, exch, token in found:
        print(f"  📊 {symbol} ({exch})")
        download_stock(api, symbol, exch, token, days=days)


# ══════════════════════════════════════════════════════════════
# 5. RESAMPLE
# ══════════════════════════════════════════════════════════════
def resample_to_interval(symbol, interval_minutes=2, days=30):
    """
    Resample stored 1-min CSV to any interval and save a new CSV.
    Uses proper OHLCV aggregation: Open=first, High=max, Low=min, Close=last, Volume=sum
    """
    csv_path = os.path.join(DATA_DIR, f"{symbol.replace('/','_')}.csv")
    if not os.path.exists(csv_path):
        print(f"  ❌ No data for {symbol}. Download it first.")
        return None

    df = pd.read_csv(csv_path, parse_dates=['datetime'])
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)
    cutoff = df.index.max() - timedelta(days=days)
    df     = df[df.index >= cutoff]

    agg_dict = {'open':'first','high':'max','low':'min','close':'last','volume':'sum'}
    if 'vwap' in df.columns:
        agg_dict['vwap'] = 'mean'

    resampled = df.resample(f"{interval_minutes}min", label='left', closed='left') \
                  .agg(agg_dict).dropna(subset=['open','close'])
    resampled.reset_index(inplace=True)

    out_path = os.path.join(DATA_DIR, f"{symbol.replace('/','_')}_{interval_minutes}min.csv")
    resampled.to_csv(out_path, index=False)

    print(f"\n  ✅ {symbol} → {interval_minutes}-min candles")
    print(f"     Records : {len(resampled)}")
    print(f"     Range   : {resampled['datetime'].min().date()} → {resampled['datetime'].max().date()}")
    print(f"     Saved   → {out_path}\n")
    return resampled


# ══════════════════════════════════════════════════════════════
# DATA SUMMARY
# ══════════════════════════════════════════════════════════════
def show_data_summary():
    """Print a summary table of all saved stock CSVs."""
    if not os.path.exists(DATA_DIR):
        print("\n  No data directory found. Download data first.\n")
        return
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    if not files:
        print("\n  No saved data yet.\n")
        return
    print(f"\n  {'Symbol':<25} {'Records':<10} {'From':<12} {'To':<12} {'Size'}")
    print(f"  {'-'*70}")
    for f in sorted(files):
        path = os.path.join(DATA_DIR, f)
        df   = pd.read_csv(path, parse_dates=['datetime'])
        size = os.path.getsize(path) / 1024
        print(f"  {f.replace('.csv',''):<25} {len(df):<10} "
              f"{str(df['datetime'].min().date()):<12} "
              f"{str(df['datetime'].max().date()):<12} {size:.1f}KB")
    print()


# ══════════════════════════════════════════════════════════════
# INTERACTIVE MENU (standalone)
# ══════════════════════════════════════════════════════════════
def run_data_menu(api):
    while True:
        print("  ┌─────────────────────────────────────────────┐")
        print("  │           Stock Data Manager                │")
        print("  ├─────────────────────────────────────────────┤")
        print("  │  1. Search stock by name                    │")
        print("  │  2. Live quote (LTP, OHLC, volume)          │")
        print("  │  3. Historical data (display in terminal)   │")
        print("  │  4. Bulk search + download multiple stocks  │")
        print("  │  5. Resample to different interval          │")
        print("  │  6. Show saved data summary                 │")
        print("  │  b. Back to main menu                       │")
        print("  └─────────────────────────────────────────────┘")
        choice = input("\n  Choice: ").strip().lower()

        if choice == '1':
            q  = input("  Stock name: ").strip()
            ex = input("  Exchange [NSE/BSE] (default NSE): ").strip() or 'NSE'
            search_stock(api, q, ex)

        elif choice == '2':
            ex    = input("  Exchange [NSE/BSE] (default NSE): ").strip() or 'NSE'
            token = input("  Token (from search): ").strip()
            get_live_quote(api, ex, token)

        elif choice == '3':
            ex    = input("  Exchange [NSE/BSE] (default NSE): ").strip() or 'NSE'
            token = input("  Token (from search): ").strip()
            days  = input("  Days of history (default 30): ").strip()
            get_historical_data(api, ex, token, int(days) if days.isdigit() else 30)

        elif choice == '4':
            print("  Enter stock names separated by commas:")
            print("  Example: INFY, RELIANCE, TCS, HDFCBANK\n")
            raw   = input("  Stocks: ").strip()
            names = [n.strip() for n in raw.split(',') if n.strip()]
            ex    = input("  Exchange [NSE/BSE] (default NSE): ").strip() or 'NSE'
            days  = input("  Days of history (default 365): ").strip()
            bulk_search_and_download(api, names, ex, int(days) if days.isdigit() else 365)

        elif choice == '5':
            show_data_summary()
            sym   = input("  Symbol (e.g. INFY-EQ): ").strip()
            mins  = input("  Interval in minutes (2/5/10/15/30): ").strip()
            days  = input("  How many days to resample (default 30): ").strip()
            resample_to_interval(sym, int(mins) if mins.isdigit() else 2,
                                  int(days) if days.isdigit() else 30)

        elif choice == '6':
            show_data_summary()

        elif choice == 'b':
            break
        else:
            print("  Invalid choice.\n")
