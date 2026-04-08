"""IA básica para SIMULATION y PVE. MVP: acción random con sesgo leve."""

import random
from typing import Literal

Action = Literal["ATK", "DEF", "INT"]

# Pesos base: ATK ligeramente preferido para que la IA sea agresiva
_BASE_WEIGHTS = {"ATK": 0.45, "DEF": 0.35, "INT": 0.20}


def choose_action(active_effect_codes: list[str], low_streak: int) -> Action:
    weights = dict(_BASE_WEIGHTS)

    # PANICO bloquea ATK
    if "PANICO" in active_effect_codes:
        weights["ATK"] = 0.0

    # Si está caído, solo INT tiene sentido (aunque el engine lo fuerza igual)
    if "CAIDO" in active_effect_codes:
        weights = {"ATK": 0.1, "DEF": 0.1, "INT": 0.8}

    # Racha baja → más DEF
    if low_streak >= 2:
        weights["DEF"] += 0.15
        weights["ATK"] = max(0.0, weights["ATK"] - 0.15)

    actions = [a for a, w in weights.items() if w > 0]
    w_values = [weights[a] for a in actions]
    return random.choices(actions, weights=w_values, k=1)[0]
