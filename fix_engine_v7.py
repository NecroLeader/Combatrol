"""
fix_engine_v7.py — Patch live DB con cambios del batch 7 (Análisis 5):
  1. Añade columna narrative_effects_applied a battle_log (si no existe)
  2. Ajusta multiplicadores extremos en state_outcome_weights:
     - VACIO: 5.0 → 3.5
     - CAIDO en fatales EXT_MX: 3.0 → 2.0
     - CAIDO en fatales EXT_BAL: 2.5 → 2.0
     - DESMEMBRADO EXT_MX: 2.5 → 2.0

Correr dentro del container:
  docker cp fix_engine_v7.py combatrol_app:/app/fix_engine_v7.py
  docker exec combatrol_app python /app/fix_engine_v7.py
"""

import sqlite3

DB = "/app/data/combatrol.db"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # ── 1. Añadir columna narrative_effects_applied si no existe ──────────────
    existing = {row[1] for row in cur.execute("PRAGMA table_info(battle_log)")}
    if "narrative_effects_applied" not in existing:
        cur.execute(
            "ALTER TABLE battle_log ADD COLUMN narrative_effects_applied TEXT NOT NULL DEFAULT '[]'"
        )
        print("  battle_log: columna narrative_effects_applied añadida.")
    else:
        print("  battle_log: columna narrative_effects_applied ya existe, skip.")

    # ── 2. Ajustar multiplicadores extremos ───────────────────────────────────

    balance_updates = [
        # VACIO: 5.0 → 3.5
        ("UPDATE state_outcome_weights SET multiplier=3.5 "
         "WHERE state_code='VACIO' AND outcome_code='ATK_INT_EXT_MX_ATAQUE_AL_PRECIPICIO'",),
        ("UPDATE state_outcome_weights SET multiplier=3.5 "
         "WHERE state_code='VACIO' AND outcome_code='INT_ATK_EXT_MX_ATAQUE_AL_PRECIPICIO'",),
        # CAIDO EXT_MX fatales: 3.0 → 2.0
        ("UPDATE state_outcome_weights SET multiplier=2.0 "
         "WHERE state_code='CAIDO' AND multiplier=3.0 AND applies_to='RECEPTOR'",),
        # CAIDO EXT_BAL fatales: 2.5 → 2.0
        ("UPDATE state_outcome_weights SET multiplier=2.0 "
         "WHERE state_code='CAIDO' AND multiplier=2.5 AND applies_to='RECEPTOR'",),
        # DESMEMBRADO EXT_MX: 2.5 → 2.0
        ("UPDATE state_outcome_weights SET multiplier=2.0 "
         "WHERE state_code='DESMEMBRADO' AND multiplier=2.5 AND applies_to='RECEPTOR'",),
    ]

    for (sql,) in balance_updates:
        cur.execute(sql)
        print(f"  {cur.rowcount} rows actualizadas: {sql[:60]}...")

    con.commit()
    con.close()
    print("\nfix_engine_v7 completado.")


if __name__ == "__main__":
    main()
