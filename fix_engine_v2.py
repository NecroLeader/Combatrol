"""
fix_engine_v2.py — Fixes de engine post-audit GDD (2026-04-09)

Qué hace:
1. Corrige duration_phases de CONTRA_EXITOSO y HIPEROFFENSIVO de 0→2
   (con duration=0 expiraban antes de que _sum_mods los pudiera leer en la fase siguiente)
2. Agrega efectos BANDA_*_BONUS (bono de diferencia de banda al ganador de fase)

Ejecutar:
  docker cp fix_engine_v2.py combatrol_app:/app/
  docker exec combatrol_app python /app/fix_engine_v2.py
"""

import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "data/combatrol.db")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ── Fix 1: CONTRA_EXITOSO y HIPEROFFENSIVO duration 0 → 2 ────────────────────
# Con duration=0, expires_at = phase_abs cuando se aplican.
# expire_effects se llama al INICIO de la siguiente fase con el nuevo phase_abs.
# Si el efecto expira_at=N y expire_effects usa "expires_at <= N+1", se elimina.
# Con duration=2, expires_at = N+2 → sobrevive hasta phase N+1 → _sum_mods lo ve.
for code in ('CONTRA_EXITOSO', 'HIPEROFFENSIVO', 'MOMENTUM_OVERFLOW'):
    old = cur.execute("SELECT duration_phases FROM combat_effects WHERE code=?", (code,)).fetchone()
    if old:
        cur.execute("UPDATE combat_effects SET duration_phases=2 WHERE code=?", (code,))
        print(f"  {code}: duration {old['duration_phases']} → 2")
    else:
        print(f"  WARN: {code} not found in combat_effects")

# ── Fix 2: Agregar efectos BANDA_*_BONUS ─────────────────────────────────────
# Bono de diferencia de banda: el ganador de fase recibe modificador temporal
# para la fase siguiente (GDD sección 4).
# duration=2 → expires_at = N+2 → activo durante la fase N+1.
banda_effects = [
    ('BANDA_MODERADA_BONUS', 'Ventaja de Banda Moderada', 2, 'P1', 1, 0, 0, '["momentum","ventaja_banda"]'),
    ('BANDA_REGULAR_BONUS',  'Ventaja de Banda Regular',  2, 'P1', 2, 0, 0, '["momentum","ventaja_banda"]'),
    ('BANDA_ALTA_BONUS',     'Ventaja de Banda Alta',     2, 'P1', 3, 0, 0, '["momentum","ventaja_banda","dominio"]'),
    ('BANDA_MUY_ALTA_BONUS', 'Ventaja de Banda Muy Alta', 2, 'P1', 4, 0, 0, '["momentum","dominio"]'),
    ('BANDA_MAXIMA_BONUS',   'Ventaja de Banda Máxima',   2, 'P1', 5, 0, 0, '["momentum","dominio","aplastante"]'),
    ('BANDA_EXTREMA_BONUS',  'Ventaja de Banda Extrema',  2, 'P1', 6, 0, 0, '["momentum","extremo","aplastante"]'),
]

inserted = 0
for eff in banda_effects:
    exists = cur.execute("SELECT 1 FROM combat_effects WHERE code=?", (eff[0],)).fetchone()
    if not exists:
        cur.execute(
            "INSERT INTO combat_effects "
            "(code, name, duration_phases, applies_to, power_mod, "
            "blocks_next_action, blocks_recovery, narrative_tags) VALUES (?,?,?,?,?,?,?,?)",
            eff
        )
        inserted += 1

print(f"  BANDA effects insertados: {inserted}")

conn.commit()
print("\nFix v2 completado.")
conn.close()
