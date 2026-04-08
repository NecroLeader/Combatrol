"""Consultas a tablas de reglas estáticas (core_*)."""

from app.database import fetch_all, fetch_one


def get_power_level(effective_roll: float) -> int:
    """Devuelve el nivel de potencia (0-8) para una tirada efectiva."""
    row = fetch_one(
        "SELECT power_level FROM core_dice_power "
        "WHERE min_value <= ? AND max_value >= ? LIMIT 1",
        (effective_roll, effective_roll),
    )
    return row["power_level"] if row else 1


def get_difference_band(difference: float) -> str:
    """Devuelve el band_code para una diferencia entre tiradas."""
    row = fetch_one(
        "SELECT band_code FROM core_difference_band "
        "WHERE min_diff <= ? AND max_diff >= ? LIMIT 1",
        (difference, difference),
    )
    return row["band_code"] if row else "BAJA"


def get_power_context(power_p1: int, power_p2: int) -> str:
    if power_p1 >= 5 and power_p2 >= 5:
        return "BOTH_HIGH"
    if power_p1 <= 2 and power_p2 <= 2:
        return "BOTH_LOW"
    if abs(power_p1 - power_p2) >= 4:
        return "MIXED_EXTREME"
    return "BALANCED"


def get_outcome(action_pair: str, diff_band: str, power_context: str) -> list[dict]:
    """
    Consulta outcome_matrix con fallback en cascada:
    1. exacto (pair + band + context)
    2. par + banda (context=DEFAULT)
    3. par default (band=DEFAULT, context=DEFAULT)
    4. genérico
    """
    levels = [
        (action_pair, diff_band,  power_context),
        (action_pair, diff_band,  "DEFAULT"),
        (action_pair, "DEFAULT",  "DEFAULT"),
        ("GENERIC",   "DEFAULT",  "DEFAULT"),
    ]
    for pair, band, ctx in levels:
        rows = fetch_all(
            "SELECT * FROM outcome_matrix "
            "WHERE action_pair=? AND difference_band=? AND power_context=?",
            (pair, band, ctx),
        )
        if rows:
            return rows
    return []


def get_combat_effect(code: str) -> dict | None:
    return fetch_one("SELECT * FROM combat_effects WHERE code=?", (code,))


def get_weapon(code: str) -> dict | None:
    return fetch_one(
        "SELECT w.*, ws.hits, ws.dmg_per_hit, ws.crit_dmg, "
        "ws.dual_allowed, ws.shield_allowed "
        "FROM weapons w JOIN weapon_sizes ws ON w.size_code = ws.size_code "
        "WHERE w.code=?",
        (code,),
    )


def get_random_weapon() -> dict | None:
    return fetch_one(
        "SELECT w.*, ws.hits, ws.dmg_per_hit, ws.crit_dmg "
        "FROM weapons w JOIN weapon_sizes ws ON w.size_code = ws.size_code "
        "ORDER BY RANDOM() LIMIT 1"
    )


def get_random_arena() -> dict | None:
    return fetch_one("SELECT * FROM arena_pool ORDER BY RANDOM() LIMIT 1")


def fetch_one_arena(code: str) -> dict | None:
    return fetch_one("SELECT * FROM arena_pool WHERE code=?", (code,))


def get_state_multipliers(outcome_code: str, active_states: list[str]) -> float:
    """Multiplica el base_weight de un outcome por todos los state_outcome_weights activos."""
    if not active_states:
        return 1.0
    placeholders = ",".join("?" * len(active_states))
    rows = fetch_all(
        f"SELECT multiplier FROM state_outcome_weights "
        f"WHERE outcome_code=? AND state_code IN ({placeholders})",
        tuple([outcome_code] + active_states),
    )
    mult = 1.0
    for r in rows:
        mult *= r["multiplier"]
    return mult
