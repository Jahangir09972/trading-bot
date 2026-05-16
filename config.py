# ============================================================
#  config.py — সব settings এখানে পরিবর্তন করুন
# ============================================================

# ── Telegram ─────────────────────────────────────────────────
BOT_TOKEN  = "8819132939:AAED-WSiZ_jvkX6y8QPrgqCfx9BiUgScoV8"       # @BotFather থেকে পাবেন
CHANNEL_ID = "-1003949570585"      # যেমন: -1001234567890

# ── Server ───────────────────────────────────────────────────
PORT = 5000

# ── Market Categories ────────────────────────────────────────
CRYPTO_SYMBOLS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE",
    "DOT", "ADA", "AVAX", "MATIC", "LTC", "LINK",
    "UNI", "ATOM", "TRX", "NEAR", "APT", "OP"
]

STOCK_SYMBOLS = [
    "AAPL", "TSLA", "GOOG", "GOOGL", "AMZN", "MSFT",
    "META", "NVDA", "NFLX", "BABA", "AMD", "INTC",
    "UBER", "LYFT", "SNAP", "TWTR", "COIN", "HOOD"
]

COMMODITY_SYMBOLS = [
    "XAUUSD", "XAGUSD", "GOLD", "SILVER",
    "USOIL", "UKOIL", "WTI", "BRENT"
]

INDEX_SYMBOLS = [
    "US30", "US100", "US500", "SPX", "NDX",
    "GER40", "UK100", "JPN225", "AUS200"
]

# বাকি সব Forex হিসেবে ধরা হবে

# ── Message Template ─────────────────────────────────────────
SIGNAL_TEMPLATE = """
🔔 *SIGNAL ALERT*
━━━━━━━━━━━━━━━━━━
{market_icon}  *{pair}*  `{category}`
{direction_icon}
⏱ Timeframe : `{timeframe}`
🎯 Entry     : `{entry}`
🕐 Time (BD) : `{time}`
━━━━━━━━━━━━━━━━━━
📊 *Technical Analysis*
🔴 Resistance : `{resistance}`
🔵 Support    : `{support}`
📉 Trend      : `{trend}`
━━━━━━━━━━━━━━━━━━
🏆 *{pair} Today Stats*
✅ Win: {win}  ❌ Loss: {loss}  📊 {winrate}%
"""

RESULT_TEMPLATE = """
{result_icon} *RESULT — {pair}*
━━━━━━━━━━━━━━
📊 Today Stats
✅ Win  : {win}
❌ Loss : {loss}
🎯 Rate : {winrate}%
━━━━━━━━━━━━━━
"""
