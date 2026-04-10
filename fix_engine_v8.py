"""
fix_engine_v8.py — Patch live DB con cambios del batch 8 (Análisis 6):
  1. Deduplicar state_outcome_weights (conservar la fila con MAX(id) por combinación)
  2. Crear UNIQUE INDEX en state_outcome_weights(state_code, outcome_code, applies_to)
  3. Corregir DESMEMBRADO EXT_MX_FATAL 3.0 → 2.0
  4. Corregir CAIDO MAX_MX_FATAL 2.5 → 2.0 (si aún está)

Correr dentro del container:
  docker cp fix_engine_v8.py combatrol_app:/app/fix_engine_v8.py
  docker exec combatrol_app python /app/fix_engine_v8.py
"""

import sqlite3

DB = "/app/data/combatrol.db"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # ── 1. Verificar duplicados antes ─────────────────────────────────────────
    dups = cur.execute("""
        SELECT state_code, outcome_code, applies_to, COUNT(*) as cnt
        FROM state_outcome_weights
        GROUP BY state_code, outcome_code, applies_to
        HAVING cnt > 1
    """).fetchall()
    print(f"  Duplicados encontrados antes: {len(dups)}")
    for row in dups:
        print(f"    ({row[0]}, {row[1]}, {row[2]}) × {row[3]}")

    # ── 2. Deduplicar (conservar fila con MAX(id) = el valor más reciente) ────
    cur.execute("""
        DELETE FROM state_outcome_weights
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM state_outcome_weights
            GROUP BY state_code, outcome_code, applies_to
        )
    """)
    print(f"  Filas eliminadas por deduplicación: {cur.rowcount}")

    # ── 3. Crear UNIQUE INDEX ─────────────────────────────────────────────────
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_sow_unique
        ON state_outcome_weights(state_code, outcome_code, applies_to)
    """)
    print("  UNIQUE INDEX creado en state_outcome_weights.")

    # ── 4. Corregir multipliers residuales ────────────────────────────────────
    cur.execute("""
        UPDATE state_outcome_weights SET multiplier=2.0
        WHERE state_code='DESMEMBRADO'
          AND outcome_code IN ('ATK_DEF_EXT_MX_FATAL_ESTOCADA','ATK_DEF_EXT_MX_FATAL_HACHAZO')
          AND multiplier > 2.0
    """)
    print(f"  DESMEMBRADO EXT_MX_FATAL corregidos: {cur.rowcount}")

    cur.execute("""
        UPDATE state_outcome_weights SET multiplier=2.0
        WHERE state_code='CAIDO'
          AND outcome_code='ATK_ATK_MAX_MX_FATAL_ESTOCADA_A'
          AND multiplier > 2.0
    """)
    print(f"  CAIDO MAX_MX_FATAL_ESTOCADA_A corregidos: {cur.rowcount}")

    # ── 5. Verificar resultado ────────────────────────────────────────────────
    dups_after = cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT state_code, outcome_code, applies_to
            FROM state_outcome_weights
            GROUP BY state_code, outcome_code, applies_to
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    total = cur.execute("SELECT COUNT(*) FROM state_outcome_weights").fetchone()[0]
    print(f"  Duplicados restantes: {dups_after}")
    print(f"  Total filas: {total}")

    con.commit()
    con.close()
    print("\nfix_engine_v8 completado.")


if __name__ == "__main__":
    main()
