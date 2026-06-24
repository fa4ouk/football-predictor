"""
Moteur IA : construit le prompt, interroge Groq, valide la réponse.
Utilise le mode JSON pour garantir un parsing fiable.
"""
import json
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, MIN_ODDS, MAX_ODDS


def _build_strategy_tips(stats: dict) -> str:
    """Génère des conseils de stratégie basés sur l'historique."""
    tips = []
    cf = stats.get("consecutive_failures", {})
    for key, count in cf.items():
        if count >= 3:
            tips.append(f"🔴 {key} : {count} échecs consécutifs — ÉVITE ce type à tout prix")
        elif count >= 2:
            tips.append(f"🟠 {key} : {count} échecs consécutifs — Sois TRÈS sélectif")
        elif count >= 1:
            tips.append(f"🟡 {key} : 1 échec récent — Reste prudent")

    for cat, s in stats.get("by_category", {}).items():
        if s.get("total", 0) >= 5 and s.get("rate", 100) < 50:
            tips.append(f"🔴 Catégorie {cat} : taux {s['rate']}% — Évite sauf opportunité exceptionnelle")

    for mk, s in stats.get("by_market", {}).items():
        if s.get("total", 0) >= 5 and s.get("rate", 100) < 50:
            tips.append(f"🔴 Marché {mk} : taux {s['rate']}% — Sois plus sélectif")

    return "\n".join(tips) if tips else "Aucun signal d'alerte. Fonctionnement normal."


def _build_previous_block(previous: list) -> str:
    """Bloque décrivant les pronostics déjà faits (pour éviter doublons)."""
    if not previous:
        return ""
    lines = ["\nPRONOSTICS DÉJÀ ÉMIS AUJOURD'HUI (ne pas dupliquer) :"]
    for p in previous:
        lines.append(
            f"  - {p['match']['home_team']} vs {p['match']['away_team']} "
            f"({p['match']['league']}) → {p['selection']['description']}"
        )
    return "\n".join(lines)


def _build_prompt(odds_data: list, stats: dict, previous: list = None) -> str:
    """Construit le prompt complet pour le modèle."""
    return f"""Tu es un analyste de cotes de football de niveau professionnel. Ta mission : sélectionner exactement 5 pronostics simples parmi les matchs ci-dessous.

RÈGLES IMPÉRATIVES :
- Exactement 5 pronostics. Ni plus, ni moins.
- Un pronostic = un coupon SIMPLE (1 seule sélection, jamais de combiné).
- Cotes obligatoirement entre {MIN_ODDS} et {MAX_ODDS}.
- Diversifie les matchs choisis plutôt que de tout miser sur les 2 mêmes rencontres.
- Si les opportunités sont faibles, propose quand même tes 5 meilleurs choix mais sois honnête sur la confiance dans l'explication.

CATÉGORIES (assigne exactement l'une des trois) :
- ULTRA SAFE : probabilité >70 %, cote modeste mais très fiable (souvent 1.4–1.7)
- VALEUR : Expected Value positif détecté, la cote est sous-évaluée par le marché (souvent 1.7–2.2)
- OPPORTUNISTE : cote plus risquée (2.0–2.5) mais avec une logique sportive solide

HISTORIQUE DE PERFORMANCE :
{json.dumps(stats, indent=2, ensure_ascii=False)}

CONSEILS DE STRATÉGIE (générés automatiquement) :
{_build_strategy_tips(stats)}
{_build_previous_block(previous or [])}

MATCHS ET COTES DISPONIBLES :
{json.dumps(odds_data, indent=2, ensure_ascii=False)}

Réponds UNIQUEMENT avec ce JSON valide, ni texte avant ni après :
{{
  "predictions": [
    {{
      "match_id": "id du match",
      "home_team": "nom exact domicile (copié des données)",
      "away_team": "nom exact extérieur (copié des données)",
      "league": "nom de la compétition",
      "commence_time": "date ISO 8601",
      "market_key": "h2h ou totals",
      "selection_description": "ex: Victoire Arsenal, Plus de 2.5 buts, Moins de 3.5 buts",
      "outcome_name": "nom exact du outcome dans les données (ex: Arsenal, Over 2.5, Under 3.5)",
      "odds": 1.85,
      "bookmaker": "nom du bookmaker",
      "category": "ULTRA SAFE ou VALEUR ou OPPORTUNISTE",
      "expected_value": 5.2,
      "explanation": "1-2 phrases d'analyse sportive justifiant le choix"
    }}
  ]
}}"""


def analyze(odds_data: list, stats: dict, previous: list = None) -> list:
    """
    Interroge Groq et retourne la liste des pronostics validés.
    En cas d'erreur, retourne une liste vide.
    """
    client = Groq(api_key=GROQ_API_KEY)

    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": _build_prompt(odds_data, stats, previous)}],
            temperature=0.3,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )
        raw = json.loads(resp.choices[0].message.content)
        preds = raw.get("predictions", [])
    except json.JSONDecodeError as e:
        print(f"  ❌ Erreur de parsing JSON Groq: {e}")
        return []
    except Exception as e:
        print(f"  ❌ Erreur Groq: {e}")
        return []

    # Validation
    valid = []
    for p in preds:
        odds = p.get("odds", 0)
        if not (MIN_ODDS <= odds <= MAX_ODDS):
            print(f"  ⚠ Cote hors plage ignorée: {odds} ({p.get('selection_description', '?')})")
            continue
        if not p.get("match_id") or not p.get("outcome_name"):
            continue
        valid.append(p)

    return valid[:5]
