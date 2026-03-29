"""
Persistenter In-Memory-Store fuer Staking-Daten.
Nutzt eine JSON-Datei im Home-Verzeichnis als persistenten Speicher.
"""

import json
import os
import time
from pathlib import Path
from typing import Any

# Datei fuer persistente Speicherung
DATA_FILE = Path.home() / ".agent_staking_store.json"


def _load() -> dict[str, Any]:
    """Laedt den Store von der JSON-Datei."""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"stakes": {}, "disputes": {}, "slash_events": []}


def _save(data: dict[str, Any]) -> None:
    """Speichert den Store in die JSON-Datei."""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def get_store() -> dict[str, Any]:
    """Gibt den gesamten Store zurueck."""
    return _load()


def deposit_stake(agent_id: str, amount: float, currency: str = "REP") -> dict[str, Any]:
    """Hinterlegt oder erhoeht den Stake eines Agents."""
    data = _load()
    stakes = data["stakes"]

    if agent_id not in stakes:
        stakes[agent_id] = {
            "agent_id": agent_id,
            "balance": 0.0,
            "currency": currency,
            "total_deposited": 0.0,
            "total_slashed": 0.0,
            "created_at": time.time(),
            "updated_at": time.time(),
            "status": "active",
        }

    stakes[agent_id]["balance"] += amount
    stakes[agent_id]["total_deposited"] += amount
    stakes[agent_id]["updated_at"] = time.time()

    _save(data)
    return stakes[agent_id]


def get_stake(agent_id: str) -> dict[str, Any] | None:
    """Gibt den Stake eines Agents zurueck."""
    data = _load()
    return data["stakes"].get(agent_id)


def get_all_stakes() -> list[dict[str, Any]]:
    """Gibt alle Stakes zurueck."""
    data = _load()
    return list(data["stakes"].values())


def slash_stake(agent_id: str, amount: float, reason: str) -> dict[str, Any]:
    """Reduziert den Stake eines Agents (Slash-Mechanismus)."""
    data = _load()
    stakes = data["stakes"]

    if agent_id not in stakes:
        return {"error": f"Agent {agent_id} hat keinen Stake"}

    # Stake reduzieren (nicht unter 0)
    actual_slash = min(amount, stakes[agent_id]["balance"])
    stakes[agent_id]["balance"] -= actual_slash
    stakes[agent_id]["total_slashed"] += actual_slash
    stakes[agent_id]["updated_at"] = time.time()

    # Slash-Event protokollieren
    slash_event = {
        "agent_id": agent_id,
        "amount": actual_slash,
        "reason": reason,
        "timestamp": time.time(),
        "remaining_balance": stakes[agent_id]["balance"],
    }
    data["slash_events"].append(slash_event)

    _save(data)
    return {"stake": stakes[agent_id], "slash_event": slash_event}


def open_dispute(claimant: str, defendant: str, description: str, amount: float = 0.0) -> dict[str, Any]:
    """Oeffnet einen Streitfall zwischen zwei Agents."""
    data = _load()
    dispute_id = f"dispute_{int(time.time())}_{claimant[:8]}"

    dispute = {
        "dispute_id": dispute_id,
        "claimant": claimant,
        "defendant": defendant,
        "description": description,
        "amount_at_stake": amount,
        "status": "open",
        "created_at": time.time(),
        "resolved_at": None,
        "resolution": None,
    }
    data["disputes"][dispute_id] = dispute

    _save(data)
    return dispute


def resolve_dispute(dispute_id: str, winner: str, resolution: str) -> dict[str, Any]:
    """Loest einen Streitfall auf."""
    data = _load()

    if dispute_id not in data["disputes"]:
        return {"error": f"Dispute {dispute_id} nicht gefunden"}

    dispute = data["disputes"][dispute_id]
    if dispute["status"] != "open":
        return {"error": f"Dispute {dispute_id} ist bereits {dispute['status']}"}

    dispute["status"] = "resolved"
    dispute["resolved_at"] = time.time()
    dispute["winner"] = winner
    dispute["resolution"] = resolution

    # Wenn der Klaeger gewinnt: Slash den Beklagten
    if winner == dispute["claimant"] and dispute["amount_at_stake"] > 0:
        slash_stake(dispute["defendant"], dispute["amount_at_stake"], f"Dispute lost: {dispute_id}")

    _save(data)
    return dispute
