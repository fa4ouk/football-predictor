"""
Vérification des résultats - Spécialisé Tennis (Wimbledon)
Parse les scores en sets/jeux pour déterminer h2h, totals et spreads.
"""
import re
from datetime import datetime, timezone, timedelta
from odds_client import fetch_scores_for_leagues, get_league_keys_with_pending
from storage import load_pending, save_pending, load_history, save_history
from telegram_bot import send, alert, format_recap
from config import VERIFICATION_TIMEOUT_HOURS


def _parse_tennis_score(score_string: str):
    """
    Parse un score tennis comme "6-4, 7-5, 6-3"
    Retourne : (sets_j1, sets_j2, jeux_j1, jeux_j2)
    """
    sets = score_string.split(", ")
    p1_sets = 0
    p2_sets = 0
    p1_games = 0
    p2_games = 0
    
    for s in sets:
        parts = s.split("-")
        if len(parts) == 2:
            try:
                g1 = int(parts[0].strip())
                g2 = int(parts[1].strip())
                p1_games += g1
                p2_games += g2
                if g1 > g2:
                    p1_sets += 1
                else:
                    p2_sets += 1
            except ValueError:
                continue
                
    return p1_sets, p2_sets, p1_games, p2_games


def _determine_result(prediction: dict, score_data: dict) -> str:
    scores = score_data.get("scores", [])
    if len(scores) < 2:
        return "pending"

    score_str_1 = scores[0].get("score", "")
    if not score_str_1:
        return "pending"

    # scores[0] = Joueur 1 (domicile), scores[1] = Joueur 2 (extérieur)
    p1_sets, p2_sets, p1_games, p2_games = _parse_tennis_score(score_str_1)

    if p1_sets == 0 and p2_sets == 0:
        return "pending"

    sel = prediction["selection"]
    market = sel["market_key"]
    outcome = sel["outcome_name"].lower()
    home_name = prediction["match"]["home_team"].lower()
    away_name = prediction["match"]["away_team"].lower()

    home_won_match = p1_sets > p2_sets
    total_games = p1_games + p2_games
    game_diff = p1_games - p2_games  # positif = J1 domine

    if market == "h2h":
        is_home = (outcome in home_name) or (home_name in outcome)
        is_away = (outcome in away_name) or (away_name in outcome)

        if is_home and not is_away:
            return "won" if home_won_match else "lost"
        elif is_away and not is_home:
            return "won" if not home_won_match else "lost"
        else:
            # Fallback avec le nom du joueur dans les scores
            name1 = scores[0].get("name", "").lower()
            if outcome in name1 or name1 in outcome:
                return "won" if home_won_match else "lost"
            return "pending"

    elif market == "totals":
        m = re.search(r"([\d.]+)", outcome)
        if m:
            threshold = float(m.group(1))
            if "over" in outcome:
                return "won" if total_games > threshold else "lost"
            elif "under" in outcome:
                return "won" if total_games < threshold else "lost"

    elif market == "spreads":
        m = re.search(r"([+-]?[\d.]+)", outcome)
        if m:
            spread_value = float(m.group(1))
            is_home_spread = (outcome in home_name) or (home_name in outcome)

            if is_home_spread:
                # J1 doit gagner par plus que le spread
                return "won" if game_diff > spread_value else "lost"
            else:
                # J2 doit gagner par plus que le spread (game_diff inversé)
                return "won" if (-game_diff) > spread_value else "lost"

    return "pending"


def run():
    pending = load_pending()
    if not pending:
        print("  ℹ Aucun pronostic en attente.")
        return

    now = datetime.now(timezone.utc)
    timeout = timedelta(hours=VERIFICATION_TIMEOUT_HOURS)
    updated = False
    completed_sessions = set()

    league_keys = get_league_keys_with_pending(pending)
    if league_keys:
        print(f"  📡 Récupération scores pour : {', '.join(league_keys)}")
        scores_by_id = fetch_scores_for_leagues(league_keys, days_from=3)
    else:
        scores_by_id = {}

    for p in pending:
        if p.get("result") not in ("pending", None):
            continue

        created = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00"))

        if now - created > timeout:
            p["result"] = "unverifiable"
            p["verified_at"] = now.isoformat()
            updated = True
            completed_sessions.add(p["session_id"])
            print(f"  ⏰ Timeout : {p['match']['home_team']} vs {p['match']['away_team']}")
            continue

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

    history = load_history()
    pending_map = {p["id"]: p for p in pending}
    for hp in history.get("predictions", []):
        if hp["id"] in pending_map:
            updated_p = pending_map[hp["id"]]
            hp["result"] = updated_p["result"]
            hp["verified_at"] = updated_p["verified_at"]
    save_history(history)

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

    remaining = [p for p in pending if p.get("result") in ("pending", None)]
    save_pending(remaining)
    print(f"  ✓ {len(pending) - len(remaining)} pronostics résolus, "
          f"{len(remaining)} restent en attente")
