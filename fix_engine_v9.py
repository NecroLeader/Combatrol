#!/usr/bin/env python3
"""
fix_engine_v9.py — Inserta skills en skill_pool de la DB live.

Cambios:
  1. INSERT OR IGNORE de 10 skills en skill_pool (5 tiers: COMUN → EPICA).
  No modifica state_outcome_weights ni ninguna otra tabla.

Uso: docker exec combatrol_app python /app/fix_engine_v9.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.config import DB_PATH

SKILLS = [
    # (code, name, tier, effect_type, power_mod, duration_phases, special_tags)
    ("RESISTENCIA",        "Resistencia",          "COMUN",       "POWER_MOD",     1, -1, "[]"),
    ("GUARDIA_ALTA",       "Guardia Alta",          "COMUN",       "IMMUNITY",      0, -1, '["POS_DESFAVORABLE"]'),
    ("REFLEJOS",           "Reflejos",              "POCO_COMUN",  "DEBUFF_RESIST", 1, -1, "[]"),
    ("FUERZA_BRUTA",       "Fuerza Bruta",          "POCO_COMUN",  "POWER_MOD",     2, -1, "[]"),
    ("VELOCIDAD",          "Velocidad",             "POCO_COMUN",  "CRIT_BOOST",    1, -1, "[]"),
    ("TEMPLE_ACERO",       "Temple de Acero",       "RARA",        "POWER_MOD",     2, -1, "[]"),
    ("INSTINTO_CAZADOR",   "Instinto del Cazador",  "RARA",        "CRIT_BOOST",    2, -1, "[]"),
    ("MAESTRIA_MARCIAL",   "Maestría Marcial",      "LEGENDARIA",  "POWER_MOD",     3, -1, "[]"),
    ("VOLUNTAD_INDOMABLE", "Voluntad Indomable",    "LEGENDARIA",  "IMMUNITY",      0, -1, '["PANICO","VACILACION"]'),
    ("BERSERKER",          "Berserker",             "EPICA",       "POWER_MOD",     4, -1, "[]"),
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Insertar skills
    inserted = 0
    for row in SKILLS:
        cur = conn.execute(
            "INSERT OR IGNORE INTO skill_pool "
            "(code, name, tier, effect_type, power_mod, duration_phases, special_tags) "
            "VALUES (?,?,?,?,?,?,?)",
            row,
        )
        inserted += cur.rowcount

    conn.commit()

    # Verificar
    total = conn.execute("SELECT COUNT(*) FROM skill_pool").fetchone()[0]
    by_tier = conn.execute(
        "SELECT tier, COUNT(*) as n FROM skill_pool GROUP BY tier ORDER BY tier"
    ).fetchall()

    conn.close()

    print(f"fix_engine_v9 completado.")
    print(f"  Skills insertadas: {inserted} / {len(SKILLS)} (ya existían: {len(SKILLS)-inserted})")
    print(f"  Total en skill_pool: {total}")
    for r in by_tier:
        print(f"    {r['tier']}: {r['n']}")


if __name__ == "__main__":
    main()
