"""
Configuration centrale de l'agent pronostiqueur.
Toutes les clés API sont lues depuis les variables d'environnement
(configurées comme Secrets dans GitHub).
"""
import os

# ── The Odds API ──────────────────────────────────────────────
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# Championnats ACTUELS (mis à jour pour l'intersaison été 2025)
# Les championnats européens reviendront en août 2025
LEAGUES = {
    # Championnats américains (jouent actuellement)
    "soccer_usa_mls":                  "MLS",
    "soccer_brazil_serie_a":           "Série A Brésil",
    "soccer_mexico_liga_mx":           "Liga MX",
    # Compétitions internationales estivales
    "soccer_fifa_club_world_cup":      "Club World Cup 2025",
    # Amicaux clubs (toujours des matchs dispo en été)
    "soccer_club_friendlies":          "Matchs Amicaux Clubs",
    # Championnats européens (actifs en août — garder pour la saison)
    "soccer_epl":                      "Premier League",
    "soccer_spain_la_liga":            "La Liga",
    "soccer_germany_bundesliga":       "Bundesliga",
    "soccer_italy_serie_a":            "Serie A",
    "soccer_france_ligue_one":         "Ligue 1",
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
