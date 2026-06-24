"""
Calcul des statistiques de performance à partir de l'historique.
Utilisé pour alimenter le prompt IA et ajuster la stratégie.
"""


def compute(history: dict) -> dict:
    preds = history.get("predictions", [])
    resolved = [p for p in preds if p.get("result") in ("won", "lost")]

    won = sum(1 for p in resolved if p["result"] == "won")
    lost = len(resolved) - won
    pending = sum(1 for p in preds if p.get("result") in ("pending", None, "unverifiable"))

    stats = {
        "total_predictions": len(preds),
        "total_won": won,
        "total_lost": lost,
        "total_pending": pending,
        "overall_rate": round(won / len(resolved) * 100, 1) if resolved else 0,
        "by_category": {},
        "by_market": {},
        "consecutive_failures": {},
        "warnings": [],
    }

    # Par catégorie
    for cat in ("ULTRA SAFE", "VALEUR", "OPPORTUNISTE"):
        subset = [p for p in resolved if p.get("category") == cat]
        w = sum(1 for p in subset if p["result"] == "won")
        stats["by_category"][cat] = {
            "total": len(subset),
            "won": w,
            "lost": len(subset) - w,
            "rate": round(w / len(subset) * 100, 1) if subset else 0,
        }

    # Par marché
    markets = {p.get("market_key", "?") for p in preds}
    for mk in sorted(markets):
        subset = [p for p in resolved if p.get("market_key") == mk]
        w = sum(1 for p in subset if p["result"] == "won")
        stats["by_market"][mk] = {
            "total": len(subset),
            "won": w,
            "lost": len(subset) - w,
            "rate": round(w / len(subset) * 100, 1) if subset else 0,
        }

    # Échecs consécutifs par catégorie ET par marché
    track_keys = list(stats["by_category"].keys()) + list(stats["by_market"].keys())
    for key in track_keys:
        count = 0
        for p in reversed(preds):
            r = p.get("result")
            if r == "lost":
                matches = (
                    (key in ("ULTRA SAFE", "VALEUR", "OPPORTUNISTE") and p.get("category") == key)
                    or p.get("market_key") == key
                )
                if matches:
                    count += 1
                else:
                    break
            elif r == "won":
                break
        stats["consecutive_failures"][key] = count

    # Warnings
    for cat, s in stats["by_category"].items():
        if s["total"] >= 5 and s["rate"] < 50:
            stats["warnings"].append(f"{cat} : taux {s['rate']}% (< 50 %)")
    for key, c in stats["consecutive_failures"].items():
        if c >= 2:
            stats["warnings"].append(f"{key} : {c} échecs consécutifs")

    return stats
