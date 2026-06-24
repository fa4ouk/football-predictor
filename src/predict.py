"""
Logique de génération des pronostics.
Appelé 2 fois/jour par GitHub Actions (matin + soir).
Le soir réutilise le cache de cotes du matin pour économiser des requêtes API.
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


def run(session_type: str = "morning"):
    """Point d'entrée principal de la génération."""
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
        # Si le cache est trop vieux (>14h), on refetch
        if not cache or not cache_time or (now - cache_time).total_seconds() > 14 * 3600:
            print("  ⚠ Cache trop vieux ou absent, fetch frais même pour le soir")
            use_cache = False
            raw_matches = fetch_odds_all_leagues()
        else:
            raw_matches = cache.get("matches", [])
            print(f"  ✓ Cache utilisé ({len(raw_matches)} matchs)")
    else:
        raw_matches = fetch_odds_all_leagues()

    if not raw_matches:
        alert("Aucun match trouvé dans les cotes. Peut-être pas de matchs aujourd'hui, ou erreur API.")
        return

    # Mise en cache (matin uniquement, ou si on a refetch le soir)
    if session_type == "morning" or not use_cache:
        save_odds_cache({"timestamp": now.isoformat(), "matches": raw_matches})

    # ── Formatage pour l'IA ──────────────────────────────
    odds_data = format_odds_for_ai(raw_matches)
    if not odds_data:
        alert("Aucune cote exploitable trouvée après formatage.")
        return

    # ── Historique & stats ───────────────────────────────
    history = load_history()
    stats = compute(history)

    # Pronostics du matin à exclure le soir
    previous = load_last_predictions() if use_cache else None

    # ── Appel à l'IA ────────────────────────────────────
    print("  🧠 Appel à Groq...")
    predictions = analyze(odds_data, stats, previous)

    if not predictions:
        alert("L'IA n'a retourné aucun pronostic valide. Vérifiez les logs.")
        return

    # Compléter à 5 si l'IA en a donné moins (avec note d'honnêteté)
    if len(predictions) < 5:
        print(f"  ⚠ L'IA n'a fourni que {len(predictions)} pronostics (sur 5 demandés)")

    predictions = predictions[:5]

    # ── Construction des enregistrements ─────────────────
    session_id = str(uuid.uuid4())
    pending = load_pending()

    # Déduplication : clé = (home, away, commence_time, description)
    seen_keys = {
        (p["match"]["home_team"], p["match"]["away_team"],
         p["match"]["commence_time"], p["selection"]["description"])
        for p in pending
    }

    new_records = []
    for p in predictions:
        key = (p["home_team"], p["away_team"], p["commence_time"], p["selection_description"])
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
                "commence_time": p["commence_time"],
                "league": p["league"],
                "league_key": None,  # sera rempli ci-dessous
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

        # Retrouver la league_key depuis les données brutes
        for rm in raw_matches:
            if rm["id"] == p.get("match_id"):
                record["match"]["league_key"] = rm.get("_league_key")
                break

        new_records.append(record)
        pending.append(record)
        seen_keys.add(key)

    if not new_records:
        print("  ⏭ Tous les pronostics étaient des doublons, rien à envoyer.")
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
