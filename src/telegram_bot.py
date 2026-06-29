"""
Envoi de messages Telegram - Version Wimbledon
"""
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def send(text: str) -> bool:
    try:
        r = requests.post(_BASE, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=30)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"  ❌ Erreur Telegram: {e}")
        return False


def alert(error: str):
    send(
        f"🚨 <b>ALERTTE AGENT WIMBLEDON</b>\n\n"
        f"❌ {error}\n\n"
        f"<i>Consultez les logs GitHub Actions pour le détail.</i>"
    )


_CAT_EMOJI = {"ULTRA SAFE": "🛡️", "VALEUR": "💎", "OPPORTUNISTE": "🎯"}
_RES_EMOJI = {"won": "✅", "lost": "❌", "unverifiable": "❓", "pending": "⏳"}


def format_predictions(predictions: list, session_type: str) -> str:
    icon = "🌅" if session_type == "morning" else "🌆"
    label = "MATIN" if session_type == "morning" else "SOIR"
    date_str = predictions[0]["created_at"][:10] if predictions else "?"

    lines = [
        f"🎾 <b>PRONOSTICS WIMBLEDON — {label}</b>",
        f"📅 {date_str}",
        "─" * 28,
    ]
    for i, p in enumerate(predictions, 1):
        ce = _CAT_EMOJI.get(p.get("category", ""), "📌")
        lines += [
            "",
            f"<b>#{i}  {ce} {p.get('category', 'N/A')}</b>",
            f"🎾 {p['match']['home_team']} vs {p['match']['away_team']}",
            f"🏆 {p['match']['league']}",
            f"🕐 {p['match']['commence_time'][11:16]} UTC",
            f"🎯 {p['selection']['description']}",
            f"💰 Cote : <b>{p['odds']:.2f}</b> ({p['bookmaker']})",
            f"📊 EV estimé : <b>+{p.get('expected_value', '?')}%</b>",
            f"💡 {p.get('explanation', '')}",
        ]
    lines += [
        "",
        "─" * 28,
        "⚡ Coupons simples — 1 sélection par coupon",
        "⚠️ Jouer responsablement",
    ]
    return "\n".join(lines)


def format_recap(session: dict) -> str:
    preds = session.get("predictions", [])
    won = sum(1 for p in preds if p.get("result") == "won")
    lost = sum(1 for p in preds if p.get("result") == "lost")
    unver = sum(1 for p in preds if p.get("result") == "unverifiable")
    resolved = won + lost
    rate = round(won / resolved * 100, 1) if resolved else 0

    icon = "🟢" if rate >= 60 else ("🟡" if rate >= 40 else "🔴")
    label = "MATIN" if session.get("type") == "morning" else "SOIR"

    lines = [
        f"📊 <b>RÉCAP SESSION WIMBLEDON {label}</b>",
        f"📅 {session.get('created_at', '?')[:10]}",
        "─" * 28,
        "",
        f"{icon} <b>Résultat : {won}/{resolved} ({rate} %)</b>",
        "",
    ]
    for i, p in enumerate(preds, 1):
        r = p.get("result", "pending")
        re = _RES_EMOJI.get(r, "❓")
        lines += [
            f"{re} #{i} {p['selection']['description']}",
            f"   {p['match']['home_team']} vs {p['match']['away_team']}",
            f"   Cote {p['odds']:.2f} → <b>{r.upper()}</b>",
        ]
        if r == "unverifiable":
            lines.append("   ⚠️ Non vérifiable (délai dépassé ou source indisponible)")
        lines.append("")

    if unver:
        lines.append(f"⚠️ {unver} coupon(s) n'ont pas pu être vérifiés.")
    lines.append("─" * 28)
    return "\n".join(lines)
