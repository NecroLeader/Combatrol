"""Endpoint liviano para polling de Arduino/ESP32."""

from fastapi import APIRouter, HTTPException
from app.repositories import battle_repo as repo

router = APIRouter(prefix="/hw_state", tags=["hardware"])


@router.get("/{battle_id}")
def hw_state(battle_id: int) -> dict:
    """
    JSON mínimo para Arduino WiFi. Optimizado para payloads chicos.
    Polling sugerido: cada 500ms-1s.
    """
    battle = repo.get_battle(battle_id)
    if not battle:
        raise HTTPException(status_code=404, detail="Not found")

    s1 = repo.get_battle_state(battle_id, "P1")
    s2 = repo.get_battle_state(battle_id, "P2")
    e1 = repo.get_active_effect_codes(battle_id, "P1")
    e2 = repo.get_active_effect_codes(battle_id, "P2")

    # Último entry del log
    log = repo.get_battle_log(battle_id)
    last = log[-1] if log else {}

    return {
        "bid":  battle_id,
        "st":   battle["status"],           # IN_PROGRESS | FINISHED
        "win":  battle.get("winner_side"),  # P1 | P2 | null
        "t":    battle["turn_number"],
        "ph":   battle["phase_number"],
        "p1":  {"cnt": s1["counters"] if s1 else 0, "fx": e1},
        "p2":  {"cnt": s2["counters"] if s2 else 0, "fx": e2},
        "last": {
            "oc":  last.get("outcome_code", ""),
            "nar": last.get("narrative_text", ""),
            "dmg": [last.get("counter_dmg_p1", 0), last.get("counter_dmg_p2", 0)],
        },
    }
