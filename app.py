# ============================================================
#  binance_signal.py — Bybit API দিয়ে অটো Crypto Signal
#  সম্পূর্ণ FREE — কোনো API key লাগবে না
# ============================================================

import requests
import time
from datetime import datetime
import pytz

BOT_SERVER = "https://trading-bot-production-09fe.up.railway.app"
BD_TZ      = pytz.timezone("Asia/Dhaka")

PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "DOTUSDT", "LTCUSDT", "AVAXUSDT",
]

INTERVAL    = "1"
EMA_PERIOD  = 20
CHECK_EVERY = 60
MIN_CANDLES = 25


def get_candles(symbol):
    url = "https://api.bybit.com/v5/market/kline"
    params = {"category": "spot", "symbol": symbol, "interval": INTERVAL, "limit": 50}
    try:
        resp    = requests.get(url, params=params, timeout=10)
        data    = resp.json()
        if data.get("retCode") != 0:
            print(f"  ⚠️ {symbol}: {data.get('retMsg')}")
            return [], [], []
        candles = list(reversed(data["result"]["list"]))
        if len(candles) < 5:
            return [], [], []
        closes = [float(c[4]) for c in candles]
        highs  = [float(c[2]) for c in candles]
        lows   = [float(c[3]) for c in candles]
        return closes, highs, lows
    except Exception as e:
        print(f"  ⚠️ {symbol}: {e}")
        return [], [], []


def calculate_ema(prices, period):
    if len(prices) < period:
        return []
    k, ema = 2 / (period + 1), [sum(prices[:period]) / period]
    for p in prices[period:]:
        ema.append(p * k + ema[-1] * (1 - k))
    return ema


def detect_signal(closes, highs, lows):
    ema = calculate_ema(closes, EMA_PERIOD)
    if len(ema) < 2:
        return None
    resistance = round(max(highs[-20:]), 6)
    support    = round(min(lows[-20:]),  6)
    if closes[-2] <= ema[-2] and closes[-1] > ema[-1]:
        return {"direction": "CALL", "entry": round(closes[-1], 6), "resistance": resistance, "support": support, "trend": "UP"}
    if closes[-2] >= ema[-2] and closes[-1] < ema[-1]:
        return {"direction": "PUT",  "entry": round(closes[-1], 6), "resistance": resistance, "support": support, "trend": "DOWN"}
    return None


def send_signal(pair, signal):
    try:
        requests.post(f"{BOT_SERVER}/signal", json={
            "pair": pair, "direction": signal["direction"],
            "entry": str(signal["entry"]), "timeframe": f"M{INTERVAL}",
            "resistance": str(signal["resistance"]), "support": str(signal["support"]),
            "trend": signal["trend"]
        }, timeout=10)
        t = datetime.now(BD_TZ).strftime("%H:%M:%S")
        print(f"  ✅ [{t}] {pair} {signal['direction']} @ {signal['entry']}")
    except Exception as e:
        print(f"  ❌ {pair}: {e}")


def main():
    print("=" * 55)
    print("🚀 Bybit Auto Signal Bot Started!")
    print(f"📊 Pairs: {', '.join(PAIRS)}")
    print(f"⏱ Interval: M{INTERVAL} | Check: {CHECK_EVERY}s")
    print(f"🌐 Server: {BOT_SERVER}")
    print("=" * 55)
    last = {p: None for p in PAIRS}
    while True:
        t = datetime.now(BD_TZ).strftime("%H:%M:%S")
        print(f"\n[{t}] Checking {len(PAIRS)} pairs...")
        for pair in PAIRS:
            closes, highs, lows = get_candles(pair)
            if len(closes) < MIN_CANDLES:
                continue
            signal = detect_signal(closes, highs, lows)
            if signal:
                if last[pair] != signal["direction"]:
                    send_signal(pair, signal)
                    last[pair] = signal["direction"]
            else:
                print(f"  ➖ {pair}: No signal")
            time.sleep(0.3)
        print(f"⏳ Next check in {CHECK_EVERY}s...")
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()
