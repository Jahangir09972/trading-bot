# ============================================================
#  binance_signal.py — Pro Multi-Indicator Signal Bot
#  Indicators: EMA + RSI + Bollinger Band + MACD + S/R + Trend
# ============================================================

import requests
import time
import threading
from datetime import datetime
import pytz
import math

BOT_SERVER   = "https://trading-bot-production-09fe.up.railway.app"
BD_TZ        = pytz.timezone("Asia/Dhaka")

PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "DOTUSDT", "LTCUSDT", "AVAXUSDT",
]

INTERVAL     = "1"    # 1 মিনিট
CHECK_EVERY  = 30     # 30 সেকেন্ড পরপর
MIN_CANDLES  = 35
RESULT_DELAY = 60     # 60 সেকেন্ড পরে result

# Signal confirm করতে কতো indicator একমত হতে হবে (3 এর মধ্যে)
MIN_CONFIRM  = 3

signal_active = True


# ── Bybit API ─────────────────────────────────────────────────
def get_candles(symbol):
    url    = "https://api.bybit.com/v5/market/kline"
    params = {"category": "spot", "symbol": symbol, "interval": INTERVAL, "limit": 100}
    try:
        resp = requests.get(url, params=params, timeout=10)
        try:
            data = resp.json()
        except Exception:
            return [], [], [], []
        if not isinstance(data, dict) or data.get("retCode") != 0:
            return [], [], [], []
        candles = list(reversed(data.get("result", {}).get("list", [])))
        if len(candles) < 10:
            return [], [], [], []
        closes, highs, lows, volumes = [], [], [], []
        for c in candles:
            try:
                closes.append(float(c[4]))
                highs.append(float(c[2]))
                lows.append(float(c[3]))
                volumes.append(float(c[5]))
            except Exception:
                continue
        return closes, highs, lows, volumes
    except Exception as e:
        print(f"  ⚠️ {symbol}: {e}")
        return [], [], [], []


def get_current_price(symbol):
    try:
        resp = requests.get(
            "https://api.bybit.com/v5/market/tickers",
            params={"category": "spot", "symbol": symbol}, timeout=10
        )
        data = resp.json()
        if data.get("retCode") == 0:
            return float(data["result"]["list"][0]["lastPrice"])
    except Exception:
        pass
    return None


# ── Indicators ────────────────────────────────────────────────

def ema(prices, period):
    if len(prices) < period:
        return []
    k   = 2 / (period + 1)
    out = [sum(prices[:period]) / period]
    for p in prices[period:]:
        out.append(p * k + out[-1] * (1 - k))
    return out


def rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, period + 1):
        d = prices[i] - prices[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains) / period
    al = sum(losses) / period
    if al == 0:
        return 100
    return round(100 - 100 / (1 + ag / al), 2)


def bollinger_bands(prices, period=20, std_dev=2):
    if len(prices) < period:
        return None, None, None
    recent = prices[-period:]
    mid    = sum(recent) / period
    std    = math.sqrt(sum((p - mid)**2 for p in recent) / period)
    return round(mid + std_dev * std, 6), round(mid, 6), round(mid - std_dev * std, 6)


def macd(prices, fast=12, slow=26, signal_period=9):
    if len(prices) < slow + signal_period:
        return None, None
    ema_fast   = ema(prices, fast)
    ema_slow   = ema(prices, slow)
    min_len    = min(len(ema_fast), len(ema_slow))
    macd_line  = [ema_fast[-min_len + i] - ema_slow[-min_len + i] for i in range(min_len)]
    if len(macd_line) < signal_period:
        return None, None
    signal_line = ema(macd_line, signal_period)
    return macd_line[-1], signal_line[-1] if signal_line else None


def support_resistance(highs, lows, period=20):
    if len(highs) < period:
        return None, None
    return round(max(highs[-period:]), 6), round(min(lows[-period:]), 6)


def trend_direction(closes, period=20):
    if len(closes) < period:
        return "SIDEWAYS"
    e = ema(closes, period)
    if not e or len(e) < 3:
        return "SIDEWAYS"
    if e[-1] > e[-2] > e[-3]:
        return "UP"
    if e[-1] < e[-2] < e[-3]:
        return "DOWN"
    return "SIDEWAYS"


