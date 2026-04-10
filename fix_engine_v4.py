"""
fix_engine_v4.py — Batch 3 live-DB patch
=========================================
Inserta los nuevos state_outcome_weights (FATIGA, VACILACION, PANICO,
HIPEROFFENSIVO, POS_FAVORABLE, POS_DESFAVORABLE, DESARMADO, DESMEMBRADO,
ESPACIO_REDUCIDO, weapon tags) y aplica los extra_effects de narrativa.

Seguro para reejecutar: INSERT OR IGNORE omite filas ya presentes.
Los UPDATE de extra_effects sobrescriben '[]' sin romper nada.
"""

import sqlite3
import os

DB_PATH = os.environ.get("COMBATROL_DB", "/app/data/combatrol.db")

NEW_STATE_WEIGHTS = [
    # (state_code, outcome_code, multiplier, applies_to)
    # ── FATIGA ──────────────────────────────────────────────────────────
    ('FATIGA', 'ATK_ATK_DEFAULT_DOMINA_A',           0.65, 'ACTOR'),
    ('FATIGA', 'ATK_ATK_DEFAULT_DOMINA_B',           0.65, 'ACTOR'),
    ('FATIGA', 'ATK_DEF_DEFAULT_IMPACTO',            0.70, 'ACTOR'),
    ('FATIGA', 'ATK_DEF_DEFAULT_IMPACTO_CONTROLADO', 0.75, 'ACTOR'),
    ('FATIGA', 'ATK_ATK_DEFAULT_VENTAJA_LEVE_A',     0.80, 'ACTOR'),
    ('FATIGA', 'ATK_ATK_DEFAULT_VENTAJA_LEVE_B',     0.80, 'ACTOR'),
    # ── VACILACION ─────────────────────────────────────────────────────
    ('VACILACION', 'ATK_ATK_DEFAULT_DOMINA_A',       0.70, 'ACTOR'),
    ('VACILACION', 'ATK_ATK_DEFAULT_DOMINA_B',       0.70, 'ACTOR'),
    ('VACILACION', 'INT_ATK_DEFAULT_INT_LOGRA',      0.75, 'ACTOR'),
    ('VACILACION', 'INT_DEF_DEFAULT_INT_LOGRA',      0.75, 'ACTOR'),
    # ── PANICO ─────────────────────────────────────────────────────────
    ('PANICO', 'ATK_DEF_DEFAULT_IMPACTO',            2.0,  'RECEPTOR'),
    ('PANICO', 'ATK_DEF_DEFAULT_IMPACTO_CONTROLADO', 1.6,  'RECEPTOR'),
    ('PANICO', 'DEF_ATK_DEFAULT_CONTRA',             1.8,  'ACTOR'),
    ('PANICO', 'DEF_ATK_DEFAULT_BLOQUEO',            1.5,  'ACTOR'),
    # ── HIPEROFFENSIVO ─────────────────────────────────────────────────
    ('HIPEROFFENSIVO', 'ATK_ATK_DEFAULT_DOMINA_A',            2.0, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_ATK_DEFAULT_DOMINA_B',            2.0, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_DEF_DEFAULT_IMPACTO',             1.8, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_DEF_DEFAULT_IMPACTO_CONTROLADO',  1.5, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_ATK_EXT_MX_FATAL_REMATE_A',       1.8, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_ATK_EXT_MX_FATAL_ESTOCADA_A',     1.8, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_DEF_EXT_MX_FATAL_ESTOCADA',       1.8, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_DEF_EXT_MX_FATAL_HACHAZO',        1.8, 'ACTOR'),
    # ── POS_FAVORABLE ──────────────────────────────────────────────────
    ('POS_FAVORABLE', 'ATK_ATK_DEFAULT_DOMINA_A',    1.5, 'ACTOR'),
    ('POS_FAVORABLE', 'ATK_ATK_DEFAULT_DOMINA_B',    1.5, 'ACTOR'),
    ('POS_FAVORABLE', 'INT_ATK_DEFAULT_INT_LOGRA',   1.5, 'ACTOR'),
    ('POS_FAVORABLE', 'INT_DEF_DEFAULT_INT_LOGRA',   1.5, 'ACTOR'),
    ('POS_FAVORABLE', 'DEF_ATK_DEFAULT_CONTRA',      1.3, 'ACTOR'),
    ('POS_FAVORABLE', 'DEF_ATK_DEFAULT_BLOQUEO',     1.3, 'ACTOR'),
    # ── POS_DESFAVORABLE ───────────────────────────────────────────────
    ('POS_DESFAVORABLE', 'ATK_DEF_DEFAULT_IMPACTO',            1.5, 'RECEPTOR'),
    ('POS_DESFAVORABLE', 'ATK_DEF_DEFAULT_IMPACTO_CONTROLADO', 1.3, 'RECEPTOR'),
    ('POS_DESFAVORABLE', 'ATK_ATK_DEFAULT_DOMINA_A',           1.3, 'RECEPTOR'),
    ('POS_DESFAVORABLE', 'ATK_ATK_DEFAULT_DOMINA_B',           1.3, 'RECEPTOR'),
    # ── DESARMADO ──────────────────────────────────────────────────────
    ('DESARMADO', 'ATK_DEF_DEFAULT_IMPACTO',           2.0, 'RECEPTOR'),
    ('DESARMADO', 'ATK_DEF_DEFAULT_IMPACTO_CONTROLADO',1.8, 'RECEPTOR'),
    ('DESARMADO', 'DEF_ATK_DEFAULT_IMPACTO',           2.0, 'RECEPTOR'),
    ('DESARMADO', 'ATK_DEF_EXT_MX_FATAL_ESTOCADA',    2.5, 'RECEPTOR'),
    ('DESARMADO', 'ATK_DEF_EXT_MX_FATAL_HACHAZO',     2.5, 'RECEPTOR'),
    ('DESARMADO', 'ATK_DEF_MAX_MX_FATAL_ESTOCADA',    2.0, 'RECEPTOR'),
    # ── DESMEMBRADO ────────────────────────────────────────────────────
    ('DESMEMBRADO', 'ATK_DEF_DEFAULT_IMPACTO',           2.5, 'RECEPTOR'),
    ('DESMEMBRADO', 'ATK_DEF_DEFAULT_IMPACTO_CONTROLADO',2.0, 'RECEPTOR'),
    ('DESMEMBRADO', 'ATK_ATK_DEFAULT_DOMINA_A',          1.8, 'RECEPTOR'),
    ('DESMEMBRADO', 'ATK_ATK_DEFAULT_DOMINA_B',          1.8, 'RECEPTOR'),
    ('DESMEMBRADO', 'ATK_DEF_EXT_MX_FATAL_ESTOCADA',    3.0, 'RECEPTOR'),
    ('DESMEMBRADO', 'ATK_DEF_EXT_MX_FATAL_HACHAZO',     3.0, 'RECEPTOR'),
    # ── ESPACIO_REDUCIDO ───────────────────────────────────────────────
    ('ESPACIO_REDUCIDO', 'INT_INT_DEFAULT_A_LOGRA',            1.8, 'BOTH'),
    ('ESPACIO_REDUCIDO', 'INT_INT_DEFAULT_B_LOGRA',            1.8, 'BOTH'),
    ('ESPACIO_REDUCIDO', 'INT_INT_DEFAULT_CRUCE_DE_MANIOBRAS', 1.5, 'BOTH'),
    ('ESPACIO_REDUCIDO', 'ATK_ATK_DEFAULT_DOMINA_A',           0.6, 'BOTH'),
    ('ESPACIO_REDUCIDO', 'ATK_ATK_DEFAULT_DOMINA_B',           0.6, 'BOTH'),
    ('ESPACIO_REDUCIDO', 'ATK_ATK_DEFAULT_INTERCAMBIO_BRUSCO', 1.4, 'BOTH'),
    # ── WEAPON TAGS ────────────────────────────────────────────────────
    ('pesado', 'ATK_DEF_DEFAULT_IMPACTO',           1.4, 'ACTOR'),
    ('pesado', 'ATK_DEF_DEFAULT_IMPACTO_CONTROLADO',1.3, 'ACTOR'),
    ('pesado', 'ATK_ATK_DEFAULT_DOMINA_A',          1.3, 'ACTOR'),
    ('pesado', 'ATK_ATK_DEFAULT_DOMINA_B',          1.3, 'ACTOR'),
    ('pesado', 'INT_ATK_DEFAULT_INT_LOGRA',         0.7, 'ACTOR'),
    ('pesado', 'INT_DEF_DEFAULT_INT_LOGRA',         0.7, 'ACTOR'),
    ('rapido', 'INT_ATK_DEFAULT_INT_LOGRA',         1.4, 'ACTOR'),
    ('rapido', 'INT_DEF_DEFAULT_INT_LOGRA',         1.4, 'ACTOR'),
    ('rapido', 'ATK_INT_DEFAULT_ATK_PASA',          1.3, 'ACTOR'),
    ('rapido', 'ATK_ATK_DEFAULT_DOMINA_A',          1.1, 'ACTOR'),
    ('rapido', 'ATK_ATK_DEFAULT_DOMINA_B',          1.1, 'ACTOR'),
    ('intimidante', 'ATK_ATK_DEFAULT_DOMINA_A',     1.3, 'ACTOR'),
    ('intimidante', 'ATK_ATK_DEFAULT_DOMINA_B',     1.3, 'ACTOR'),
    ('intimidante', 'ATK_DEF_DEFAULT_IMPACTO',      1.2, 'ACTOR'),
    ('sigilo', 'INT_ATK_DEFAULT_INT_LOGRA',         1.5, 'ACTOR'),
    ('sigilo', 'ATK_INT_DEFAULT_INT_LOGRA',         1.5, 'ACTOR'),
    ('sigilo', 'INT_DEF_DEFAULT_INT_LOGRA',         1.4, 'ACTOR'),
]

NARRATIVE_EXTRA_EFFECTS = [
    # (pool_tag, extra_effects_json)
    ('DEF_ATK_CONTRA',
     '[{"target":"ACTOR","effect":"POS_FAVORABLE","duration_phases":2,"chance":0.35,"source":"narrative"},{"target":"RECEPTOR","effect":"VACILACION","duration_phases":3,"chance":0.15,"source":"narrative"}]'),
    ('ATK_DEF_CONTRA',
     '[{"target":"ACTOR","effect":"POS_FAVORABLE","duration_phases":2,"chance":0.40,"source":"narrative"}]'),
    ('ATK_DEF_GUARDIA_ROTA',
     '[{"target":"RECEPTOR","effect":"POS_DESFAVORABLE","duration_phases":2,"chance":0.25,"source":"narrative"}]'),
    ('ATK_DEF_CONTRA_EPICO',
     '[{"target":"RECEPTOR","effect":"VACILACION","duration_phases":3,"chance":0.20,"source":"narrative"}]'),
    ('ATK_ATK_CHOQUE_EPICO',
     '[{"target":"ACTOR","effect":"VACILACION","duration_phases":2,"chance":0.12,"source":"narrative"},{"target":"RECEPTOR","effect":"VACILACION","duration_phases":2,"chance":0.12,"source":"narrative"}]'),
]


def run():
    print(f"Conectando a {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── 1. state_outcome_weights ─────────────────────────────────────
    inserted = 0
    skipped = 0
    for sc, oc, mult, at in NEW_STATE_WEIGHTS:
        cur.execute(
            "SELECT 1 FROM state_outcome_weights WHERE state_code=? AND outcome_code=?",
            (sc, oc),
        )
        if cur.fetchone():
            skipped += 1
        else:
            cur.execute(
                "INSERT INTO state_outcome_weights (state_code, outcome_code, multiplier, applies_to) VALUES (?,?,?,?)",
                (sc, oc, mult, at),
            )
            inserted += 1

    print(f"state_outcome_weights: {inserted} insertadas, {skipped} ya existían")

    # ── 2. narrative extra_effects ───────────────────────────────────
    upd = 0
    for pool_tag, fx_json in NARRATIVE_EXTRA_EFFECTS:
        cur.execute(
            "UPDATE narrative_templates SET extra_effects=? WHERE pool_tag=?",
            (fx_json, pool_tag),
        )
        upd += cur.rowcount

    print(f"narrative_templates extra_effects: {upd} filas actualizadas")

    conn.commit()
    conn.close()
    print("fix_engine_v4.py completado OK")


if __name__ == "__main__":
    run()
