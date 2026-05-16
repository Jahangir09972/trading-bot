# ============================================================
#  telegram.py — Telegram message sender
# ============================================================

import requests
from config import BOT_TOKEN, CHANNEL_ID


def send_message(text: str, chat_id: str = None) -> bool:
    """Telegram channel-এ message পাঠায়"""
    target = chat_id or CHANNEL_ID
    url    = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id":    target,
        "text":       text,
        "parse_mode": "Markdown"
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if not data.get("ok"):
            print(f"[Telegram Error] {data.get('description')}")
            return False
        return True
    except Exception as e:
        print(f"[Telegram Exception] {e}")
        return False


def send_photo(image_url: str, caption: str = "", chat_id: str = None) -> bool:
    """ছবিসহ message পাঠায় (chart screenshot)"""
    target = chat_id or CHANNEL_ID
    url    = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    payload = {
        "chat_id":    target,
        "photo":      image_url,
        "caption":    caption,
        "parse_mode": "Markdown"
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.json().get("ok", False)
    except Exception as e:
        print(f"[Photo Error] {e}")
        return False


def get_channel_id(username: str) -> str:
    """Channel ID বের করে (যেমন @MyChannel)"""
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
    resp = requests.get(url, params={"chat_id": username})
    data = resp.json()
    if data.get("ok"):
        return str(data["result"]["id"])
    return "Error: " + data.get("description", "unknown")