# ── Pro Signal Detection ───────────────────────────────────────
def detect_signal(closes, highs, lows, volumes):
    if len(closes) < MIN_CANDLES:
        return None

    cur  = closes[-1]
    prev = closes[-2]

    # Calculate all indicators
    ema9   = ema(closes, 9)
    ema21  = ema(closes, 21)
    rsi_v  = rsi(closes[-15:])
    bb_up, bb_mid, bb_low = bollinger_bands(closes)
    macd_v, macd_sig      = macd(closes)
    res, sup              = support_resistance(highs, lows)
    trend                 = trend_direction(closes)

    if not all([ema9, ema21, bb_up, bb_low, res, sup]):
        return None

    e9  = ema9[-1]
    e21 = ema21[-1]
    pe9 = ema9[-2]
    pe21= ema21[-2]

    # ── CALL Signals (প্রতিটা = 1 point) ──────────────────────
    call_score = 0
    call_reasons = []

    # 1. EMA Cross (EMA9 উপরে গেল EMA21 এর)
    if pe9 <= pe21 and e9 > e21:
        call_score += 1
        call_reasons.append("EMA✅")

    # 2. RSI Oversold থেকে ফিরছে
    if 30 < rsi_v < 50:
        call_score += 1
        call_reasons.append(f"RSI{rsi_v}✅")

    # 3. Bollinger Band নিচে touch করে ফিরছে
    if prev <= bb_low and cur > bb_low:
        call_score += 1
        call_reasons.append("BB✅")

    # 4. MACD Bullish
    if macd_v and macd_sig and macd_v > macd_sig:
        call_score += 1
        call_reasons.append("MACD✅")

    # 5. Support থেকে bounce
    if abs(cur - sup) / sup < 0.003:
        call_score += 1
        call_reasons.append("SUP✅")

    # 6. Trend UP
    if trend == "UP":
        call_score += 1
        call_reasons.append("TREND✅")

    # ── PUT Signals ────────────────────────────────────────────
    put_score = 0
    put_reasons = []

    # 1. EMA Cross (EMA9 নিচে গেল EMA21 এর)
    if pe9 >= pe21 and e9 < e21:
        put_score += 1
        put_reasons.append("EMA✅")

    # 2. RSI Overbought থেকে ফিরছে
    if 50 < rsi_v < 70:
        put_score += 1
        put_reasons.append(f"RSI{rsi_v}✅")

    # 3. Bollinger Band উপরে touch করে ফিরছে
    if prev >= bb_up and cur < bb_up:
        put_score += 1
        put_reasons.append("BB✅")

    # 4. MACD Bearish
    if macd_v and macd_sig and macd_v < macd_sig:
        put_score += 1
        put_reasons.append("MACD✅")

    # 5. Resistance থেকে reject
    if abs(cur - res) / res < 0.003:
        put_score += 1
        put_reasons.append("RES✅")

    # 6. Trend DOWN
    if trend == "DOWN":
        put_score += 1
        put_reasons.append("TREND✅")

    # ── Final Decision ─────────────────────────────────────────
    if call_score >= MIN_CONFIRM and call_score > put_score:
        return {
            "direction":  "CALL",
            "entry":      round(cur, 6),
            "resistance": res,
            "support":    sup,
            "trend":      trend,
            "score":      call_score,
            "reasons":    " ".join(call_reasons),
            "rsi":        rsi_v,
            "bb_up":      bb_up,
            "bb_low":     bb_low,
        }

    if put_score >= MIN_CONFIRM and put_score > call_score:
        return {
            "direction":  "PUT",
            "entry":      round(cur, 6),
            "resistance": res,
            "support":    sup,
            "trend":      trend,
            "score":      put_score,
            "reasons":    " ".join(put_reasons),
            "rsi":        rsi_v,
            "bb_up":      bb_up,
            "bb_low":     bb_low,
        }

    return None


# ── Auto Result ───────────────────────────────────────────────
def check_result(pair, direction, entry_price):
    time.sleep(RESULT_DELAY)
    current = get_current_price(pair)
    if not current:
        return
    outcome = "WIN" if (
        (direction == "CALL" and current > entry_price) or
        (direction == "PUT"  and current < entry_price)
    ) else "LOSS"
    t    = datetime.now(BD_TZ).strftime("%H:%M:%S")
    icon = "🏆" if outcome == "WIN" else "❌"
    print(f"  {icon} [{t}] {pair} {outcome} Entry:{entry_price} Now:{current}")
    try:
        requests.post(f"{BOT_SERVER}/result",
                      json={"pair": pair, "outcome": outcome}, timeout=10)
    except Exception:
        pass


