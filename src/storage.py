"""
Persistance JSON dans le dossier data/.
Utilisé par GitHub Actions entre les runs (commit/push du repo).
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _ensure():
    os.makedirs(DATA_DIR, exist_ok=True)


def _path(name):
    return os.path.join(DATA_DIR, name)


def load(name, default=None):
    p = _path(name)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return default if default is not None else {}


def save(name, data):
    _ensure()
    with open(_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Raccourcis ───────────────────────────────────────────────

def load_pending():
    return load("pending.json", [])


def save_pending(data):
    save("pending.json", data)


def load_history():
    return load("history.json", {"predictions": [], "sessions": []})


def save_history(data):
    save("history.json", data)


def load_odds_cache():
    return load("odds_cache.json", None)


def save_odds_cache(data):
    save("odds_cache.json", data)


def load_last_predictions():
    return load("last_predictions.json", [])


def save_last_predictions(data):
    save("last_predictions.json", data)
