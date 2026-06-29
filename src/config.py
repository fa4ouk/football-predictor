"""
Configuration Wimbledon - Spécialisé Tennis sur gazon
"""
import os

# ── The Odds API ──────────────────────────────────────────────
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

LEAGUES = {
    "tennis_atp_wimbledon": "Wimbledon Hommes (ATP)",
    "tennis_wta_wimbledon": "Wimbledon Femmes (WTA)",
}

# Marchés tennis : Vainqueur, Total jeux, Handicap jeux
MARKETS = "h2h,totals,spreads"

# Plage de cotes acceptable
MIN_ODDS = 1.4
MAX_ODDS = 2.5

# ── Groq ─────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Telegram ─────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── Délais ───────────────────────────────────────────────────
VERIFICATION_TIMEOUT_HOURS = 24

# Regarder UNIQUEMENT les matchs des 14 prochaines heures
# Le matin à 9h UTC, ça couvre jusqu'à 23h UTC (toute la journée Wimbledon)
MATCHES_LOOKAHEAD_HOURS = 14
