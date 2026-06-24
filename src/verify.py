"""
Logique de vérification des résultats.
Processus séparé de la génération, exécuté 4 fois/jour.
Utilise les scores de The Odds API (même match_id que les cotes).
"""
import re
from datetime import datetime, timezone, timedelta
from odds_client import fetch_scores_for_leagues, get_league_keys_with_pending
from storage import load_pending, save_pending, load_history, save_history
from telegram_bot import send, alert, format_recap
from config import VERIFICATION_TIMEOUT_HOURS


def _determine_result(prediction: dict, score_data: dict) -> str:
    """
    Détermine si un pronostic est gagné ou perdu
    à partir des données de score de l'API.
    """
    scores = score_data.get("scores", [])
    if len(scores) < 2:
        return "pending"

    # L'API The Odds met généralement le domicile en premier
    home_score = scores[0].get("score", 0)
    away_score = scores[1].get("score", 0)

    sel = prediction["selection"]
    market = sel["market_key"]
    outcome = sel["outcome_name"].lower()
    home_name = prediction["match"]["home_team"].lower()
    away_name = prediction["match"]["away_team"].lower()

    if market == "h2h":
        if "draw" in outcome:
            return "won" if home_score == away_score else "lost"

        # Identifier si l'outcome correspond à domicile ou extérieur
        is_home = (outcome in home_name) or (home_name in outcome)
        is_away = (outcome in away_name) or (away_name in outcome)

        if is_home and not is_away:
            return "won" if home_score > away_score else "lost"
        elif is_away and not is_home:
            return "won" if away_score > home_score else "lost"
        else:
            # Ambigu → tenter avec le nom exact du score
            scorer_home = scores[0].get("name", "").lower()
            if outcome in scorer_home or scorer_home in outcome:
                return "won" if home_score > away_score else "lost"
            return "pending"  # Ne pas deviner

    elif market == "totals":
        m = re.search(r"([\d.]+)", outcome)
        if m:
            threshold = float(m.group(1))
            total = home_score + away_score
            if "over" in outcome:
                return "won" if total > threshold else "lost"
            elif "under" in outcome:
                return "won" if total < threshold else "lost"

    return "pending"


def run():
    """Point d'entrée principal de la vérification."""
    pending = load_pending()
    if not pending:
        print("  ℹ Aucun pronostic en attente.")
        return

    now = datetime.now(timezone.utc)
    timeout = timedelta(hours=VERIFICATION_TIMEOUT_HOURS)
    updated = False
    completed_sessions = set()

    # ── Récupérer les scores uniquement pour les ligues concernées ──
    league_keys = get_league_keys_with_pending(pending)
    if league_keys:
        print(f"  📡 Récupération scores pour : {', '.join(league_keys)}")
        scores_by_id = fetch_scores_for_leagues(league_keys, days_from=3)
    else:
        scores_by_id = {}

    # ── Vérifier chaque pronostic en attente ─────────────────────
    for p in pending:
        if p.get("result") not in ("pending", None):
            continue

        created = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00"))

        # Timeout de sécurité
        if now - created > timeout:
            p["result"] = "unverifiable"
            p["verified_at"] = now.isoformat()
            updated = True
            completed_sessions.add(p["session_id"])
            print(f"  ⏰ Timeout : {p['match']['home_team']} vs {p['match']['away_team']}")
            continue

        # Recherche par match_id
        match_id = p.get("match", {}).get("match_id", "")
        score_data = scores_by_id.get(match_id)

        if score_data and score_data.get("completed"):
            result = _determine_result(p, score_data)
            if result in ("won", "lost"):
                p["result"] = result
                p["verified_at"] = now.isoformat()
                updated = True
                completed_sessions.add(p["session_id"])
                icon = "✅" if result == "won" else "❌"
                print(f"  {icon} {p['match']['home_team']} vs {p['match']['away_team']} "
                      f"→ {p['selection']['description']} → {result}")

    if not updated:
        print("  ℹ Aucun nouveau résultat.")
        return

    # ── Mettre à jour l'historique ──────────────────────────────
    history = load_history()
    pending_map = {p["id"]: p for p in pending}
    for hp in history.get("predictions", []):
        if hp["id"] in pending_map:
            updated_p = pending_map[hp["id"]]
            hp["result"] = updated_p["result"]
            hp["verified_at"] = updated_p["verified_at"]
    save_history(history)

    # ── Vérifier les sessions complètes ────────────────────────
    for sid in completed_sessions:
        session_preds = [p for p in pending if p["session_id"] == sid]
        if not session_preds:
            continue

        all_done = all(
            p.get("result") in ("won", "lost", "unverifiable")
            for p in session_preds
        )
        if not all_done:
            continue

        session = {
            "id": sid,
            "type": session_preds[0].get("session_type", "morning"),
            "created_at": session_preds[0]["created_at"],
            "predictions": session_preds,
        }

        msg = format_recap(session)
        send(msg)
        print(f"  📊 Récap session {session['type']} envoyé")

    # ── Nettoyer le pending (supprimer les résolus) ────────────
    remaining = [p for p in pending if p.get("result") in ("pending", None)]
    save_pending(remaining)
    print(f"  ✓ {len(pending) - len(remaining)} pronostics résolus, "
          f"{len(remaining)} restent en attente")
