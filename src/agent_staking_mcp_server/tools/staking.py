"""
MCP-Tools fuer Agent Reputation Staking.
Implementiert Stake-Deposit, Verify, Reputation-Score, Slash, Dispute und Leaderboard.
"""

import time
from typing import Any

from agent_staking_mcp_server import store


def stake_deposit(agent_id: str, amount: float, currency: str = "REP") -> dict[str, Any]:
    """
    Hinterlegt einen Stake fuer einen Agent als Vertrauensbeweis.

    Je hoeher der Stake, desto vertrauenswuerdiger gilt der Agent
    in der Agent-Economy.
    """
    if amount <= 0:
        return {"success": False, "error": "Stake-Betrag muss groesser als 0 sein"}

    if not agent_id or len(agent_id.strip()) == 0:
        return {"success": False, "error": "Agent-ID darf nicht leer sein"}

    stake = store.deposit_stake(agent_id.strip(), amount, currency)

    return {
        "success": True,
        "agent_id": stake["agent_id"],
        "new_balance": stake["balance"],
        "currency": stake["currency"],
        "total_deposited": stake["total_deposited"],
        "trust_tier": _get_trust_tier(stake["balance"]),
        "message": f"Stake von {amount} {currency} fuer {agent_id} hinterlegt",
    }


def stake_verify(agent_id: str) -> dict[str, Any]:
    """
    Prueft den Stake-Status und Trust-Level eines Agents.

    Gibt Stake-Balance, Trust-Tier und Slash-Historie zurueck.
    """
    stake = store.get_stake(agent_id.strip())

    if not stake:
        return {
            "agent_id": agent_id,
            "has_stake": False,
            "balance": 0.0,
            "trust_tier": "unverified",
            "message": "Kein Stake gefunden — Agent gilt als nicht verifiziert",
        }

    data = store.get_store()
    # Slash-Events fuer diesen Agent zaehlen
    slash_count = sum(1 for e in data["slash_events"] if e["agent_id"] == agent_id)

    return {
        "agent_id": stake["agent_id"],
        "has_stake": True,
        "balance": stake["balance"],
        "currency": stake["currency"],
        "total_deposited": stake["total_deposited"],
        "total_slashed": stake["total_slashed"],
        "slash_events": slash_count,
        "trust_tier": _get_trust_tier(stake["balance"]),
        "trust_score": _calc_trust_score(stake),
        "status": stake["status"],
        "member_since": stake["created_at"],
    }


def reputation_by_stake(agent_id: str) -> dict[str, Any]:
    """
    Berechnet einen stake-gewichteten Reputations-Score fuer einen Agent.

    Kombiniert Stake-Groesse, Slash-Historie und Mitgliedsdauer
    zu einem Gesamtscore (0-100).
    """
    stake = store.get_stake(agent_id.strip())

    if not stake:
        return {
            "agent_id": agent_id,
            "reputation_score": 0,
            "grade": "F",
            "message": "Kein Stake vorhanden — keine Reputation berechenbar",
        }

    score = _calc_trust_score(stake)
    grade = _score_to_grade(score)

    # Detaillierte Aufschluesselung
    balance_score = min(50, stake["balance"] / 10)  # max 50 Punkte fuer Balance
    slash_penalty = min(30, stake["total_slashed"] * 2)  # bis zu 30 Punkte Abzug
    longevity_days = (time.time() - stake["created_at"]) / 86400
    longevity_score = min(20, longevity_days * 2)  # max 20 Punkte fuer Dauer

    return {
        "agent_id": agent_id,
        "reputation_score": round(score, 1),
        "grade": grade,
        "breakdown": {
            "stake_balance_score": round(balance_score, 1),
            "slash_penalty": round(slash_penalty, 1),
            "longevity_score": round(longevity_score, 1),
        },
        "stake_balance": stake["balance"],
        "currency": stake["currency"],
        "trust_tier": _get_trust_tier(stake["balance"]),
        "recommendation": _get_recommendation(grade),
    }


def slash_stake(agent_id: str, slash_amount: float, reason: str) -> dict[str, Any]:
    """
    Schlaegt einen Stake-Slash fuer einen Agent vor (bei schlechtem Verhalten).

    Reduziert die Stake-Balance als Strafe. Der Slash wird protokolliert
    und ist dauerhaft in der Slash-Historie sichtbar.
    """
    if slash_amount <= 0:
        return {"success": False, "error": "Slash-Betrag muss groesser als 0 sein"}

    stake = store.get_stake(agent_id.strip())
    if not stake:
        return {"success": False, "error": f"Agent {agent_id} hat keinen Stake"}

    result = store.slash_stake(agent_id.strip(), slash_amount, reason)

    if "error" in result:
        return {"success": False, "error": result["error"]}

    return {
        "success": True,
        "agent_id": agent_id,
        "slashed_amount": result["slash_event"]["amount"],
        "reason": reason,
        "remaining_balance": result["stake"]["balance"],
        "new_trust_tier": _get_trust_tier(result["stake"]["balance"]),
        "message": f"Stake von {agent_id} um {result['slash_event']['amount']} reduziert",
    }


