# ============================================================
#  binance_signal.py — Bybit API + Auto WIN/LOSS + ON/OFF
# ============================================================

import requests
import time
import threading
from datetime import datetime
import pytz

BOT_SERVER = "https://trading-bot-production-09fe.up.railway.app"
BD_TZ      = pytz.timezone("Asia/Dhaka")

PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "DOTUSDT", "LTCUSDT", "AVAXUSDT",
]

INTERVAL      = "1"
EMA_PERIOD    = 20
CHECK_EVERY   = 60
MIN_CANDLES   = 25
RESULT_DELAY  = 60   # Signal-এর কতো সেকেন্ড পরে result check করবে

# Global ON/OFF switch
signal_active = True


# ── Bybit API ─────────────────────────────────────────────────
def get_candles(symbol):
    url    = "https://api.bybit.com/v5/market/kline"
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


def get_current_price(symbol):
    url    = "https://api.bybit.com/v5/market/tickers"
    params = {"category": "spot", "symbol": symbol}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("retCode") == 0:
            return float(data["result"]["list"][0]["lastPrice"])
    except:
        pass
    return None


# ── EMA ───────────────────────────────────────────────────────
def calculate_ema(prices, period):
    if len(prices) < period:
        return []
    k, ema = 2 / (period + 1), [sum(prices[:period]) / period]
    for p in prices[period:]:
        ema.append(p * k + ema[-1] * (1 - k))
    return ema


# ── Signal Detection ──────────────────────────────────────────
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


# ── Send Signal ───────────────────────────────────────────────
def send_signal(pair, signal):
    try:
        requests.post(f"{BOT_SERVER}/signal", json={
            "pair":       pair,
            "direction":  signal["direction"],
            "entry":      str(signal["entry"]),
            "timeframe":  f"M{INTERVAL}",
            "resistance": str(signal["resistance"]),
            "support":    str(signal["support"]),
            "trend":      signal["trend"]
        }, timeout=10)
        t = datetime.now(BD_TZ).strftime("%H:%M:%S")
        print(f"  ✅ [{t}] {pair} {signal['direction']} @ {signal['entry']}")

        # Result check — RESULT_DELAY সেকেন্ড পরে
        thread = threading.Thread(
            target=check_result,
            args=(pair, signal["direction"], signal["entry"]),
            daemon=True
        )
        thread.start()

    except Exception as e:
        print(f"  ❌ {pair}: {e}")


# ── Auto Result Check ─────────────────────────────────────────
def check_result(pair, direction, entry_price):
    time.sleep(RESULT_DELAY)
    current = get_current_price(pair)
    if not current:
        print(f"  ⚠️ Result check failed: {pair}")
        return

    if direction == "CALL":
        outcome = "WIN" if current > entry_price else "LOSS"
    else:
        outcome = "WIN" if current < entry_price else "LOSS"

    t = datetime.now(BD_TZ).strftime("%H:%M:%S")
    print(f"  {'🏆' if outcome=='WIN' else '❌'} [{t}] {pair} {outcome} (Entry:{entry_price} → Now:{current})")

    try:
        requests.post(f"{BOT_SERVER}/result", json={
            "pair":    pair,
            "outcome": outcome
        }, timeout=10)
    except Exception as e:
        print(f"  ❌ Result send error: {e}")


# ── Telegram Command Listener ─────────────────────────────────
BOT_TOKEN   = ""   # app.py থেকে auto নেবে — নিচে দেখুন
LAST_UPDATE = 0

def listen_telegram():
    global signal_active, LAST_UPDATE, BOT_TOKEN

    # config.py থেকে TOKEN নেওয়া
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(__file__))
        from config import BOT_TOKEN as TOKEN
        BOT_TOKEN = TOKEN
    except:
        print("⚠️ Could not load BOT_TOKEN for Telegram commands")
        return

    print("📱 Telegram command listener started (/stop, /start, /status)")

    while True:
        try:
            url  = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            resp = requests.get(url, params={"offset": LAST_UPDATE + 1, "timeout": 30}, timeout=35)
            data = resp.json()

            for update in data.get("result", []):
                LAST_UPDATE = update["update_id"]
                msg = update.get("message", {})
                text = msg.get("text", "").strip().lower()
                chat_id = msg.get("chat", {}).get("id")

                if text == "/stop":
                    signal_active = False
                    _reply(chat_id, "🔴 Signal বন্ধ করা হয়েছে।")
                    print("🔴 Signal stopped by Telegram command")

                elif text == "/start":
                    signal_active = True
                    _reply(chat_id, "🟢 Signal চালু হয়েছে!")
                    print("🟢 Signal started by Telegram command")

                elif text == "/status":
                    status = "🟢 চালু" if signal_active else "🔴 বন্ধ"
                    _reply(chat_id, f"Signal status: {status}")

        except Exception as e:
            pass
        time.sleep(2)


def _reply(chat_id, text):
    try:
        from config import BOT_TOKEN as TOKEN
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
    except:
        pass


# ── Main Loop ─────────────────────────────────────────────────
def main():
    global signal_active

    print("=" * 55)
    print("🚀 Bybit Auto Signal Bot Started!")
    print(f"📊 Pairs: {', '.join(PAIRS)}")
    print(f"⏱ Interval: M{INTERVAL} | Check: {CHECK_EVERY}s")
    print(f"⏳ Result check after: {RESULT_DELAY}s")
    print(f"🌐 Server: {BOT_SERVER}")
    print("📱 Commands: /stop | /start | /status")
    print("=" * 55)

    # Telegram command listener আলাদা thread-এ
    cmd_thread = threading.Thread(target=listen_telegram, daemon=True)
    cmd_thread.start()

    last = {p: None for p in PAIRS}

    while True:
        if not signal_active:
            print("🔴 Signal OFF — waiting...")
            time.sleep(10)
            continue

        t = datetime.now(BD_TZ).strftime("%H:%M:%S")
        print(f"\n[{t}] Checking {len(PAIRS)} pairs...")

        for pair in PAIRS:
            if not signal_active:
                break

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
