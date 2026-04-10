"""
fix_engine_v5.py — Batch 5 live-DB patch
=========================================
1. Inserta combat_effects faltantes para estados de entorno
   (ESPACIO_REDUCIDO, VACIO, NIEBLA_EXTREMA, ARMAS_COLGADAS)
2. Actualiza bodega arena para incluir VIDRIO_ROTO en initial_state_tags
3. Inserta nuevos state_outcome_weights (full matrix: HIPEROFFENSIVO fatales,
   CAIDO fatales, DESMEMBRADO extremo, PANICO extremo, POS_FAVORABLE extremo,
   ARMAS_COLGADAS, VIDRIO_ROTO)
4. Inserta narrative templates con required_tags (weapon/arena context)

Seguro para re-ejecutar: INSERT OR IGNORE / UPDATE idempotentes.
"""

import sqlite3
import os

DB_PATH = os.environ.get("COMBATROL_DB", "/app/data/combatrol.db")

NEW_COMBAT_EFFECTS = [
    # (code, name, duration_phases, applies_to, power_mod, blocks_next_action, blocks_recovery, narrative_tags)
    ('ESPACIO_REDUCIDO', 'Espacio Reducido', -1, 'ENTORNO', 0, 0, 0, '["estrecho","claustrofobia"]'),
    ('VACIO',            'Vacío/Precipicio', -1, 'ENTORNO', 0, 0, 0, '["altura","peligro","precipicio"]'),
    ('NIEBLA_EXTREMA',   'Niebla Extrema',   -1, 'ENTORNO', 0, 0, 0, '["niebla","sorpresa","ocultacion"]'),
    ('ARMAS_COLGADAS',   'Armas Colgadas',   -1, 'ENTORNO', 0, 0, 0, '["armas","improvisa","entorno_activo"]'),
]

