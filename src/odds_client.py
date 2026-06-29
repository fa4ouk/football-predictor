"""
Client pour The Odds API — Version Ultra-Compacte Wimbledon
"""
import requests
from datetime import datetime, timezone, timedelta
from config import (
    ODDS_API_KEY, ODDS_API_BASE, LEAGUES,
    MARKETS, MATCHES_LOOKAHEAD_HOURS
)


def _get(league_key: str, endpoint: str, extra_params: dict = None) -> list:
    url = f"{ODDS_API_BASE}/sports/{league_key}/{endpoint}/"
    params = {"api_key": ODDS_API_KEY}
    if extra_params:
        params.update(extra_params)
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        remaining = r.headers.get("x-requests-remaining", "?")
        data = r.json()
        results = data if isinstance(data, list) else data.get("data", [])
        print(f"  [{league_key}] {endpoint} → {len(results)} résultats (reste: {remaining} req)")
        return results
    except requests.HTTPError as e:
        print(f"  [{league_key}] ERREUR HTTP {e.response.status_code}")
        return []
    except Exception as e:
        print(f"  [{league_key}] ERREUR: {e}")
        return []


def fetch_odds_all_leagues() -> list:
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=MATCHES_LOOKAHEAD_HOURS)
    all_matches = []

    for league_key, league_name in LEAGUES.items():
        raw = _get(league_key, "odds", {
            "regions": "eu,uk,us",
            "markets": MARKETS,
            "oddsFormat": "decimal",
        })
        for m in raw:
            try:
                commence = datetime.fromisoformat(m["commence_time"].replace("Z", "+00:00"))
            except (ValueError, KeyError):
                continue
            if now < commence < cutoff:
                m["_league"] = league_name
                m["_league_key"] = league_key
                all_matches.append(m)

    print(f"  ✓ {len(all_matches)} matchs avec cotes dans la fenêtre")
    return all_matches


def format_odds_for_ai(matches: list) -> list:
    """
    Format ULTRA COMPACT pour diviser le nombre de tokens par 10.
    Ex: {"h2h": {"Alcaraz": 1.40, "Djokovic": 2.80}, "totals": {"Over 35.5": 1.90}}
    """
    formatted = []
    for m in matches:
        best = {}
        for bm in m.get("bookmakers", []):
            for mk in bm.get("markets", []):
                key = mk["key"]
                if key not in best:
                    best[key] = {}
                for o in mk.get("outcomes", []):
                    name = o["name"]
                    price = o.get("price", 0)
                    if name not in best[key] or price > best[key][name]:
                        best[key][name] = price

        if best:
            formatted.append({
                "id": m["id"],
                "home": m["home_team"],
                "away": m["away_team"],
                "league": m.get("_league", "?"),
                "time": m["commence_time"][11:16],
                "odds": best
            })
            
    return formatted


def fetch_scores_for_leagues(league_keys: list, days_from: int = 3) -> dict:
    scores_by_id = {}
    for lk in league_keys:
        raw = _get(lk, "scores", {"daysFrom": days_from})
        for m in raw:
            if m.get("completed") and m.get("scores"):
                scores_by_id[m["id"]] = m
    return scores_by_id


def get_league_keys_with_pending(pending: list) -> list:
    keys = set()
    for p in pending:
        if p.get("result") in ("pending", None):
            lk = p.get("match", {}).get("league_key")
            if lk:
                keys.add(lk)
    return list(keys)
