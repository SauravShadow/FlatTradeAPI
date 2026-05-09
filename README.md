# FlatTrade API — Ready To Use 🚀

A self-contained, production-ready Python toolkit for the **Flattrade brokerage API**.
Built and tested on Ubuntu Server. Works anywhere Python 3.10+ is installed.

---

## 📁 Project Structure

```
FlatTrade_API-ReadyToUse/
├── main.py                   ← Master entry point (start here)
├── config.py                 ← Your API credentials (edit this first)
├── api_helper.py             ← Flattrade API wrapper (do not edit)
├── requirements.txt          ← All Python dependencies
├── data_manager.py           ← Download & manage stock OHLCV data
├── trader.py                 ← Buy, sell, orders, positions
├── token_generator/
│   └── login.py              ← Headless browser login with screenshots
├── screenshots/              ← Auto-created: login debug screenshots
├── data/                     ← Auto-created: stock CSV files
├── dist/
│   └── norenrestapi-*.whl    ← Flattrade API library (bundled)
└── .session_token            ← Auto-created: cached daily token
```

---

## ⚡ Quick Setup (New Machine)

### Step 1 — Clone / Copy the project
```bash
cp -r FlatTrade_API-ReadyToUse /your/new/path/
cd /your/new/path/FlatTrade_API-ReadyToUse
```

### Step 2 — Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
python3 -m playwright install chromium
```

> ⚠️ **Linux only** — also install Playwright system libraries:
> ```bash
> sudo apt-get install -y libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
>   libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
>   libxrandr2 libgbm1 libasound2t64
> ```

### Step 4 — Edit your credentials
Open `config.py` and fill in:
```python
API_KEY    = "your_api_key"
API_SECRET = "your_api_secret"
USER_ID    = "your_client_id"   # e.g. FZ42614
```

Get these from: **Flattrade Dashboard → API → Your App**

### Step 5 — Whitelist your server IP
1. Go to **Flattrade Dashboard → API → Edit App**
2. Set **Primary IP** to your server's public IP
3. To find your server IP: `curl -s https://api.ipify.org`

### Step 6 — Run!
```bash
source venv/bin/activate
python3 main.py
```

---

## 🔐 Daily Login Flow

The login is **fully automated** using a headless Chromium browser.

```
python3 main.py

→ Checks for saved token (.session_token)
→ If valid: skips login, goes straight to menu ✅
→ If expired: runs headless login automatically

Login steps (automated):
  1. Opens Flattrade auth page in hidden browser
  2. Fills your User ID + Password
  3. Clicks "Get OTP"
  4. Fills popup User ID + PAN/DOB
  5. Clicks OK (OTP sent to your mobile)
  
You enter: the 6-digit OTP from your phone

  6. Script fills OTP + clicks Log In
  7. Token is captured and saved to .session_token
```

### Login Debug Screenshots
Every step saves a screenshot to `screenshots/`:
```
screenshots/
  20260509_103000_01_login_page.png
  20260509_103002_02_credentials_filled.png
  20260509_103005_03_after_get_otp_click.png
  20260509_103007_04_popup_filled.png
  20260509_103010_05_after_popup_ok.png
  20260509_103015_06_otp_filled.png
  20260509_103017_07_final_state.png
```
If login fails, open these images to see exactly what went wrong.

---

## 📊 Stock Data Manager

Access via **Main Menu → 1**

### Option 1: Search Stock
Find the symbol and token for any stock:
```
Stock name: INFY
→ INFY-EQ    Token: 1594    INFOSYS LIMITED
→ INFY-BL    Token: 9876    ...
```

### Option 2: Live Quote
Get real-time price (market hours only: 9:15 AM – 3:30 PM IST):
```
Exchange: NSE
Token: 1594
→ LTP: ₹1455.30 | High: ₹1462 | Low: ₹1448 | Change: +0.85%
```

### Option 3: Historical Data (terminal display)
```
Exchange: NSE | Token: 1594 | Days: 7
→ Shows last 7 days of 1-min OHLCV in terminal
```

