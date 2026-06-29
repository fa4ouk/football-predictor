"""
Moteur IA Wimbledon - Analyse de cotes de tennis
"""
import json
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, MIN_ODDS, MAX_ODDS


def _build_strategy_tips(stats: dict) -> str:
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
    return f"""Tu es un analyste de cotes de tennis de niveau professionnel, spécialiste absolu du gazon de Wimbledon. Ta mission : sélectionner exactement 5 pronostics simples.

RÈGLES IMPÉRATIVES :
- Exactement 5 pronostics. Ni plus, ni moins.
- Un pronostic = un coupon SIMPLE (1 seule sélection, jamais de combiné).
- Cotes obligatoirement entre {MIN_ODDS} et {MAX_ODDS}.

RÉPARTITION OBLIGATOIRE DES 5 PRONOSTICS :
- 2 pronostics "ULTRA SAFE" chez les HOMMES (ATP Wimbledon)
- 2 pronostics "ULTRA SAFE" chez les FEMMES (WTA Wimbledon)
- 1 pronostic LIBRE (n'importe quel tableau, n'importe quelle catégorie : VALEUR ou OPPORTUNISTE)

CATÉGORIES (assigne exactement l'une des trois) :
- ULTRA SAFE : probabilité >70 %, cote modeste mais très fiable (1.4–1.7). Favori fort sur gazon contre un joueur faible.
- VALEUR : Expected Value positif, la cote est sous-évaluée par le marché (1.7–2.2).
- OPPORTUNISTE : cote plus risquée (2.0–2.5) mais logique solide (ex: handicap de jeux intéressant).

TYPES DE MARCHÉS DISPONIBLES :
- h2h : Victoire d'un joueur
- totals : Over/Under sur le nombre total de JEUX du match (pas de sets)
- spreads : Handicap de jeux (ex: Joueur A -4.5 jeux)

ANALYSE TENNIS ATTENDUE :
- Prends en compte la surface (gazon : service, slice, réception).
- La forme récente du joueur sur gazon.
- Le niveau de l'adversaire.
- Pour les totaux : style de jeu des deux joueurs (serveur-volleyeur vs baseliner).
- Pour les spreads : écart de niveau réaliste entre les deux joueurs.

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
      "home_team": "nom exact joueur 1 (copié des données)",
      "away_team": "nom exact joueur 2 (copié des données)",
      "league": "nom de la compétition",
      "commence_time": "heure du match (ex: 14:00)",
      "market_key": "h2h ou totals ou spreads",
      "selection_description": "ex: Victoire Alcaraz, Plus de 35.5 jeux, Alcaraz -4.5 jeux",
      "outcome_name": "nom exact du outcome dans les données",
      "odds": 1.85,
      "bookmaker": "nom du bookmaker",
      "category": "ULTRA SAFE ou VALEUR ou OPPORTUNISTE",
      "expected_value": 5.2,
      "explanation": "1-2 phrases d'analyse tennis justifiant le choix"
    }}
  ]
}}"""


def analyze(odds_data: list, stats: dict, previous: list = None) -> list:
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
