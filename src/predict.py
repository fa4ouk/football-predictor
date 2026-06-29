"""
Logique de génération des pronostics - Version Wimbledon
Limite les matchs à 35 pour respecter le quota Groq gratuit.
"""
import uuid
from datetime import datetime, timezone
from odds_client import fetch_odds_all_leagues, format_odds_for_ai
from ai_engine import analyze
from storage import (
    load_pending, save_pending,
    load_history, save_history,
    load_odds_cache, save_odds_cache,
    load_last_predictions, save_last_predictions,
)
from stats import compute
from telegram_bot import send, alert, format_predictions

# Limite stricte pour ne pas dépasser 12000 tokens chez Groq
MAX_MATCHES_FOR_AI = 20


def run(session_type: str = "morning"):
    now = datetime.now(timezone.utc)

    # ── Récupération des cotes ───────────────────────────
    use_cache = session_type == "evening"
    if use_cache:
        cache = load_odds_cache()
        cache_time = None
        if cache and cache.get("timestamp"):
            try:
                cache_time = datetime.fromisoformat(cache["timestamp"])
            except ValueError:
                pass
        if not cache or not cache_time or (now - cache_time).total_seconds() > 14 * 3600:
            print("  ⚠ Cache trop vieux, fetch frais même pour le soir")
            use_cache = False
            raw_matches = fetch_odds_all_leagues()
        else:
            raw_matches = cache.get("matches", [])
            print(f"  ✓ Cache utilisé ({len(raw_matches)} matchs)")
    else:
        raw_matches = fetch_odds_all_leagues()

    if not raw_matches:
        alert("Aucun match trouvé. Erreur API ou pas de matchs aujourd'hui.")
        return

    if session_type == "morning" or not use_cache:
        save_odds_cache({"timestamp": now.isoformat(), "matches": raw_matches})

    # ── Formatage et limitation pour l'IA ───────────────
    odds_data = format_odds_for_ai(raw_matches)
    if not odds_data:
        alert("Aucune cote exploitable.")
        return

    # Trier par heure et limiter à MAX_MATCHES_FOR_IA pour ne pas exploser Groq
    odds_data = sorted(odds_data, key=lambda x: x["time"])[:MAX_MATCHES_FOR_AI]
    print(f"  ✂️ Limité à {len(odds_data)} matchs pour l'IA (limite Groq)")

    # ── Historique & stats ───────────────────────────────
    history = load_history()
    stats = compute(history)
    previous = load_last_predictions() if use_cache else None

    # ── Appel à l'IA ────────────────────────────────────
    print("  🧠 Appel à Groq...")
    predictions = analyze(odds_data, stats, previous)

    if not predictions:
        alert("L'IA n'a retourné aucun pronostic valide.")
        return

    predictions = predictions[:5]

    # ── Construction des enregistrements ─────────────────
    session_id = str(uuid.uuid4())
    pending = load_pending()

    seen_keys = {
        (p["match"]["home_team"], p["match"]["away_team"],
         p["match"]["commence_time"], p["selection"]["description"])
        for p in pending
    }

    new_records = []
    for p in predictions:
        # Retrouver l'heure complète depuis les données brutes (car l'IA n'a que l'heure)
        full_time = now.isoformat()
        for rm in raw_matches:
            if rm["id"] == p.get("match_id"):
                full_time = rm["commence_time"]
                break

        key = (p["home_team"], p["away_team"], full_time, p["selection_description"])
        if key in seen_keys:
            print(f"  ⏭ Doublon ignoré: {p['home_team']} vs {p['away_team']}")
            continue

        record = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "session_type": session_type,
            "created_at": now.isoformat(),
            "match": {
                "home_team": p["home_team"],
                "away_team": p["away_team"],
                "commence_time": full_time,
                "league": p["league"],
                "league_key": None,
                "match_id": p.get("match_id", ""),
            },
            "selection": {
                "market_key": p["market_key"],
                "description": p["selection_description"],
                "outcome_name": p["outcome_name"],
            },
            "odds": p["odds"],
            "bookmaker": p["bookmaker"],
            "category": p["category"],
            "expected_value": p["expected_value"],
            "explanation": p["explanation"],
            "result": "pending",
            "verified_at": None,
        }

        for rm in raw_matches:
            if rm["id"] == p.get("match_id"):
                record["match"]["league_key"] = rm.get("_league_key")
                break

        new_records.append(record)
        pending.append(record)
        seen_keys.add(key)

    if not new_records:
        print("  ⏭ Tous les pronostics étaient des doublons.")
        return

    # ── Sauvegarde ──────────────────────────────────────
    save_pending(pending)
    history.setdefault("predictions", []).extend(new_records)
    save_history(history)
    save_last_predictions(new_records)

    # ── Notification Telegram ───────────────────────────
    msg = format_predictions(new_records, session_type)
    ok = send(msg)
    print(f"  {'✅' if ok else '❌'} {len(new_records)} pronostics envoyés ({session_type})")
