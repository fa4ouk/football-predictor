"""
Configuration centrale de l'agent pronostiqueur.
Toutes les clés API sont lues depuis les variables d'environnement
(configurées comme Secrets dans GitHub).
"""
import os

# ── The Odds API ──────────────────────────────────────────────
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# 8 championnats majeurs couverts par le plan gratuit (~480 req/mois)
# Ajouter des clés supplémentaires consommera plus de requêtes
LEAGUES = {
    "soccer_epl":                 "Premier League",
    "soccer_spain_la_liga":       "La Liga",
    "soccer_germany_bundesliga":  "Bundesliga",
    "soccer_italy_serie_a":       "Serie A",
    "soccer_france_ligue_one":    "Ligue 1",
    "soccer_uefa_champs_league":  "Ligue des Champions",
    "soccer_uefa_europa_league":  "Ligue Europa",
    "soccer_portugal_primeira_liga": "Liga Portugal",
}

# Marchés à récupérer (séparés par des virgules pour l'API)
MARKETS = "h2h,totals"

# Plage de cotes acceptable pour les sélections
MIN_ODDS = 1.4
MAX_ODDS = 2.5

# ── Groq ─────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Telegram ─────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── Délais ───────────────────────────────────────────────────
# Heures après lesquelles un pronostic non vérifié est marqué "unverifiable"
VERIFICATION_TIMEOUT_HOURS = 24

# Heures de fenêtre pour chercher des matchs à venir (depuis maintenant)
MATCHES_LOOKAHEAD_HOURS = 36
