# ============================================================
#  stats.py — Per-pair Win/Loss tracking (in-memory + file backup)
# ============================================================

import json
import os
from datetime import date

STATS_FILE = "stats_data.json"


def _load() -> dict:
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    return {}


def _save(data: dict):
    with open(STATS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _today() -> str:
    return str(date.today())


def record_result(pair: str, outcome: str):
    """outcome = 'WIN' or 'LOSS'"""
    data  = _load()
    today = _today()

    if pair not in data:
        data[pair] = {}
    if today not in data[pair]:
        data[pair][today] = {"win": 0, "loss": 0}

    if outcome.upper() == "WIN":
        data[pair][today]["win"] += 1
    else:
        data[pair][today]["loss"] += 1

    _save(data)


def get_today_stats(pair: str) -> dict:
    data  = _load()
    today = _today()
    s     = data.get(pair, {}).get(today, {"win": 0, "loss": 0})
    total = s["win"] + s["loss"]
    rate  = round(s["win"] / total * 100) if total > 0 else 0
    return {"win": s["win"], "loss": s["loss"], "winrate": rate}


def get_all_today_stats() -> dict:
    """সব pair-এর আজকের stats একসাথে"""
    data  = _load()
    today = _today()
    result = {}
    for pair, days in data.items():
        s = days.get(today, {"win": 0, "loss": 0})
        total = s["win"] + s["loss"]
        rate  = round(s["win"] / total * 100) if total > 0 else 0
        result[pair] = {"win": s["win"], "loss": s["loss"], "winrate": rate}
    return result


def reset_pair(pair: str):
    """একটি pair-এর আজকের stats reset"""
    data  = _load()
    today = _today()
    if pair in data and today in data[pair]:
        data[pair][today] = {"win": 0, "loss": 0}
        _save(data)
