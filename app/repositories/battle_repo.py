"""CRUD de runtime de batalla."""

from app.database import fetch_one, fetch_all, execute, execute_many


# ── Batalla ──────────────────────────────────────────────────────────────────

def create_battle(mode: str, arena_code: str | None) -> int:
    return execute(
        "INSERT INTO battles (mode, arena_code) VALUES (?, ?)",
        (mode, arena_code),
    )


def get_battle(battle_id: int) -> dict | None:
    return fetch_one("SELECT * FROM battles WHERE id=?", (battle_id,))


def update_battle_turn(battle_id: int, turn: int, phase: int) -> None:
    execute(
        "UPDATE battles SET turn_number=?, phase_number=? WHERE id=?",
        (turn, phase, battle_id),
    )


def finish_battle(battle_id: int, winner_side: str) -> None:
    execute(
        "UPDATE battles SET status='FINISHED', winner_side=?, "
        "finished_at=CURRENT_TIMESTAMP WHERE id=?",
        (winner_side, battle_id),
    )


# ── Estado de combatiente ─────────────────────────────────────────────────────

def create_battle_state(battle_id: int, side: str, weapon_code: str) -> None:
    execute(
        "INSERT INTO battle_state (battle_id, side, weapon_code) VALUES (?,?,?)",
        (battle_id, side, weapon_code),
    )


def get_battle_state(battle_id: int, side: str) -> dict | None:
    return fetch_one(
        "SELECT * FROM battle_state WHERE battle_id=? AND side=?",
        (battle_id, side),
    )


def update_counters(battle_id: int, side: str, new_value: float) -> None:
    execute(
        "UPDATE battle_state SET counters=? WHERE battle_id=? AND side=?",
        (new_value, battle_id, side),
    )


def update_atk_streak(battle_id: int, side: str, streak: int) -> None:
    execute(
        "UPDATE battle_state SET atk_streak=? WHERE battle_id=? AND side=?",
        (streak, battle_id, side),
    )


def block_recovery(battle_id: int, side: str, until_turn: int) -> None:
    execute(
        "UPDATE battle_state SET recovery_blocked_until_turn=? "
        "WHERE battle_id=? AND side=?",
        (until_turn, battle_id, side),
    )


# ── Efectos activos ──────────────────────────────────────────────────────────

def add_effect(battle_id: int, side: str, effect_code: str,
               expires_at_phase: int | None, source: str) -> None:
    execute(
        "INSERT INTO battle_active_effects "
        "(battle_id, side, effect_code, expires_at_phase, source) "
        "VALUES (?,?,?,?,?)",
        (battle_id, side, effect_code, expires_at_phase, source),
    )


def get_active_effects(battle_id: int, side: str) -> list[dict]:
    return fetch_all(
        "SELECT bae.*, ce.narrative_tags "
        "FROM battle_active_effects bae "
        "LEFT JOIN combat_effects ce ON bae.effect_code = ce.code "
        "WHERE bae.battle_id=? AND bae.side=?",
        (battle_id, side),
    )


def get_active_effect_codes(battle_id: int, side: str) -> list[str]:
    rows = get_active_effects(battle_id, side)
    return [r["effect_code"] for r in rows]


def expire_effects(battle_id: int, current_phase_abs: int) -> None:
    """Elimina efectos cuya expires_at_phase ya pasó (excepto permanentes = NULL)."""
    execute(
        "DELETE FROM battle_active_effects "
        "WHERE battle_id=? AND expires_at_phase IS NOT NULL "
        "AND expires_at_phase <= ?",
        (battle_id, current_phase_abs),
    )


def remove_effect(battle_id: int, side: str, effect_code: str) -> None:
    execute(
        "DELETE FROM battle_active_effects "
        "WHERE battle_id=? AND side=? AND effect_code=?",
        (battle_id, side, effect_code),
    )


def has_effect(battle_id: int, side: str, effect_code: str) -> bool:
    row = fetch_one(
        "SELECT id FROM battle_active_effects "
        "WHERE battle_id=? AND side=? AND effect_code=?",
        (battle_id, side, effect_code),
    )
    return row is not None


# ── Acumuladores ─────────────────────────────────────────────────────────────

def create_accumulators(battle_id: int, side: str) -> None:
    execute(
        "INSERT INTO battle_accumulators (battle_id, side) VALUES (?,?)",
        (battle_id, side),
    )


def get_accumulators(battle_id: int, side: str) -> dict | None:
    return fetch_one(
        "SELECT * FROM battle_accumulators WHERE battle_id=? AND side=?",
        (battle_id, side),
    )


def update_accumulators(battle_id: int, side: str, **fields) -> None:
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [battle_id, side]
    execute(
        f"UPDATE battle_accumulators SET {set_clause} "
        f"WHERE battle_id=? AND side=?",
        tuple(values),
    )


# ── Log ──────────────────────────────────────────────────────────────────────

def log_phase(battle_id: int, data: dict) -> None:
    execute(
        "INSERT INTO battle_log "
        "(battle_id, turn_number, phase_number, action_p1, action_p2, "
        "roll_p1, roll_p2, effective_p1, effective_p2, power_p1, power_p2, "
        "difference, difference_band, power_context, action_pair, outcome_code, "
        "phase_winner, roll_winner, counter_dmg_p1, counter_dmg_p2, "
        "counters_p1, counters_p2, effect_applied_p1, effect_applied_p2, "
        "narrative_text) VALUES "
        "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            battle_id,
            data["turn_number"], data["phase_number"],
            data["action_p1"], data["action_p2"],
            data["roll_p1"], data["roll_p2"],
            data["effective_p1"], data["effective_p2"],
            data["power_p1"], data["power_p2"],
            data["difference"], data["difference_band"], data["power_context"],
            data["action_pair"], data["outcome_code"],
            data["phase_winner"], data["roll_winner"],
            data["counter_dmg_p1"], data["counter_dmg_p2"],
            data["counters_p1"], data["counters_p2"],
            data.get("effect_applied_p1"), data.get("effect_applied_p2"),
            data["narrative_text"],
        ),
    )


def get_battle_log(battle_id: int) -> list[dict]:
    return fetch_all(
        "SELECT * FROM battle_log WHERE battle_id=? ORDER BY id",
        (battle_id,),
    )
