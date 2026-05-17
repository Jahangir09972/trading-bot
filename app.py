# ============================================================
#  app.py — Main server (Flask)
#  Run: python app.py
# ============================================================

from flask import Flask, request, jsonify
from datetime import datetime
import pytz

from config import PORT, SIGNAL_TEMPLATE, RESULT_TEMPLATE
from market import detect_market, format_direction
from stats  import record_result, get_today_stats, get_all_today_stats, reset_pair
from telegram import send_message

app = Flask(__name__)

BD_TZ = pytz.timezone("Asia/Dhaka")


def bd_time() -> str:
    return datetime.now(BD_TZ).strftime("%H:%M  %d-%b-%Y")


# ─────────────────────────────────────────────────────────────
#  POST /signal
#  TradingView webhook এখানে আসবে
#  Body (JSON):
#  {
#    "pair":       "AUDJPY",
#    "direction":  "PUT",          ← PUT or CALL
#    "entry":      "113.510",
#    "timeframe":  "M1",
#    "resistance": "113.696",      ← optional
#    "support":    "113.158",      ← optional
#    "trend":      "DOWN"          ← optional
#  }
# ─────────────────────────────────────────────────────────────
@app.route("/signal", methods=["POST"])
def signal():
    d = request.json or {}

    pair      = d.get("pair",       "UNKNOWN").upper()
    direction = d.get("direction",  "PUT").upper()
    entry     = d.get("entry",      "N/A")
    timeframe = d.get("timeframe",  "M1")
    resistance= d.get("resistance", "N/A")
    support   = d.get("support",    "N/A")
    trend     = d.get("trend",      "N/A")

    market = detect_market(pair)
    stats  = get_today_stats(pair)

    msg = SIGNAL_TEMPLATE.format(
        market_icon  = market["icon"],
        pair         = pair,
        category     = market["label"],
        direction_icon = format_direction(direction),
        timeframe    = timeframe,
        entry        = entry,
        time         = bd_time(),
        resistance   = resistance,
        support      = support,
        trend        = trend,
        win          = stats["win"],
        loss         = stats["loss"],
        winrate      = stats["winrate"]
    )

    ok = send_message(msg)
    return jsonify({"status": "sent" if ok else "failed", "pair": pair})


# ─────────────────────────────────────────────────────────────
#  POST /result
#  Signal শেষ হলে WIN/LOSS পাঠান
#  Body: { "pair": "AUDJPY", "outcome": "WIN" }
# ─────────────────────────────────────────────────────────────
@app.route("/result", methods=["POST"])
def result():
    d       = request.json or {}
    pair    = d.get("pair",    "UNKNOWN").upper()
    outcome = d.get("outcome", "LOSS").upper()

    record_result(pair, outcome)
    stats = get_today_stats(pair)

    icon = "🏆" if outcome == "WIN" else "❌"
    msg  = RESULT_TEMPLATE.format(
        result_icon = icon,
        pair        = pair,
        win         = stats["win"],
        loss        = stats["loss"],
        winrate     = stats["winrate"]
    )

    ok = send_message(msg)
    return jsonify({"status": "ok", "stats": stats})


# ─────────────────────────────────────────────────────────────
#  GET /summary
#  সব pair-এর আজকের summary
# ─────────────────────────────────────────────────────────────
@app.route("/summary", methods=["GET"])
def summary():
    all_stats = get_all_today_stats()

    if not all_stats:
        send_message("📊 *Today Summary*\nআজ কোনো signal নেই।")
        return jsonify({"status": "empty"})

    lines = ["📊 *TODAY FULL SUMMARY*\n━━━━━━━━━━━━━━━━━━"]
    for pair, s in all_stats.items():
        market = detect_market(pair)
        lines.append(
            f"{market['icon']} *{pair}* — ✅{s['win']} ❌{s['loss']} ({s['winrate']}%)"
        )
    lines.append("━━━━━━━━━━━━━━━━━━")
    send_message("\n".join(lines))
    return jsonify(all_stats)


# ─────────────────────────────────────────────────────────────
#  POST /reset
#  একটি pair reset: { "pair": "AUDJPY" }
# ─────────────────────────────────────────────────────────────
@app.route("/reset", methods=["POST"])
def reset():
    pair = (request.json or {}).get("pair", "").upper()
    reset_pair(pair)
    return jsonify({"status": "reset", "pair": pair})


# ─────────────────────────────────────────────────────────────
#  GET /health  — server চলছে কিনা দেখুন
# ─────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running", "time": bd_time()})

import threading
from binance_signal import main as binance_main

def start_binance():
    binance_main()

thread = threading.Thread(target=start_binance, daemon=True)
thread.start()

if __name__ == "__main__":
    print(f"✅ Bot server running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