# ── Send Signal ───────────────────────────────────────────────
def send_signal(pair, signal):
    try:
        trend_txt = (
            f"{signal['trend']} | "
            f"RSI:{signal['rsi']} | "
            f"BB:{signal['bb_low']}-{signal['bb_up']} | "
            f"Score:{signal['score']}/6 | "
            f"{signal['reasons']}"
        )
        requests.post(f"{BOT_SERVER}/signal", json={
            "pair":       pair,
            "direction":  signal["direction"],
            "entry":      str(signal["entry"]),
            "timeframe":  f"M{INTERVAL}",
            "resistance": str(signal["resistance"]),
            "support":    str(signal["support"]),
            "trend":      trend_txt,
        }, timeout=10)
        t = datetime.now(BD_TZ).strftime("%H:%M:%S")
        print(f"  ✅ [{t}] {pair} {signal['direction']} @ {signal['entry']} [{signal['score']}/6] {signal['reasons']}")
        threading.Thread(
            target=check_result,
            args=(pair, signal["direction"], signal["entry"]),
            daemon=True
        ).start()
    except Exception as e:
        print(f"  ❌ {pair}: {e}")


# ── Telegram Commands ─────────────────────────────────────────
LAST_UPDATE = 0

def listen_telegram():
    global signal_active, LAST_UPDATE
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from config import BOT_TOKEN
    except Exception as e:
        print(f"⚠️ Telegram commands disabled: {e}")
        return
    print("📱 Commands: /stop | /start | /status")
    while True:
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params={"offset": LAST_UPDATE + 1, "timeout": 20}, timeout=25
            )
            for update in resp.json().get("result", []):
                LAST_UPDATE = update["update_id"]
                msg     = update.get("message", {})
                text    = msg.get("text", "").strip().lower()
                chat_id = msg.get("chat", {}).get("id")
                if text == "/stop":
                    signal_active = False
                    _reply(BOT_TOKEN, chat_id, "🔴 Signal বন্ধ করা হয়েছে।")
                    print("🔴 Stopped")
                elif text == "/start":
                    signal_active = True
                    _reply(BOT_TOKEN, chat_id, "🟢 Signal চালু হয়েছে!")
                    print("🟢 Started")
                elif text == "/status":
                    s = "🟢 চালু" if signal_active else "🔴 বন্ধ"
                    _reply(BOT_TOKEN, chat_id, f"Signal: {s}")
        except Exception:
            pass
        time.sleep(3)


def _reply(token, chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text}, timeout=10
        )
    except Exception:
        pass


# ── Main ──────────────────────────────────────────────────────
def main():
    global signal_active
    print("=" * 60)
    print("🚀 Pro Multi-Indicator Signal Bot Started!")
    print(f"📊 Pairs     : {', '.join(PAIRS)}")
    print(f"⏱  Interval  : M{INTERVAL} | Check: {CHECK_EVERY}s")
    print(f"📈 Indicators: EMA9/21 + RSI + BB + MACD + S/R + Trend")
    print(f"✅ Min Confirm: {MIN_CONFIRM}/6 indicators")
    print(f"⏳ Result    : after {RESULT_DELAY}s")
    print(f"🌐 Server    : {BOT_SERVER}")
    print("=" * 60)

    threading.Thread(target=listen_telegram, daemon=True).start()
    last = {p: None for p in PAIRS}

    while True:
        if not signal_active:
            print("🔴 Signal OFF...")
            time.sleep(10)
            continue

        t = datetime.now(BD_TZ).strftime("%H:%M:%S")
        print(f"\n[{t}] Checking {len(PAIRS)} pairs...")

        for pair in PAIRS:
            if not signal_active:
                break
            closes, highs, lows, volumes = get_candles(pair)
            if len(closes) < MIN_CANDLES:
                continue
            signal = detect_signal(closes, highs, lows, volumes)
            if signal:
                if last[pair] != signal["direction"]:
                    send_signal(pair, signal)
                    last[pair] = signal["direction"]
            else:
                print(f"  ➖ {pair}: No signal")
            time.sleep(0.5)

        print(f"⏳ Next: {CHECK_EVERY}s...")
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()
