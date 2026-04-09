"""
fix_engine_v3.py — Corrige referencias muertas en state_outcome_weights.

Problema: state_outcome_weights apunta a outcome_codes que no existen en
outcome_matrix. Esto hace que los multiplicadores de CAIDO (×2.5) y VACIO
(×5.0) nunca disparen.

NO volver a aplicar si ya fue ejecutado.
"""

import sqlite3

DB = "/app/data/combatrol.db"


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # ── 1. Diagnóstico ────────────────────────────────────────────────────────
    print("=== DIAGNÓSTICO: referencias muertas en state_outcome_weights ===")
    cur.execute("""
        SELECT sow.state_code, sow.outcome_code, sow.multiplier
        FROM state_outcome_weights sow
        WHERE sow.outcome_code NOT IN (
            SELECT DISTINCT outcome_code FROM outcome_matrix
        )
        ORDER BY sow.state_code, sow.outcome_code
    """)
    dead = cur.fetchall()
    if not dead:
        print("No se encontraron referencias muertas. ¿Ya fue aplicado el fix?")
        con.close()
        return

    for row in dead:
        print(f"  MUERTO: state={row['state_code']} | outcome={row['outcome_code']} | mult={row['multiplier']}")

    # ── 2. Mapeo de correcciones ──────────────────────────────────────────────
    # Para cada referencia muerta definimos:
    #   - nueva_outcome_code (reemplaza la muerta)
    #   - outcomes_extra: filas adicionales a insertar (para mapear 1-a-muchos)
    #
    # CAIDO (×2.5): fatal ATK outcomes reales
    #   ATK_ATK_EXT_MX_FATAL_CHOQUE → ATK_ATK_MAX_MX_FATAL_ESTOCADA_A
    #   + agregar también ATK_ATK_EXT_MX_FATAL_REMATE_A
    #
    # VACIO (×5.0): precipicio outcomes reales
    #   FATAL_CAIDA_VACIO → ATK_INT_EXT_MX_ATAQUE_AL_PRECIPICIO
    #   + agregar también INT_ATK_EXT_MX_ATAQUE_AL_PRECIPICIO

    # (state_code, dead_outcome_code): (new_outcome_code, [extra_outcomes], applies_to)
    FIXES = {
        ("CAIDO", "ATK_ATK_EXT_MX_FATAL_CHOQUE"): (
            "ATK_ATK_MAX_MX_FATAL_ESTOCADA_A",
            ["ATK_ATK_EXT_MX_FATAL_REMATE_A"],
            "RECEPTOR",
        ),
        ("VACIO", "FATAL_CAIDA_VACIO"): (
            "ATK_INT_EXT_MX_ATAQUE_AL_PRECIPICIO",
            ["INT_ATK_EXT_MX_ATAQUE_AL_PRECIPICIO"],
            "BOTH",
        ),
    }

    # ── 3. Verificar que los outcomes destino existen ─────────────────────────
    print("\n=== Verificando outcomes destino ===")
    all_targets = set()
    for (sc, dead_oc), (new_oc, extras, applies_to) in FIXES.items():
        all_targets.add(new_oc)
        all_targets.update(extras)

    missing_targets = []
    for oc in all_targets:
        cur.execute("SELECT 1 FROM outcome_matrix WHERE outcome_code=? LIMIT 1", (oc,))
        if not cur.fetchone():
            missing_targets.append(oc)
            print(f"  ERROR: outcome destino no existe en outcome_matrix: {oc}")
        else:
            print(f"  OK: {oc}")

    if missing_targets:
        print("\nABORTANDO: falta al menos un outcome destino en outcome_matrix.")
        con.close()
        return

    # ── 4. Aplicar correcciones ───────────────────────────────────────────────
    print("\n=== Aplicando correcciones ===")
    changes = 0

    for (state_code, dead_oc), (new_oc, extras, applies_to) in FIXES.items():
        # Verificar que la fila muerta existe (puede haber duplicados — tomamos el primero)
        cur.execute(
            "SELECT id, multiplier FROM state_outcome_weights "
            "WHERE state_code=? AND outcome_code=? LIMIT 1",
            (state_code, dead_oc),
        )
        row = cur.fetchone()
        if not row:
            print(f"  SKIP: ({state_code}, {dead_oc}) — fila no encontrada (¿ya corregida?)")
            continue

        mult = row["multiplier"]

        # Eliminar TODAS las filas muertas duplicadas para este par (state, dead_oc)
        cur.execute(
            "DELETE FROM state_outcome_weights WHERE state_code=? AND outcome_code=?",
            (state_code, dead_oc),
        )
        deleted = cur.rowcount
        print(f"  DELETE: {deleted} fila(s) ({state_code}, {dead_oc})")
        changes += deleted

        # INSERT el primer outcome real (reemplaza la fila muerta)
        cur.execute(
            "SELECT 1 FROM state_outcome_weights WHERE state_code=? AND outcome_code=?",
            (state_code, new_oc),
        )
        if cur.fetchone():
            print(f"  SKIP INSERT: ({state_code}, {new_oc}) — ya existe")
        else:
            cur.execute(
                "INSERT INTO state_outcome_weights "
                "(state_code, outcome_code, multiplier, applies_to) VALUES (?,?,?,?)",
                (state_code, new_oc, mult, applies_to),
            )
            print(f"  INSERT: ({state_code}, {new_oc}) mult={mult} applies_to={applies_to}")
            changes += 1

        # INSERT filas extra si corresponde
        for extra_oc in extras:
            cur.execute(
                "SELECT 1 FROM state_outcome_weights "
                "WHERE state_code=? AND outcome_code=?",
                (state_code, extra_oc),
            )
            if cur.fetchone():
                print(f"  SKIP INSERT: ({state_code}, {extra_oc}) — ya existe")
                continue
            cur.execute(
                "INSERT INTO state_outcome_weights "
                "(state_code, outcome_code, multiplier, applies_to) VALUES (?,?,?,?)",
                (state_code, extra_oc, mult, applies_to),
            )
            print(f"  INSERT: ({state_code}, {extra_oc}) mult={mult} applies_to={applies_to}")
            changes += 1

    con.commit()
    print(f"\nTotal cambios: {changes}")

    # ── 5. Verificación final ─────────────────────────────────────────────────
    print("\n=== Verificación final ===")
    cur.execute("""
        SELECT sow.state_code, sow.outcome_code, sow.multiplier
        FROM state_outcome_weights sow
        WHERE sow.outcome_code NOT IN (
            SELECT DISTINCT outcome_code FROM outcome_matrix
        )
    """)
    remaining = cur.fetchall()
    if remaining:
        print(f"  ADVERTENCIA: quedan {len(remaining)} refs muertas:")
        for r in remaining:
            print(f"    state={r['state_code']} | outcome={r['outcome_code']}")
    else:
        print("  OK: 0 referencias muertas restantes.")

    # Mostrar filas CAIDO y VACIO activas
    print("\n=== state_outcome_weights para CAIDO y VACIO (post-fix) ===")
    cur.execute(
        "SELECT state_code, outcome_code, multiplier FROM state_outcome_weights "
        "WHERE state_code IN ('CAIDO','VACIO') ORDER BY state_code, outcome_code"
    )
    for r in cur.fetchall():
        print(f"  {r['state_code']} | {r['outcome_code']} | ×{r['multiplier']}")

    con.close()
    print("\nfix_engine_v3.py completado.")


if __name__ == "__main__":
    main()
