# ============================================================
#  market.py — Market category auto-detection
# ============================================================

from config import (
    CRYPTO_SYMBOLS, STOCK_SYMBOLS,
    COMMODITY_SYMBOLS, INDEX_SYMBOLS
)


def detect_market(pair: str) -> dict:
    """
    pair যেমন: 'AUDJPY', 'BTCUSDT', 'AAPL', 'XAUUSD'
    returns: { category, icon, label }
    """
    p = pair.upper().replace("-", "").replace("/", "").replace("_", "")

    for sym in CRYPTO_SYMBOLS:
        if sym in p:
            return {"category": "Crypto",    "icon": "🪙", "label": "Crypto OTC"}

    for sym in COMMODITY_SYMBOLS:
        if sym in p:
            return {"category": "Commodity", "icon": "🥇", "label": "Commodity"}

    for sym in INDEX_SYMBOLS:
        if sym in p:
            return {"category": "Index",     "icon": "📊", "label": "Index"}

    for sym in STOCK_SYMBOLS:
        if sym in p:
            return {"category": "Stock",     "icon": "📈", "label": "Stock"}

    # Default → Forex
    return {"category": "Forex", "icon": "💱", "label": "Forex OTC"}


def format_direction(direction: str) -> str:
    d = direction.upper()
    if d == "PUT":
        return "🔴 *PUT* ▼  (Sell)"
    elif d == "CALL":
        return "🟢 *CALL* ▲  (Buy)"
    return f"⚪ {direction}"
