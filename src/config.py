"""
Configuration centrale - Juin 2026 (Coupe du Monde + ligues actives)
"""
import os

# ── The Odds API ──────────────────────────────────────────────
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# Championnats et compétitions ACTIFS en juin 2026
LEAGUES = {
    # COUPE DU MONDE 2026 (Priorité absolue)
    "soccer_fifa_world_cup":           "Coupe du Monde 2026",
    
    # Championnats américains (en cours en juin)
    "soccer_usa_mls":                  "MLS",
    "soccer_mexico_liga_mx":           "Liga MX",
    "soccer_brazil_serie_a":           "Série A Brésil",
    "soccer_argentina_primera_division":"Liga Argentine",
    "soccer_japan_j_league":           "J-League",
}

# Marchés à récupérer
MARKETS = "h2h,totals"

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
MATCHES_LOOKAHEAD_HOURS = 36
