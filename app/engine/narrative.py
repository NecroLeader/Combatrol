"""Selección de narrativa por tags activos."""

import json
import random
from app.database import fetch_all


def select_narrative(pool_tag: str, active_tags: list[str]) -> str:
    """
    Busca templates con pool_tag dado, filtra por required/excluded tags,
    selecciona uno por peso. Devuelve el texto o un fallback genérico.
    """
    rows = fetch_all(
        "SELECT * FROM narrative_templates WHERE pool_tag=?",
        (pool_tag,),
    )
    if not rows:
        # Buscar genérico
        rows = fetch_all(
            "SELECT * FROM narrative_templates WHERE pool_tag='GENERIC_INTERCAMBIO'"
        )

    candidates = []
    for row in rows:
        required = json.loads(row["required_tags"] or "[]")
        excluded = json.loads(row["excluded_tags"] or "[]")

        if any(tag not in active_tags for tag in required):
            continue
        if any(tag in active_tags for tag in excluded):
            continue

        candidates.append((row["template_text"], row["weight"]))

    if not candidates:
        return "El intercambio se resuelve sin consecuencias claras."

    texts, weights = zip(*candidates)
    return random.choices(texts, weights=weights, k=1)[0]


def collect_active_tags(active_effects: list[dict], weapon_tags: list[str],
                        arena_tags: list[str]) -> list[str]:
    """Consolida todos los tags activos para filtrado de narrativa."""
    tags = list(weapon_tags) + list(arena_tags)
    for effect in active_effects:
        try:
            effect_tags = json.loads(effect.get("narrative_tags", "[]") or "[]")
            tags.extend(effect_tags)
        except (json.JSONDecodeError, TypeError):
            pass
    return list(set(tags))
