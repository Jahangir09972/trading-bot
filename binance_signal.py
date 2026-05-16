# ============================================================
#  binance_signal.py — Binance API দিয়ে অটো Crypto Signal
#  সম্পূর্ণ FREE — কোনো API key লাগবে না (public data)
#  Run: python binance_signal.py
# ============================================================

import requests
import time
from datetime import datetime
import pytz

# ── Config ───────────────────────────────────────────────────
BOT_SERVER = "https://trading-bot-production-09fe.up.railway.app"   # Railway deploy হলে সেই URL দিন
# BOT_SERVER = "https://trading-bot-production-09fe.up.railway.app"

BD_TZ = pytz.timezone("Asia/Dhaka")

# ── Crypto Pairs যেগুলো monitor করবে ─────────────────────────
PAIRS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "MATICUSDT",
    "DOTUSDT",
    "LTCUSDT",
]

# ── Settings ─────────────────────────────────────────────────
INTERVAL      = "1m"     # 1m, 3m, 5m, 15m, 1h
EMA_PERIOD    = 20       # EMA length
CHECK_EVERY   = 60       # কতো সেকেন্ড পরপর check করবে (60 = 1 মিনিট)
MIN_CANDLES   = 30       # কমপক্ষে কতো candle দরকার


# ── Binance Public API ────────────────────────────────────────
def get_candles(symbol: str, interval: str = "1m", limit: int = 50):
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        closes = [float(c[4]) for c in data]   # close price
        highs  = [float(c[2]) for c in data]   # high
        lows   = [float(c[3]) for c in data]   # low
        return closes, highs, lows
    except Exception as e:
        print(f"[Binance Error] {symbol}: {e}")
        return [], [], []


# ── EMA Calculation ───────────────────────────────────────────
def calculate_ema(prices: list, period: int) -> list:
    if len(prices) < period:
        return []
    ema = []
    k = 2 / (period + 1)
    ema.append(sum(prices[:period]) / period)
    for price in prices[period:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema


# ── Support & Resistance ──────────────────────────────────────
def get_support_resistance(highs: list, lows: list, period: int = 20):
    if len(highs) < period:
        return None, None
    resistance = max(highs[-period:])
    support    = min(lows[-period:])
    return round(resistance, 6), round(support, 6)


# ── Signal Detection ──────────────────────────────────────────
def detect_signal(closes: list, highs: list, lows: list):
    ema = calculate_ema(closes, EMA_PERIOD)
    if len(ema) < 2:
        return None

    resistance, support = get_support_resistance(highs, lows)

    current_close = closes[-1]
    prev_close    = closes[-2]
    current_ema   = ema[-1]
    prev_ema      = ema[-2]

    # CALL signal — price EMA cross করে উপরে গেল
    if prev_close <= prev_ema and current_close > current_ema:
        if current_close > support:
            return {
                "direction":  "CALL",
                "entry":      round(current_close, 6),
                "resistance": resistance,
                "support":    support,
                "trend":      "UP"
            }

    # PUT signal — price EMA cross করে নিচে গেল
    if prev_close >= prev_ema and current_close < current_ema:
        if current_close < resistance:
            return {
                "direction":  "PUT",
                "entry":      round(current_close, 6),
                "resistance": resistance,
                "support":    support,
                "trend":      "DOWN"
            }

    return None


# ── Send Signal to Bot ────────────────────────────────────────
def send_signal(pair: str, signal: dict):
    payload = {
        "pair":       pair,
        "direction":  signal["direction"],
        "entry":      str(signal["entry"]),
        "timeframe":  INTERVAL.upper(),
        "resistance": str(signal["resistance"]),
        "support":    str(signal["support"]),
        "trend":      signal["trend"]
    }
    try:
        resp = requests.post(
            f"{BOT_SERVER}/signal",
            json=payload,
            timeout=10
        )
        result = resp.json()
        time_now = datetime.now(BD_TZ).strftime("%H:%M:%S")
        print(f"[{time_now}] ✅ Signal sent: {pair} {signal['direction']} @ {signal['entry']}")
        return result
    except Exception as e:
        print(f"[Send Error] {pair}: {e}")
        return None


# ── Main Loop ─────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("🚀 Binance Auto Signal Bot Started!")
    print(f"📊 Monitoring: {', '.join(PAIRS)}")
    print(f"⏱ Interval: {INTERVAL} | Check every: {CHECK_EVERY}s")
    print(f"🌐 Bot Server: {BOT_SERVER}")
    print("=" * 50)

    # Last signal tracker (একই pair-এ বারবার signal না দিতে)
    last_signal = {pair: None for pair in PAIRS}

    while True:
        time_now = datetime.now(BD_TZ).strftime("%H:%M:%S")
        print(f"\n[{time_now}] Checking {len(PAIRS)} pairs...")

        for pair in PAIRS:
            closes, highs, lows = get_candles(pair, INTERVAL, limit=50)

            if len(closes) < MIN_CANDLES:
                print(f"  ⚠️ {pair}: Not enough data")
                continue

            signal = detect_signal(closes, highs, lows)

            if signal:
                # একই direction-এ বারবার signal না দেওয়া
                if last_signal[pair] != signal["direction"]:
                    send_signal(pair, signal)
                    last_signal[pair] = signal["direction"]
                else:
                    print(f"  ⏭ {pair}: Same signal skipped ({signal['direction']})")
            else:
                print(f"  ➖ {pair}: No signal")

            time.sleep(0.5)   # API rate limit এড়াতে

        print(f"\n⏳ Next check in {CHECK_EVERY} seconds...")
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()