### Option 4: Bulk Download (saves CSV files)
```
Stocks: INFY, RELIANCE, TCS, HDFCBANK, WIPRO
Exchange: NSE | Days: 365

→ Auto-searches, picks EQ variant, downloads 1 year of 1-min data
→ Saves to: data/INFY-EQ.csv, data/RELIANCE-EQ.csv, ...
→ Subsequent runs only fetch NEW data (incremental updates)
```

**CSV format:**
```
datetime,open,high,low,close,volume,vwap
2025-05-12 09:15:00,1445.0,1462.0,1443.5,1455.3,234512,1453.1
```

### Option 5: Resample to Different Interval
Convert stored 1-min data to any candle size:
```
Symbol: INFY-EQ | Interval: 5 | Days: 30
→ Creates data/INFY-EQ_5min.csv with proper OHLCV aggregation

Supported: 2min, 3min, 5min, 10min, 15min, 30min, 60min (any number)
```

---

## 💹 Trading Panel

Access via **Main Menu → 2**

> ⚠️ **Real money is at risk. Test with small quantities first.**

### Buy Order
```
Symbol: INFY-EQ
Exchange: NSE
Quantity: 1
Price type: MKT       ← Market order (instant execution)
Product: I            ← Intraday (auto square-off at 3:20 PM)
```

### Sell Order
```
Symbol: INFY-EQ
Exchange: NSE
Quantity: 1
Price type: LMT       ← Limit order
Limit price: 1460     ← Sell at ₹1460 or better
Product: C            ← Delivery (keeps in your demat)
```

### Price Types
| Type    | Description |
|---------|-------------|
| `MKT`   | Market — instant execution at best available price |
| `LMT`   | Limit — only execute at your price or better |
| `SL-LMT`| Stop-Loss Limit — trigger at stop price, execute at limit |

### Product Types
| Type | Description |
|------|-------------|
| `C`  | CNC — Delivery / Long-term holding |
| `I`  | MIS — Intraday, auto square-off |
| `M`  | NRML — Margin (F&O) |

### Order Book
Shows all orders placed today with status (OPEN, COMPLETE, CANCELLED).

### Positions
Shows open intraday positions with real-time P&L.

### Holdings
Shows your long-term demat holdings.

### Cancel Order
```
Order ID: 26052609123456   ← From the order book
```

---

## 🔑 Key Notes

### Token Validity
- The session token is **valid for one trading day**
- `main.py` caches it in `.session_token`
- Next day, it will re-login automatically (one OTP required)

### INVALID_IP Error
If you see `INVALID_IP`:
1. Check your current IP: `curl -s https://api.ipify.org`
2. Ensure that IP is set as **Primary IP** in Flattrade Dashboard → API
3. The project forces IPv4 connections automatically (to avoid IPv6 issues)

### Market Hours
- **Equity**: 9:15 AM – 3:30 PM IST (Mon–Fri, excluding holidays)
- Live quotes only work during market hours
- Historical data and downloads work 24/7

### Rate Limiting
- Space out bulk downloads (the 0.3s delay between chunks is intentional)
- If OTP is not received, wait 5–10 minutes before trying again

---

## 🤖 ML / Data Science Usage

The saved CSVs are ready for direct use with pandas, scikit-learn, etc.:

```python
import pandas as pd

# Load 1-min data
df = pd.read_csv('data/INFY-EQ.csv', parse_dates=['datetime'])
df.set_index('datetime', inplace=True)

# Or load resampled data
df_5min = pd.read_csv('data/INFY-EQ_5min.csv', parse_dates=['datetime'])

# Features for ML
df['returns']  = df['close'].pct_change()
df['range']    = df['high'] - df['low']
df['body']     = abs(df['close'] - df['open'])
df['vol_ma20'] = df['volume'].rolling(20).mean()
```

Available columns: `datetime`, `open`, `high`, `low`, `close`, `volume`, `vwap`

---

## 🛠 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: playwright` | Run `pip install playwright && python3 -m playwright install chromium` |
| `libnspr4.so not found` | Run the apt-get command in Step 3 above |
| `INVALID_IP` error | Whitelist your server IP in Flattrade dashboard |
| OTP not received | Wait 5-10 min (rate limit), try again |
| Token expired mid-day | Use option 4 (Re-login) in main menu |
| Wrong symbol | Use Search (option 1 in Data Manager) to find exact symbol |