NEW_STATE_WEIGHTS = [
    # (state_code, outcome_code, multiplier, applies_to)
    # ── ARMAS_COLGADAS ────────────────────────────────────────────────
    ('ARMAS_COLGADAS', 'INT_INT_DEFAULT_A_LOGRA',          1.5, 'BOTH'),
    ('ARMAS_COLGADAS', 'INT_INT_DEFAULT_B_LOGRA',          1.5, 'BOTH'),
    ('ARMAS_COLGADAS', 'ATK_INT_DEFAULT_INT_LOGRA',        1.4, 'BOTH'),
    ('ARMAS_COLGADAS', 'INT_ATK_DEFAULT_INT_LOGRA',        1.4, 'BOTH'),
    # ── VIDRIO_ROTO ───────────────────────────────────────────────────
    ('VIDRIO_ROTO', 'ATK_ATK_ALTA_MX_DOMINIO_A',           1.5, 'BOTH'),
    ('VIDRIO_ROTO', 'ATK_ATK_ALTA_MX_DOMINIO_B',           1.5, 'BOTH'),
    ('VIDRIO_ROTO', 'ATK_DEF_ALTA_MX_DOMINA_A',            1.4, 'BOTH'),
    # ── HIPEROFFENSIVO en fatales del full matrix ─────────────────────
    ('HIPEROFFENSIVO', 'ATK_ATK_EXT_BAL_FATAL_A',          2.5, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_ATK_EXT_BAL_FATAL_B',          2.5, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_ATK_EXT_BH_FATAL_A',           2.0, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_ATK_EXT_BH_FATAL_B',           2.0, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_DEF_EXT_BAL_FATAL_A',          2.5, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_DEF_EXT_MX_FATAL_ESTOCADA',    2.2, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_DEF_EXT_MX_FATAL_HACHAZO',     2.2, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_ATK_MAX_MX_FATAL_ESTOCADA_A',  2.0, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_ATK_EXT_MX_DOMINIO_ABSOLUTO_A',2.0, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_ATK_EXT_MX_DOMINIO_ABSOLUTO_B',2.0, 'ACTOR'),
    ('HIPEROFFENSIVO', 'ATK_DEF_EXT_MX_DEFENSOR_COLAPSADO',1.8, 'ACTOR'),
    # ── CAIDO amplifica fatales sobre el caído ────────────────────────
    ('CAIDO', 'ATK_ATK_EXT_MX_FATAL_REMATE_A',             3.0, 'RECEPTOR'),
    ('CAIDO', 'ATK_ATK_EXT_MX_FATAL_ESTOCADA_A',           3.0, 'RECEPTOR'),
    ('CAIDO', 'ATK_DEF_EXT_MX_FATAL_ESTOCADA',             3.0, 'RECEPTOR'),
    ('CAIDO', 'ATK_DEF_EXT_MX_FATAL_HACHAZO',              3.0, 'RECEPTOR'),
    ('CAIDO', 'ATK_ATK_EXT_BAL_FATAL_A',                   2.5, 'RECEPTOR'),
    ('CAIDO', 'ATK_DEF_EXT_BAL_FATAL_A',                   2.5, 'RECEPTOR'),
    ('CAIDO', 'ATK_ATK_EXT_BH_DOMINIO_A',                  2.0, 'RECEPTOR'),
    # ── DESMEMBRADO en dominio extremo ────────────────────────────────
    ('DESMEMBRADO', 'ATK_ATK_EXT_MX_DOMINIO_ABSOLUTO_A',   2.5, 'RECEPTOR'),
    ('DESMEMBRADO', 'ATK_ATK_EXT_MX_DOMINIO_ABSOLUTO_B',   2.5, 'RECEPTOR'),
    ('DESMEMBRADO', 'ATK_ATK_EXT_BAL_DOMINIO_A',           2.0, 'RECEPTOR'),
    ('DESMEMBRADO', 'ATK_ATK_EXT_BAL_DOMINIO_B',           2.0, 'RECEPTOR'),
    ('DESMEMBRADO', 'ATK_DEF_EXT_MX_DEFENSOR_COLAPSADO',   2.5, 'RECEPTOR'),
    # ── PANICO en dominio extremo ─────────────────────────────────────
    ('PANICO', 'ATK_ATK_ALTA_MX_DOMINIO_A',                1.8, 'RECEPTOR'),
    ('PANICO', 'ATK_ATK_ALTA_MX_DOMINIO_B',                1.8, 'RECEPTOR'),
    ('PANICO', 'ATK_DEF_ALTA_MX_DOMINA_A',                 2.0, 'RECEPTOR'),
    # ── POS_FAVORABLE en dominio extremo ──────────────────────────────
    ('POS_FAVORABLE', 'ATK_ATK_EXT_MX_DOMINIO_ABSOLUTO_A', 2.0, 'ACTOR'),
    ('POS_FAVORABLE', 'ATK_ATK_EXT_MX_DOMINIO_ABSOLUTO_B', 2.0, 'ACTOR'),
    ('POS_FAVORABLE', 'ATK_DEF_EXT_MX_DEFENSOR_COLAPSADO', 1.8, 'ACTOR'),
    ('POS_FAVORABLE', 'ATK_ATK_ALTA_MX_DOMINIO_A',         1.5, 'ACTOR'),
    ('POS_FAVORABLE', 'ATK_ATK_ALTA_MX_DOMINIO_B',         1.5, 'ACTOR'),
]

NEW_NARRATIVE_TEMPLATES = [
    # (pool_tag, template_text, required_tags, excluded_tags, extra_effects, weight)
    # ── pesado ────────────────────────────────────────────────────────
    ('ATK_DEF_IMPACTO_PESADO',
     'El mandoble cae con un impacto devastador. No hay defensa que aguante ese peso.',
     '["pesado"]','[]','[]',1.5),
    ('ATK_DEF_IMPACTO_PESADO_B',
     'La brutalidad del acero pesado aplasta la guardia antes de que el defensor pueda reaccionar.',
     '["pesado"]','[]','[]',1.0),
    ('ATK_ATK_DOMINA_PESADO',
     'El primer golpe aplasta al otro con el puro peso del metal. La fuerza decide.',
     '["pesado"]','[]','[]',1.5),
    ('ATK_DEF_BLOQUEO_PESADO',
     'El defensor aguanta el golpe del mandoble, pero el impacto lo empuja dos pasos hacia atrás.',
     '["pesado"]','[]','[{"target":"RECEPTOR","effect":"POS_DESFAVORABLE","duration_phases":2,"chance":0.3,"source":"narrative"}]',1.2),
    # ── rapido ────────────────────────────────────────────────────────
    ('INT_ATK_INT_LOGRA_RAPIDO',
     'La hoja ágil se mueve antes de que el golpe llegue. Velocidad pura.',
     '["rapido"]','[]','[]',1.5),
    ('ATK_DEF_CONTRA_RAPIDO',
     'La velocidad del contraataque supera la reacción del atacante. La rapidez es el arma.',
     '["rapido"]','[]','[{"target":"ACTOR","effect":"POS_FAVORABLE","duration_phases":2,"chance":0.4,"source":"narrative"}]',1.5),
    ('ATK_ATK_DOMINA_RAPIDO',
     'El acero ágil llega primero. El más rápido siempre gana la iniciativa.',
     '["rapido"]','[]','[]',1.2),
    # ── sigilo ────────────────────────────────────────────────────────
    ('INT_ATK_INT_LOGRA_SIGILO',
     'La daga aparece de la sombra. El atacante no vio el movimiento hasta que ya era tarde.',
     '["sigilo"]','[]','[]',1.5),
    ('ATK_INT_INT_LOGRA_SIGILO',
     'La maniobra sigilosa redirige el ataque sin que el primero sepa cómo lo hicieron.',
     '["sigilo"]','[]','[]',1.3),
    ('INT_DEF_INT_LOGRA_SIGILO',
     'La defensa falla porque no esperaba que la maniobra viniera de ese ángulo oscuro.',
     '["sigilo"]','[]','[{"target":"ACTOR","effect":"POS_FAVORABLE","duration_phases":2,"chance":0.3,"source":"narrative"}]',1.2),
    # ── intimidante ───────────────────────────────────────────────────
    ('ATK_ATK_DOMINA_INTIMIDANTE',
     'El simple hecho de ver esa hoja descender es suficiente para que el oponente dude.',
     '["intimidante"]','[]','[{"target":"RECEPTOR","effect":"VACILACION","duration_phases":2,"chance":0.2,"source":"narrative"}]',1.3),
    ('DEF_ATK_CONTRA_INTIMIDANTE',
     'La defensa sorprende al atacante intimidado por su propio arma. El miedo tiene dos filos.',
     '["intimidante"]','[]','[]',1.2),
    # ── estrecho / claustrofobia ───────────────────────────────────────
    ('INT_INT_A_LOGRA_ESTRECHO',
     'En el espacio apretado, quien se mueve menos es quien tiene ventaja.',
     '["estrecho"]','[]','[]',1.5),
    ('INT_INT_B_LOGRA_ESTRECHO',
     'Las paredes trabajan a favor del segundo. El espacio no perdona movimientos amplios.',
     '["estrecho"]','[]','[]',1.5),
    ('ATK_ATK_INTERCAMBIO_ESTRECHO',
     'Los golpes se cruzan sin margen para esquivar. El espacio no permite más.',
     '["estrecho","claustrofobia"]','[]','[]',1.3),
    ('ATK_DEF_BLOQUEO_ESTRECHO',
     'La defensa se beneficia del espacio comprimido. Hay menos ángulos de ataque posibles.',
     '["estrecho"]','[]','[]',1.2),
    # ── altura / peligro (precipicio) ────────────────────────────────
    ('ATK_DEF_IMPACTO_PRECIPICIO',
     'El golpe empuja hacia el borde. El viento del precipicio es el tercer combatiente.',
     '["peligro","altura"]','[]','[{"target":"RECEPTOR","effect":"POS_DESFAVORABLE","duration_phases":2,"chance":0.35,"source":"narrative"}]',1.5),
    ('INT_INT_CAOS_PRECIPICIO',
     'Los dos maniobran al borde. Un paso en falso termina la batalla de una sola vez.',
     '["altura","peligro"]','[]','[]',1.3),
    ('ATK_ATK_DOMINA_PRECIPICIO',
     'El vencedor acerca al otro al borde. La victoria huele a abismo.',
     '["altura"]','[]','[]',1.2),
    # ── niebla ────────────────────────────────────────────────────────
    ('ATK_ATK_INTERCAMBIO_NIEBLA',
     'En la niebla los golpes llegan de donde no se espera. Nadie sabe quién atacó primero.',
     '["niebla"]','[]','[]',1.5),
    ('INT_ATK_INT_LOGRA_NIEBLA',
     'La niebla oculta la maniobra. El atacante golpea en el vacío.',
     '["niebla","sorpresa"]','[]','[]',1.5),
    ('ATK_DEF_BLOQUEO_NIEBLA',
     'El defensor escucha el golpe antes de verlo. La niebla lo salva por un instante.',
     '["niebla"]','[]','[]',1.2),
    ('DEF_ATK_CONTRA_NIEBLA',
     'En la niebla, la defensa pasiva se convierte en trampa. El contraataque surge de la nada.',
     '["niebla"]','[]','[{"target":"ACTOR","effect":"POS_FAVORABLE","duration_phases":2,"chance":0.3,"source":"narrative"}]',1.3),
    # ── sala_armeria ──────────────────────────────────────────────────
    ('ATK_INT_ATK_PASA_ARMAS',
     'El segundo tropieza con un asta colgada. El primer golpe pasa sin obstáculo.',
     '["armas"]','[]','[]',1.3),
    ('INT_INT_A_LOGRA_ARMAS',
     'El primero usa el entorno a su favor, aprovechando las armas colgadas para redirigir.',
     '["armas","entorno_activo"]','[]','[]',1.2),
    # ── bodega (interior/oscuro) ──────────────────────────────────────
    ('INT_INT_CAOS_OSCURO',
     'En la oscuridad de la bodega, ninguno sabe dónde está el otro. El caos manda.',
     '["interior","oscuro"]','[]','[]',1.4),
    ('ATK_DEF_IMPACTO_PELIGRO_ENTORNO',
     'El impacto hace crujir los estantes. Vidrios caen al suelo complicando cada paso.',
     '["peligro_entorno"]','[]','[]',1.3),
    # ── campo_abierto (exterior) ──────────────────────────────────────
    ('ATK_ATK_DOMINA_EXTERIOR',
     'En campo abierto, el más fuerte impone su ritmo desde el principio sin obstáculos.',
     '["exterior","espacio"]','[]','[]',1.3),
    ('DEF_DEF_REPOSICION_EXTERIOR',
     'El espacio abierto permite el reposicionamiento limpio. Hay margen para respirar.',
     '["exterior"]','[]','[]',1.2),
]


def run():
    print(f"Conectando a {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── 1. combat_effects de entorno ─────────────────────────────────
    ins_ce = 0
    for code, name, dur, at, pm, bna, br, nt in NEW_COMBAT_EFFECTS:
        cur.execute("SELECT 1 FROM combat_effects WHERE code=?", (code,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO combat_effects (code,name,duration_phases,applies_to,power_mod,"
                "blocks_next_action,blocks_recovery,narrative_tags) VALUES (?,?,?,?,?,?,?,?)",
                (code, name, dur, at, pm, bna, br, nt),
            )
            ins_ce += 1
    print(f"combat_effects entorno: {ins_ce} insertadas")

    # ── 2. bodega arena → VIDRIO_ROTO ────────────────────────────────
    cur.execute(
        "UPDATE arena_pool SET initial_state_tags='[\"VIDRIO_ROTO\"]' "
        "WHERE code='bodega' AND initial_state_tags='[]'"
    )
    print(f"bodega initial_state_tags: {cur.rowcount} filas actualizadas")

    # ── 3. state_outcome_weights ─────────────────────────────────────
    ins_sw = 0; sk_sw = 0
    for sc, oc, mult, at in NEW_STATE_WEIGHTS:
        cur.execute(
            "SELECT 1 FROM state_outcome_weights WHERE state_code=? AND outcome_code=?",
            (sc, oc),
        )
        if cur.fetchone():
            sk_sw += 1
        else:
            cur.execute(
                "INSERT INTO state_outcome_weights (state_code,outcome_code,multiplier,applies_to) VALUES (?,?,?,?)",
                (sc, oc, mult, at),
            )
            ins_sw += 1
    print(f"state_outcome_weights: {ins_sw} insertadas, {sk_sw} omitidas")

    # ── 4. narrative templates con required_tags ──────────────────────
    ins_nt = 0; sk_nt = 0
    for pt, txt, rt, et, fx, w in NEW_NARRATIVE_TEMPLATES:
        cur.execute("SELECT 1 FROM narrative_templates WHERE pool_tag=? AND template_text=?", (pt, txt))
        if cur.fetchone():
            sk_nt += 1
        else:
            cur.execute(
                "INSERT INTO narrative_templates (pool_tag,template_text,required_tags,excluded_tags,extra_effects,weight) "
                "VALUES (?,?,?,?,?,?)",
                (pt, txt, rt, et, fx, w),
            )
            ins_nt += 1
    print(f"narrative_templates contextuales: {ins_nt} insertadas, {sk_nt} omitidas")

    conn.commit()
    conn.close()
    print("fix_engine_v5.py completado OK")


if __name__ == "__main__":
    run()