def dispute_open(claimant_id: str, defendant_id: str, description: str, stake_at_risk: float = 0.0) -> dict[str, Any]:
    """
    Oeffnet einen Streitfall zwischen zwei Agents.

    Wenn der Beklagte verliert, wird sein Stake entsprechend geslasht.
    """
    if not claimant_id or not defendant_id:
        return {"success": False, "error": "Klaeger und Beklagter muessen angegeben werden"}

    if claimant_id == defendant_id:
        return {"success": False, "error": "Klaeger und Beklagter koennen nicht identisch sein"}

    dispute = store.open_dispute(
        claimant_id.strip(), defendant_id.strip(), description, stake_at_risk
    )

    return {
        "success": True,
        "dispute_id": dispute["dispute_id"],
        "claimant": dispute["claimant"],
        "defendant": dispute["defendant"],
        "description": dispute["description"],
        "stake_at_risk": dispute["amount_at_stake"],
        "status": dispute["status"],
        "created_at": dispute["created_at"],
        "message": f"Dispute {dispute['dispute_id']} eroeffnet",
    }


def dispute_resolve(dispute_id: str, winner_id: str, resolution_notes: str) -> dict[str, Any]:
    """
    Loest einen offenen Streitfall auf.

    Wenn der Klaeger gewinnt, wird der Stake des Beklagten automatisch
    um den strittigen Betrag geslasht.
    """
    result = store.resolve_dispute(dispute_id.strip(), winner_id.strip(), resolution_notes)

    if "error" in result:
        return {"success": False, "error": result["error"]}

    return {
        "success": True,
        "dispute_id": result["dispute_id"],
        "winner": result.get("winner"),
        "resolution": result["resolution"],
        "status": result["status"],
        "stake_slashed": result.get("winner") == result["claimant"] and result["amount_at_stake"] > 0,
        "amount_slashed": result["amount_at_stake"] if result.get("winner") == result["claimant"] else 0,
        "message": f"Dispute {dispute_id} aufgeloest. Gewinner: {winner_id}",
    }


def stake_leaderboard(top_n: int = 10) -> dict[str, Any]:
    """
    Gibt die top-gestaketen Agents zurueck (Vertrauens-Rangliste).

    Sortiert nach Stake-Balance und Trust-Score — die vertrauenswuerdigsten
    Agents zuerst.
    """
    all_stakes = store.get_all_stakes()

    if not all_stakes:
        return {
            "leaderboard": [],
            "total_agents": 0,
            "message": "Noch keine gestaketen Agents",
        }

    # Nach Trust-Score sortieren
    ranked = sorted(all_stakes, key=lambda x: _calc_trust_score(x), reverse=True)
    top = ranked[:top_n]

    entries = []
    for i, stake in enumerate(top, 1):
        entries.append({
            "rank": i,
            "agent_id": stake["agent_id"],
            "balance": stake["balance"],
            "currency": stake["currency"],
            "trust_score": round(_calc_trust_score(stake), 1),
            "trust_tier": _get_trust_tier(stake["balance"]),
            "total_slashed": stake["total_slashed"],
        })

    total_staked = sum(s["balance"] for s in all_stakes)

    return {
        "leaderboard": entries,
        "total_agents": len(all_stakes),
        "total_staked": round(total_staked, 2),
        "currency": all_stakes[0]["currency"] if all_stakes else "REP",
    }


# ---- Hilfsfunktionen ----

def _get_trust_tier(balance: float) -> str:
    """Bestimmt das Trust-Tier basierend auf der Stake-Balance."""
    if balance <= 0:
        return "unverified"
    elif balance < 10:
        return "bronze"
    elif balance < 50:
        return "silver"
    elif balance < 200:
        return "gold"
    else:
        return "platinum"


def _calc_trust_score(stake: dict) -> float:
    """Berechnet einen Trust-Score (0-100) aus den Stake-Daten."""
    balance_score = min(50, stake["balance"] / 10)
    slash_penalty = min(30, stake["total_slashed"] * 2)
    longevity_days = (time.time() - stake["created_at"]) / 86400
    longevity_score = min(20, longevity_days * 2)
    return max(0, balance_score - slash_penalty + longevity_score)


def _score_to_grade(score: float) -> str:
    """Wandelt einen Numerik-Score in eine Schulnote um."""
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "F"


def _get_recommendation(grade: str) -> str:
    """Gibt eine Empfehlung basierend auf der Note zurueck."""
    recommendations = {
        "A+": "Hoechste Vertrauenswuerdigkeit — ideal fuer Hochrisiko-Transaktionen",
        "A": "Sehr vertrauenswuerdig — empfohlen fuer die meisten Agent-Kooperationen",
        "B": "Vertrauenswuerdig — geeignet fuer Standard-Transaktionen",
        "C": "Maessige Vertrauenswuerdigkeit — Vorsicht bei kritischen Operationen",
        "D": "Niedrige Vertrauenswuerdigkeit — nur fuer unkritische Aufgaben",
        "F": "Nicht vertrauenswuerdig — Interaktion nicht empfohlen",
    }
    return recommendations.get(grade, "Unbekannte Bewertung")
