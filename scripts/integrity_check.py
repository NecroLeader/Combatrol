#!/usr/bin/env python3
"""
Checker de integridad de datos de Combatrol.
Detecta referencias rotas y JSON inválidos antes de que rompan en runtime.

Uso: python scripts/integrity_check.py
Salida: lista de issues con nivel OK / WARN / ERROR.
Exit code: 0 si todo OK, 1 si hay ERRORs.
"""

import sys
import json
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import DB_PATH


def check(db_path: str = DB_PATH) -> bool:
    """Retorna True si todo OK, False si hay errores."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    issues = []

    # ── 1. state_outcome_weights → outcome_matrix ─────────────────────────────
    orphan_weights = conn.execute("""
        SELECT DISTINCT sow.state_code, sow.outcome_code
        FROM state_outcome_weights sow
        LEFT JOIN outcome_matrix om ON sow.outcome_code = om.outcome_code
        WHERE om.outcome_code IS NULL
    """).fetchall()
    for row in orphan_weights:
        issues.append(("ERROR", f"state_outcome_weights: outcome_code '{row['outcome_code']}' "
                                f"(estado '{row['state_code']}') no existe en outcome_matrix"))

    # ── 2. outcome_matrix effect_A / effect_B → combat_effects ────────────────
    orphan_effects = conn.execute("""
        SELECT outcome_code, effect_A, effect_B
        FROM outcome_matrix
        WHERE (effect_A IS NOT NULL AND effect_A NOT IN (SELECT code FROM combat_effects))
           OR (effect_B IS NOT NULL AND effect_B NOT IN (SELECT code FROM combat_effects))
    """).fetchall()
    for row in orphan_effects:
        if row["effect_A"] and row["effect_A"] not in _get_codes(conn):
            issues.append(("ERROR", f"outcome_matrix '{row['outcome_code']}': "
                                    f"effect_A '{row['effect_A']}' no existe en combat_effects"))
        if row["effect_B"] and row["effect_B"] not in _get_codes(conn):
            issues.append(("ERROR", f"outcome_matrix '{row['outcome_code']}': "
                                    f"effect_B '{row['effect_B']}' no existe en combat_effects"))

    # ── 3. JSON inválidos en narrative_templates ───────────────────────────────
    templates = conn.execute(
        "SELECT id, pool_tag, required_tags, excluded_tags, extra_effects FROM narrative_templates"
    ).fetchall()
    for t in templates:
        for field in ("required_tags", "excluded_tags", "extra_effects"):
            val = t[field]
            if not val:
                continue
            try:
                json.loads(val)
            except json.JSONDecodeError as e:
                issues.append(("ERROR", f"narrative_templates id={t['id']} pool_tag='{t['pool_tag']}': "
                                        f"JSON inválido en {field}: {e}"))

    # ── 4. combat_effects refs en arena_pool initial_state_tags ───────────────
    arenas = conn.execute("SELECT code, initial_state_tags FROM arena_pool").fetchall()
    effect_codes = _get_codes(conn)
    for arena in arenas:
        raw = arena["initial_state_tags"]
        if not raw:
            continue
        try:
            tags = json.loads(raw)
            for tag in tags:
                if tag not in effect_codes:
                    issues.append(("WARN", f"arena_pool '{arena['code']}': "
                                           f"initial_state_tag '{tag}' no existe en combat_effects"))
        except json.JSONDecodeError as e:
            issues.append(("ERROR", f"arena_pool '{arena['code']}': JSON inválido en initial_state_tags: {e}"))

    # ── 5. extra_effects en narrative_templates → combat_effects ──────────────
    for t in templates:
        val = t["extra_effects"]
        if not val:
            continue
        try:
            effs = json.loads(val)
            for e in effs:
                code = e.get("effect")
                if code and code not in effect_codes:
                    issues.append(("WARN", f"narrative_templates id={t['id']} pool_tag='{t['pool_tag']}': "
                                           f"extra_effect.effect '{code}' no existe en combat_effects"))
                target = e.get("target", "")
                if target not in ("ACTOR", "RECEPTOR", "P1", "P2", "ENTORNO", "NONE"):
                    issues.append(("WARN", f"narrative_templates id={t['id']}: "
                                           f"target desconocido '{target}'"))
        except (json.JSONDecodeError, TypeError):
            pass  # ya capturado arriba

    # ── 6. Estadísticas de cobertura ──────────────────────────────────────────
    total_outcomes = conn.execute("SELECT COUNT(*) FROM outcome_matrix").fetchone()[0]
    outcomes_with_weights = conn.execute(
        "SELECT COUNT(DISTINCT outcome_code) FROM state_outcome_weights"
    ).fetchone()[0]
    outcomes_with_narrative = conn.execute(
        "SELECT COUNT(DISTINCT narrative_pool_tag) FROM outcome_matrix"
    ).fetchone()[0]
    total_templates = conn.execute("SELECT COUNT(*) FROM narrative_templates").fetchone()[0]
    total_weights = conn.execute("SELECT COUNT(*) FROM state_outcome_weights").fetchone()[0]

    conn.close()

    # ── Reporte ────────────────────────────────────────────────────────────────
    errors = [i for i in issues if i[0] == "ERROR"]
    warns  = [i for i in issues if i[0] == "WARN"]

    print("=" * 60)
    print("COMBATROL — INTEGRITY CHECK")
    print("=" * 60)
    print(f"  outcome_matrix: {total_outcomes} rows")
    print(f"  state_outcome_weights: {total_weights} rows ({outcomes_with_weights} outcomes únicos)")
    print(f"  narrative_templates: {total_templates} rows ({outcomes_with_narrative} pool_tags únicos)")
    print()

    if not issues:
        print("✓ Todo OK — sin referencias rotas ni JSON inválidos.")
    else:
        for level, msg in issues:
            prefix = "✗ ERROR" if level == "ERROR" else "⚠ WARN "
            print(f"  {prefix}: {msg}")

    print()
    print(f"Resultado: {len(errors)} ERROR(es), {len(warns)} WARN(s)")
    print("=" * 60)

    return len(errors) == 0


def _get_codes(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT code FROM combat_effects").fetchall()
    return {r["code"] for r in rows}


if __name__ == "__main__":
    ok = check()
    sys.exit(0 if ok else 1)
