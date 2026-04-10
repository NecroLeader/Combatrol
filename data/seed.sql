-- ============================================================
-- SEED DATA — Combatrol
-- Rangos de potencia: FUENTE Excel "Roll and Fight.xlsx"
-- ============================================================

-- Potencia (rangos del Excel, NO del starter original)
INSERT OR IGNORE INTO core_dice_power (min_value, max_value, power_level, label) VALUES
(-99, 0,  0, 'COLAPSO'),
(1,   5,  1, 'P1'),
(6,   9,  2, 'P2'),
(10,  13, 3, 'P3'),
(14,  16, 4, 'P4'),
(17,  19, 5, 'P5'),
(20,  20, 6, 'P6'),
(21,  22, 7, 'LÍMITE'),
(23,  99, 8, 'TRANSCENDENTE');

-- Bandas de diferencia (7 niveles del Excel)
INSERT OR IGNORE INTO core_difference_band (min_diff, max_diff, band_code, bono_value) VALUES
(0,  3,  'BAJA',     0),
(4,  7,  'MODERADA', 1),
(8,  10, 'REGULAR',  2),
(11, 13, 'ALTA',     3),
(14, 16, 'MUY_ALTA', 4),
(17, 19, 'MAXIMA',   5),
(20, 999,'EXTREMA',  6);

-- ============================================================
-- TAMAÑOS DE ARMA
-- ============================================================

INSERT OR IGNORE INTO weapon_sizes (size_code, hits, dmg_per_hit, crit_dmg, dual_allowed, shield_allowed) VALUES
('PEQUEÑA', 2, 0.5, 1.0, 1, 1),
('MEDIANA', 1, 1.0, 2.0, 1, 1),
('GRANDE',  1, 1.5, 4.0, 0, 0);

-- Armas base (del Excel hoja 2: Espada=MEDIANA, Mandoble=GRANDE, Daga=PEQUEÑA)
INSERT OR IGNORE INTO weapons (code, name, size_code, narrative_tags) VALUES
('espada',   'Espada',   'MEDIANA', '["filo","rapido","equilibrado"]'),
('mandoble', 'Mandoble', 'GRANDE',  '["filo","pesado","dos_manos","intimidante"]'),
('daga',     'Daga',     'PEQUEÑA', '["filo","rapido","sigilo","dual_natural"]');

-- ============================================================
-- ESTADOS DE COMBATE
-- ============================================================

INSERT OR IGNORE INTO combat_effects
    (code, name, duration_phases, applies_to, power_mod, blocks_next_action, blocks_recovery, narrative_tags)
VALUES
('CAIDO',           'Caído',                 0,  'P1',     0,  1, 0, '["suelo","vulnerable","sin_accion"]'),
('DESARMADO',       'Desarmado',             -1, 'P1',    -3,  0, 0, '["sin_arma","desesperado"]'),
('ARMA_ROTA',       'Arma Rota',             -1, 'P1',    -2,  0, 0, '["improvisa","fragil"]'),
('DESMEMBRADO',     'Desmembrado',           -1, 'P1',    -5,  0, 1, '["herida_grave","agonia"]'),
-- duration=2: expires_at=N+2 → sobrevive expire_effects(N+1) → _sum_mods lo lee en fase N+1
('CONTRA_EXITOSO',  'Contraataque Exitoso',   2, 'P1',    +4,  0, 0, '["momentum","contraataque"]'),
('POS_FAVORABLE',   'Posición Favorable',    -1, 'P1',    +3,  0, 0, '["ventaja_posicional"]'),
('POS_DESFAVORABLE','Posición Desfavorable', -1, 'P1',    -3,  0, 0, '["mala_posicion"]'),
('FATIGA',          'Fatiga',                 3, 'P1',    -3,  0, 0, '["agotado","lento"]'),
('VACILACION',      'Vacilación',             6, 'P1',    -2,  0, 0, '["miedo","duda","retroceso"]'),
('PANICO',          'Pánico',                 3, 'P1',    -3,  1, 0, '["panico","supervivencia"]'),
-- duration=2: idem CONTRA_EXITOSO (se aplica explícito con expires_at+2 en _apply_effect)
('HIPEROFFENSIVO',  'Hiper Ofensivo',         2, 'P1',    +5,  0, 0, '["rabia","impulso","oportunidad"]'),
('VIDRIO_ROTO',     'Vidrio Roto',            9, 'ENTORNO',0,  0, 0, '["peligro_entorno","cautela"]'),
('IMPROVISA',       'Improvisa',             -1, 'P1',     0,  0, 0, '["improvisa","sin_arma_formal"]'),
-- duration=2: el valor real va en source="overflow:X.X"; expira vía remove+add en _roll_dice
('MOMENTUM_OVERFLOW','Momentum Overflow',     2, 'P1',     0,  0, 0, '["racha","overflow"]'),
-- Bonos de banda: ganador de fase recibe +power_mod para la siguiente fase (GDD §4)
('BANDA_MODERADA_BONUS', 'Ventaja Banda Moderada', 2, 'P1', 1, 0, 0, '["momentum","ventaja_banda"]'),
('BANDA_REGULAR_BONUS',  'Ventaja Banda Regular',  2, 'P1', 2, 0, 0, '["momentum","ventaja_banda"]'),
('BANDA_ALTA_BONUS',     'Ventaja Banda Alta',     2, 'P1', 3, 0, 0, '["momentum","ventaja_banda","dominio"]'),
('BANDA_MUY_ALTA_BONUS', 'Ventaja Banda Muy Alta', 2, 'P1', 4, 0, 0, '["momentum","dominio"]'),
('BANDA_MAXIMA_BONUS',   'Ventaja Banda Máxima',   2, 'P1', 5, 0, 0, '["momentum","dominio","aplastante"]'),
('BANDA_EXTREMA_BONUS',  'Ventaja Banda Extrema',  2, 'P1', 6, 0, 0, '["momentum","extremo","aplastante"]');

-- ============================================================
-- ARENA BASE
-- ============================================================

INSERT OR IGNORE INTO arena_pool (code, name, initial_state_tags, fatal_multiplier_base, narrative_tags) VALUES
('campo_abierto',   'Campo Abierto',       '[]',                         1.0, '["exterior","espacio","luz"]'),
('sala_armeria',    'Sala de Armería',     '["ARMAS_COLGADAS"]',         1.2, '["interior","armas","madera"]'),
('precipicio',      'Borde del Precipicio','["VACIO"]',                  3.0, '["altura","viento","peligro"]'),
('bodega',          'Bodega',              '[]',                         1.3, '["interior","oscuro","vidrios"]'),
('espacio_reducido','Espacio Reducido',    '["ESPACIO_REDUCIDO"]',       1.5, '["estrecho","claustrofobia"]'),
('niebla',          'Campo con Niebla',    '["NIEBLA_EXTREMA"]',         2.0, '["niebla","sorpresa","exterior"]');

-- Lanzables por arena
INSERT OR IGNORE INTO arena_throwables (arena_code, object_code, object_name, type, weight) VALUES
('campo_abierto',    'piedra',    'Piedra',        'LIGERO', 1.0),
('campo_abierto',    'rama',      'Rama',          'MEDIO',  0.7),
('sala_armeria',     'daga_col',  'Daga Colgada',  'LIGERO', 1.0),
('sala_armeria',     'espada_col','Espada Colgada','MEDIO',  0.8),
('precipicio',       'piedra_p',  'Piedra',        'LIGERO', 1.0),
('bodega',           'botella',   'Botella',       'LIGERO', 1.0),
('bodega',           'cajon',     'Cajón',         'PESADO', 0.6),
('espacio_reducido', 'escombro',  'Escombro',      'LIGERO', 0.8);

-- ============================================================
-- OUTCOME MATRIX — Fallbacks MVP
-- (Las ~130 entradas específicas se importan desde outcome_matrix_seed.csv)
-- ============================================================

-- Fallback genérico global (último recurso)
INSERT OR IGNORE INTO outcome_matrix
    (action_pair, difference_band, power_context, outcome_code, phase_winner,
     counter_dmg_A, counter_dmg_B, effect_A, effect_B, base_weight, narrative_pool_tag, is_fatal)
VALUES
('GENERIC','DEFAULT','DEFAULT','GENERIC_INTERCAMBIO_NEUTRO','NONE', 0.5, 0.5, NULL, NULL, 0.7, 'GENERIC_INTERCAMBIO', 0),
('GENERIC','DEFAULT','DEFAULT','GENERIC_VENTAJA_LEVE','A',           0.0, 0.5, NULL, NULL, 0.3, 'GENERIC_VENTAJA_LEVE', 0);

-- Fallbacks de par (uno por par, aplican si no hay entrada específica)
INSERT OR IGNORE INTO outcome_matrix
    (action_pair, difference_band, power_context, outcome_code, phase_winner,
     counter_dmg_A, counter_dmg_B, effect_A, effect_B, base_weight, narrative_pool_tag, is_fatal)
VALUES
-- ATK_ATK default
('ATK_ATK','DEFAULT','DEFAULT','ATK_ATK_DEFAULT_INTERCAMBIO','NONE', 0.5, 0.5, NULL, NULL, 0.6,'ATK_ATK_INTERCAMBIO',0),
('ATK_ATK','DEFAULT','DEFAULT','ATK_ATK_DEFAULT_DOMINA_A','A',       0.0, 1.0, NULL, NULL, 0.3,'ATK_ATK_DOMINA',0),
('ATK_ATK','DEFAULT','DEFAULT','ATK_ATK_DEFAULT_DOMINA_B','B',       1.0, 0.0, NULL, NULL, 0.1,'ATK_ATK_DOMINA',0),
-- ATK_DEF default
('ATK_DEF','DEFAULT','DEFAULT','ATK_DEF_DEFAULT_BLOQUEO','B',        0.0, 0.5, NULL, NULL, 0.5,'ATK_DEF_BLOQUEO',0),
('ATK_DEF','DEFAULT','DEFAULT','ATK_DEF_DEFAULT_IMPACTO','A',        0.0, 1.0, NULL, NULL, 0.4,'ATK_DEF_IMPACTO',0),
('ATK_DEF','DEFAULT','DEFAULT','ATK_DEF_DEFAULT_CONTRA','B',         0.5, 0.0, 'POS_DESFAVORABLE','CONTRA_EXITOSO', 0.1,'ATK_DEF_CONTRA',0),
-- DEF_ATK default (mirror de ATK_DEF, A=defensor B=atacante)
('DEF_ATK','DEFAULT','DEFAULT','DEF_ATK_DEFAULT_BLOQUEO','A',        0.5, 0.0, NULL, NULL, 0.5,'DEF_ATK_BLOQUEO',0),
('DEF_ATK','DEFAULT','DEFAULT','DEF_ATK_DEFAULT_IMPACTO','B',        1.0, 0.0, NULL, NULL, 0.4,'DEF_ATK_IMPACTO',0),
('DEF_ATK','DEFAULT','DEFAULT','DEF_ATK_DEFAULT_CONTRA','A',         0.0, 0.5, 'CONTRA_EXITOSO','POS_DESFAVORABLE',0.1,'DEF_ATK_CONTRA',0),
-- DEF_DEF default
('DEF_DEF','DEFAULT','DEFAULT','DEF_DEF_DEFAULT_REPOSICION','A',     0.0, 0.0, 'POS_FAVORABLE','POS_DESFAVORABLE',0.5,'DEF_DEF_REPOSICION',0),
('DEF_DEF','DEFAULT','DEFAULT','DEF_DEF_DEFAULT_ESPERA','NONE',      0.0, 0.0, NULL, NULL, 0.5,'DEF_DEF_ESPERA',0),
-- ATK_INT default (A ataca, B intenta INT)
('ATK_INT','DEFAULT','DEFAULT','ATK_INT_DEFAULT_ATK_PASA','A',       0.0, 0.5, NULL, NULL, 0.5,'ATK_INT_ATK_PASA',0),
('ATK_INT','DEFAULT','DEFAULT','ATK_INT_DEFAULT_INT_LOGRA','B',      0.5, 0.0, NULL,'POS_FAVORABLE',0.4,'ATK_INT_INT_LOGRA',0),
('ATK_INT','DEFAULT','DEFAULT','ATK_INT_DEFAULT_AMBOS','NONE',       0.5, 0.5, NULL, NULL, 0.1,'ATK_INT_AMBOS',0),
-- INT_ATK default (A intenta INT, B ataca)
('INT_ATK','DEFAULT','DEFAULT','INT_ATK_DEFAULT_ATK_PASA','B',       0.5, 0.0, NULL, NULL, 0.5,'INT_ATK_ATK_PASA',0),
('INT_ATK','DEFAULT','DEFAULT','INT_ATK_DEFAULT_INT_LOGRA','A',      0.0, 0.5,'POS_FAVORABLE',NULL,0.4,'INT_ATK_INT_LOGRA',0),
('INT_ATK','DEFAULT','DEFAULT','INT_ATK_DEFAULT_AMBOS','NONE',       0.5, 0.5, NULL, NULL, 0.1,'INT_ATK_AMBOS',0),
-- DEF_INT default (A defiende, B intenta INT)
('DEF_INT','DEFAULT','DEFAULT','DEF_INT_DEFAULT_DEF_AGUANTA','A',    0.0, 0.0,'CONTRA_EXITOSO',NULL,0.5,'DEF_INT_DEF_AGUANTA',0),
('DEF_INT','DEFAULT','DEFAULT','DEF_INT_DEFAULT_INT_LOGRA','B',      0.0, 0.0,'POS_DESFAVORABLE','POS_FAVORABLE',0.5,'DEF_INT_INT_LOGRA',0),
-- INT_DEF default (A intenta INT, B defiende)
('INT_DEF','DEFAULT','DEFAULT','INT_DEF_DEFAULT_INT_LOGRA','A',      0.0, 0.0,'POS_FAVORABLE','POS_DESFAVORABLE',0.5,'INT_DEF_INT_LOGRA',0),
('INT_DEF','DEFAULT','DEFAULT','INT_DEF_DEFAULT_DEF_AGUANTA','B',    0.0, 0.0, NULL,'CONTRA_EXITOSO',0.5,'INT_DEF_DEF_AGUANTA',0),
-- INT_INT default
('INT_INT','DEFAULT','DEFAULT','INT_INT_DEFAULT_A_LOGRA','A',        0.0, 0.0,'POS_FAVORABLE','POS_DESFAVORABLE',0.4,'INT_INT_A_LOGRA',0),
('INT_INT','DEFAULT','DEFAULT','INT_INT_DEFAULT_B_LOGRA','B',        0.0, 0.0,'POS_DESFAVORABLE','POS_FAVORABLE',0.4,'INT_INT_B_LOGRA',0),
('INT_INT','DEFAULT','DEFAULT','INT_INT_DEFAULT_CAOS','NONE',        0.0, 0.0, NULL, NULL, 0.2,'INT_INT_CAOS',0);

-- ============================================================
-- MULTIPLICADORES DE ESTADO
-- ============================================================

INSERT OR IGNORE INTO state_outcome_weights (state_code, outcome_code, multiplier, applies_to) VALUES
-- ── CAIDO ───────────────────────────────────────────────────────────────────
-- Amplifica outcomes fatales contra el receptor caído
('CAIDO',        'ATK_ATK_MAX_MX_FATAL_ESTOCADA_A',          2.5,  'RECEPTOR'),
('CAIDO',        'ATK_ATK_EXT_MX_FATAL_REMATE_A',            2.5,  'RECEPTOR'),

-- ── VACIO ────────────────────────────────────────────────────────────────────
-- Amplifica caída al precipicio (×5 sobre outcomes de precipicio)
('VACIO',        'ATK_INT_EXT_MX_ATAQUE_AL_PRECIPICIO',      5.0,  'BOTH'),
('VACIO',        'INT_ATK_EXT_MX_ATAQUE_AL_PRECIPICIO',      5.0,  'BOTH'),

-- ── NIEBLA_EXTREMA ───────────────────────────────────────────────────────────
-- Amplifica ataques sorpresa y dominio por niebla
('NIEBLA_EXTREMA','ATK_ATK_DEFAULT_DOMINA_A',                1.5,  'ACTOR'),
('NIEBLA_EXTREMA','ATK_ATK_DEFAULT_DOMINA_B',                1.5,  'ACTOR'),

-- ── FATIGA ───────────────────────────────────────────────────────────────────
-- El actor fatigado domina menos (penaliza outcomes decisivos del fatigado)
('FATIGA',       'ATK_ATK_DEFAULT_DOMINA_A',                 0.65, 'ACTOR'),
('FATIGA',       'ATK_ATK_DEFAULT_DOMINA_B',                 0.65, 'ACTOR'),
('FATIGA',       'ATK_DEF_DEFAULT_IMPACTO',                  0.70, 'ACTOR'),
('FATIGA',       'ATK_DEF_DEFAULT_IMPACTO_CONTROLADO',       0.75, 'ACTOR'),
('FATIGA',       'ATK_ATK_DEFAULT_VENTAJA_LEVE_A',           0.80, 'ACTOR'),
('FATIGA',       'ATK_ATK_DEFAULT_VENTAJA_LEVE_B',           0.80, 'ACTOR'),

-- ── VACILACION ───────────────────────────────────────────────────────────────
-- La duda reduce efectividad del vacilante como actor
('VACILACION',   'ATK_ATK_DEFAULT_DOMINA_A',                 0.70, 'ACTOR'),
('VACILACION',   'ATK_ATK_DEFAULT_DOMINA_B',                 0.70, 'ACTOR'),
('VACILACION',   'INT_ATK_DEFAULT_INT_LOGRA',                0.75, 'ACTOR'),
('VACILACION',   'INT_DEF_DEFAULT_INT_LOGRA',                0.75, 'ACTOR'),

-- ── PANICO ───────────────────────────────────────────────────────────────────
-- El receptor en pánico es más vulnerable a ataques y déficit defensivo
('PANICO',       'ATK_DEF_DEFAULT_IMPACTO',                  2.0,  'RECEPTOR'),
('PANICO',       'ATK_DEF_DEFAULT_IMPACTO_CONTROLADO',       1.6,  'RECEPTOR'),
-- El actor en pánico puede defenderse con éxito desesperado (adrenalina)
('PANICO',       'DEF_ATK_DEFAULT_CONTRA',                   1.8,  'ACTOR'),
('PANICO',       'DEF_ATK_DEFAULT_BLOQUEO',                  1.5,  'ACTOR'),

-- ── HIPEROFFENSIVO ───────────────────────────────────────────────────────────
-- Amplifica fuertemente los ataques dominantes del hiperofensivo
('HIPEROFFENSIVO','ATK_ATK_DEFAULT_DOMINA_A',                2.0,  'ACTOR'),
('HIPEROFFENSIVO','ATK_ATK_DEFAULT_DOMINA_B',                2.0,  'ACTOR'),
('HIPEROFFENSIVO','ATK_DEF_DEFAULT_IMPACTO',                 1.8,  'ACTOR'),
('HIPEROFFENSIVO','ATK_DEF_DEFAULT_IMPACTO_CONTROLADO',      1.5,  'ACTOR'),
('HIPEROFFENSIVO','ATK_ATK_EXT_MX_FATAL_REMATE_A',           1.8,  'ACTOR'),
('HIPEROFFENSIVO','ATK_ATK_EXT_MX_FATAL_ESTOCADA_A',         1.8,  'ACTOR'),
('HIPEROFFENSIVO','ATK_DEF_EXT_MX_FATAL_ESTOCADA',           1.8,  'ACTOR'),
('HIPEROFFENSIVO','ATK_DEF_EXT_MX_FATAL_HACHAZO',            1.8,  'ACTOR'),

-- ── POS_FAVORABLE ────────────────────────────────────────────────────────────
-- Ventaja posicional amplifica wins del posicionado
('POS_FAVORABLE','ATK_ATK_DEFAULT_DOMINA_A',                 1.5,  'ACTOR'),
('POS_FAVORABLE','ATK_ATK_DEFAULT_DOMINA_B',                 1.5,  'ACTOR'),
('POS_FAVORABLE','INT_ATK_DEFAULT_INT_LOGRA',                1.5,  'ACTOR'),
('POS_FAVORABLE','INT_DEF_DEFAULT_INT_LOGRA',                1.5,  'ACTOR'),
('POS_FAVORABLE','DEF_ATK_DEFAULT_CONTRA',                   1.3,  'ACTOR'),
('POS_FAVORABLE','DEF_ATK_DEFAULT_BLOQUEO',                  1.3,  'ACTOR'),

-- ── POS_DESFAVORABLE ─────────────────────────────────────────────────────────
-- Mala posición amplifica ataques recibidos
('POS_DESFAVORABLE','ATK_DEF_DEFAULT_IMPACTO',               1.5,  'RECEPTOR'),
('POS_DESFAVORABLE','ATK_DEF_DEFAULT_IMPACTO_CONTROLADO',    1.3,  'RECEPTOR'),
('POS_DESFAVORABLE','ATK_ATK_DEFAULT_DOMINA_A',              1.3,  'RECEPTOR'),
('POS_DESFAVORABLE','ATK_ATK_DEFAULT_DOMINA_B',              1.3,  'RECEPTOR'),

-- ── DESARMADO ────────────────────────────────────────────────────────────────
-- Combatiente desarmado es muy vulnerable a ataques con éxito
('DESARMADO',    'ATK_DEF_DEFAULT_IMPACTO',                  2.0,  'RECEPTOR'),
('DESARMADO',    'ATK_DEF_DEFAULT_IMPACTO_CONTROLADO',       1.8,  'RECEPTOR'),
('DESARMADO',    'DEF_ATK_DEFAULT_IMPACTO',                  2.0,  'RECEPTOR'),
('DESARMADO',    'ATK_DEF_EXT_MX_FATAL_ESTOCADA',            2.5,  'RECEPTOR'),
('DESARMADO',    'ATK_DEF_EXT_MX_FATAL_HACHAZO',             2.5,  'RECEPTOR'),
('DESARMADO',    'ATK_DEF_MAX_MX_FATAL_ESTOCADA',            2.0,  'RECEPTOR'),

-- ── DESMEMBRADO ──────────────────────────────────────────────────────────────
-- Herida grave: amplifica aún más el daño recibido y los outcomes fatales
('DESMEMBRADO',  'ATK_DEF_DEFAULT_IMPACTO',                  2.5,  'RECEPTOR'),
('DESMEMBRADO',  'ATK_DEF_DEFAULT_IMPACTO_CONTROLADO',       2.0,  'RECEPTOR'),
('DESMEMBRADO',  'ATK_ATK_DEFAULT_DOMINA_A',                 1.8,  'RECEPTOR'),
('DESMEMBRADO',  'ATK_ATK_DEFAULT_DOMINA_B',                 1.8,  'RECEPTOR'),
('DESMEMBRADO',  'ATK_DEF_EXT_MX_FATAL_ESTOCADA',           3.0,  'RECEPTOR'),
('DESMEMBRADO',  'ATK_DEF_EXT_MX_FATAL_HACHAZO',            3.0,  'RECEPTOR'),

-- ── ESPACIO_REDUCIDO (entorno) ───────────────────────────────────────────────
-- Espacio estrecho favorece INT y penaliza ATK_ATK dominante
('ESPACIO_REDUCIDO','INT_INT_DEFAULT_A_LOGRA',               1.8,  'BOTH'),
('ESPACIO_REDUCIDO','INT_INT_DEFAULT_B_LOGRA',               1.8,  'BOTH'),
('ESPACIO_REDUCIDO','INT_INT_DEFAULT_CRUCE_DE_MANIOBRAS',    1.5,  'BOTH'),
('ESPACIO_REDUCIDO','ATK_ATK_DEFAULT_DOMINA_A',              0.6,  'BOTH'),
('ESPACIO_REDUCIDO','ATK_ATK_DEFAULT_DOMINA_B',              0.6,  'BOTH'),
('ESPACIO_REDUCIDO','ATK_ATK_DEFAULT_INTERCAMBIO_BRUSCO',    1.4,  'BOTH'),

-- ── WEAPON TAGS — impacto mecánico de tipo de arma ──────────────────────────
-- pesado: armas grandes (mandoble) dominan ATK pero son más lentas en INT
('pesado',       'ATK_DEF_DEFAULT_IMPACTO',                  1.4,  'ACTOR'),
('pesado',       'ATK_DEF_DEFAULT_IMPACTO_CONTROLADO',       1.3,  'ACTOR'),
('pesado',       'ATK_ATK_DEFAULT_DOMINA_A',                 1.3,  'ACTOR'),
('pesado',       'ATK_ATK_DEFAULT_DOMINA_B',                 1.3,  'ACTOR'),
('pesado',       'INT_ATK_DEFAULT_INT_LOGRA',                0.7,  'ACTOR'),
('pesado',       'INT_DEF_DEFAULT_INT_LOGRA',                0.7,  'ACTOR'),
-- rapido: armas ágiles (espada, daga) mejoran INT y ataques rápidos
('rapido',       'INT_ATK_DEFAULT_INT_LOGRA',                1.4,  'ACTOR'),
('rapido',       'INT_DEF_DEFAULT_INT_LOGRA',                1.4,  'ACTOR'),
('rapido',       'ATK_INT_DEFAULT_ATK_PASA',                 1.3,  'ACTOR'),
('rapido',       'ATK_ATK_DEFAULT_DOMINA_A',                 1.1,  'ACTOR'),
('rapido',       'ATK_ATK_DEFAULT_DOMINA_B',                 1.1,  'ACTOR'),
-- intimidante: presencia que asusta (mandoble) amplifica dominio y desestabiliza
('intimidante',  'ATK_ATK_DEFAULT_DOMINA_A',                 1.3,  'ACTOR'),
('intimidante',  'ATK_ATK_DEFAULT_DOMINA_B',                 1.3,  'ACTOR'),
('intimidante',  'ATK_DEF_DEFAULT_IMPACTO',                  1.2,  'ACTOR'),
-- sigilo: armas furtivas (daga) amplifican interrupciones sorpresa
('sigilo',       'INT_ATK_DEFAULT_INT_LOGRA',                1.5,  'ACTOR'),
('sigilo',       'ATK_INT_DEFAULT_INT_LOGRA',                1.5,  'ACTOR'),
('sigilo',       'INT_DEF_DEFAULT_INT_LOGRA',                1.4,  'ACTOR');

-- ============================================================
-- NARRATIVA BASE (mínima para que el engine no falle en MVP)
-- ============================================================

INSERT OR IGNORE INTO narrative_templates
    (pool_tag, template_text, required_tags, excluded_tags, extra_effects, weight)
VALUES
('GENERIC_INTERCAMBIO',    'Los dos se golpean al mismo tiempo — ninguno cede terreno.',      '[]','[]','[]',1.0),
('GENERIC_VENTAJA_LEVE',   'El primero conecta antes. El otro absorbe el impacto.',           '[]','[]','[]',1.0),
('ATK_ATK_INTERCAMBIO',    'Ambos lanzan sus ataques en el mismo instante. Los golpes se cruzan.', '[]','[]','[]',1.0),
('ATK_ATK_DOMINA',         'Uno de los dos llega primero y con más fuerza. El otro lo siente.', '[]','[]','[]',1.0),
('ATK_ATK_CHOQUE_EPICO',   'El choque es brutal. Dos fuerzas iguales colisionan sin ceder.',  '[]','[]','[]',1.0),
('ATK_ATK_DOMINIO_ABSOLUTO','No hay defensa posible. El dominio es total.',                   '[]','[]','[]',1.0),
('ATK_DEF_BLOQUEO',        'El defensor interpone su posición y el ataque pierde fuerza.',    '[]','[]','[]',1.0),
('ATK_DEF_IMPACTO',        'El ataque pasa por encima de la defensa y conecta limpio.',       '[]','[]','[]',1.0),
('ATK_DEF_CONTRA',         'La defensa fue tan perfecta que generó una apertura. Contraataque.','[]','[]','[]',1.0),
('ATK_DEF_BLOQUEO_PARCIAL','El defensor aguanta pero el impacto lo empuja hacia atrás.',      '[]','[]','[]',1.0),
('ATK_DEF_GUARDIA_ROTA',   'El ataque desbarata por completo la guardia del defensor.',       '[]','[]','[]',1.0),
('ATK_DEF_CONTRA_EPICO',   'La defensa convierte el impulso del atacante en su propia trampa.','[]','[]','[]',1.0),
('ATK_DEF_CONTRA_PARCIAL', 'La defensa sólida abre una rendija. El defensor aprovecha.',      '[]','[]','[]',1.0),
('DEF_ATK_BLOQUEO',        'La defensa aguanta. El ataque se estrella contra ella.',           '[]','[]','[]',1.0),
('DEF_ATK_IMPACTO',        'El ataque supera la defensa y deja su marca.',                    '[]','[]','[]',1.0),
('DEF_ATK_CONTRA',         'El defensor convierte la presión en contraataque.',               '[]','[]','[]',1.0),
('DEF_DEF_REPOSICION',     'Ambos se mueven. Uno encuentra mejor posición que el otro.',      '[]','[]','[]',1.0),
('DEF_DEF_ESPERA',         'Los dos se miden en silencio. Nadie ataca. La tensión sube.',     '[]','[]','[]',1.0),
('ATK_INT_ATK_PASA',       'Mientras el segundo maniobra, el primero aprovecha y conecta.',   '[]','[]','[]',1.0),
('ATK_INT_INT_LOGRA',      'La maniobra funciona. El ataque pasa por donde ya no estaba.',    '[]','[]','[]',1.0),
('ATK_INT_AMBOS',          'El ataque y la maniobra se dan casi al mismo tiempo.',            '[]','[]','[]',1.0),
('INT_ATK_ATK_PASA',       'El ataque llega mientras el otro aún maniobra.',                  '[]','[]','[]',1.0),
('INT_ATK_INT_LOGRA',      'La maniobra redirige el ataque. El primero sale mejor parado.',   '[]','[]','[]',1.0),
('INT_ATK_AMBOS',          'Los dos cambian de posición. La situación queda indefinida.',     '[]','[]','[]',1.0),
('DEF_INT_DEF_AGUANTA',    'La defensa sólida deja al que maniobra sin respuesta.',           '[]','[]','[]',1.0),
('DEF_INT_INT_LOGRA',      'La maniobra descoloca al defensor. El campo cambia.',             '[]','[]','[]',1.0),
('INT_DEF_INT_LOGRA',      'La maniobra consigue reposicionar antes de que la defensa cierre.','[]','[]','[]',1.0),
('INT_DEF_DEF_AGUANTA',    'La defensa se cierra a tiempo. La maniobra no tiene espacio.',    '[]','[]','[]',1.0),
('INT_INT_A_LOGRA',        'Las dos maniobras chocan. Una de las dos sale mejor.',            '[]','[]','[]',1.0),
('INT_INT_B_LOGRA',        'Ambos intentan modificar el campo. Solo uno lo logra.',           '[]','[]','[]',1.0),
('INT_INT_CAOS',           'Las dos maniobras se anulan mutuamente. Caos controlado.',        '[]','[]','[]',1.0),
('ATK_INT_INT_FALLIDA',    'La maniobra quedó a medio camino. El golpe llega sin obstáculo.', '[]','[]','[]',1.0),
('ATK_INT_INT_FALLIDA_LEVE','El intento de maniobra dejó al segundo ligeramente expuesto.',   '[]','[]','[]',1.0),
('INT_ATK_INT_FALLIDA',    'La maniobra falló. El ataque encuentra un blanco sin defensa.',   '[]','[]','[]',1.0),
('FATAL_REMATE',           'El golpe final llega cuando ya no hay posibilidad de defensa.',   '["vulnerable"]','[]','[]',0.5),
('INT_INT_CAOS_TORPE',     'Ninguno sabe muy bien qué está haciendo. La situación es ridícula.','[]','[]','[]',1.0),
('INT_INT_TROPIEZO_MUTUO', 'Los dos se estorban y pierden el equilibrio.',                    '[]','[]','[]',1.0);

-- ============================================================
-- EXTRA_EFFECTS en templates narrativos (narrativa → mecánica)
-- Estos UPDATE garantizan que incluso clones limpios tengan extra_effects
-- en templates que demuestran el sistema. Formato JSON:
-- [{"target":"ACTOR|RECEPTOR|P1|P2","effect":"CODE","duration_phases":N,"chance":0.X}]
-- ============================================================

UPDATE narrative_templates SET extra_effects = '[{"target":"ACTOR","effect":"POS_FAVORABLE","duration_phases":2,"chance":0.30,"source":"narrative"}]'
    WHERE pool_tag = 'DEF_ATK_CONTRA';

UPDATE narrative_templates SET extra_effects = '[{"target":"ACTOR","effect":"POS_FAVORABLE","duration_phases":2,"chance":0.40,"source":"narrative"}]'
    WHERE pool_tag = 'ATK_DEF_CONTRA';

UPDATE narrative_templates SET extra_effects = '[{"target":"RECEPTOR","effect":"POS_DESFAVORABLE","duration_phases":2,"chance":0.25,"source":"narrative"}]'
    WHERE pool_tag = 'ATK_DEF_GUARDIA_ROTA';

UPDATE narrative_templates SET extra_effects = '[{"target":"RECEPTOR","effect":"VACILACION","duration_phases":3,"chance":0.20,"source":"narrative"}]'
    WHERE pool_tag = 'ATK_DEF_CONTRA_EPICO';

UPDATE narrative_templates SET extra_effects = '[{"target":"ACTOR","effect":"POS_FAVORABLE","duration_phases":2,"chance":0.35,"source":"narrative"},{"target":"RECEPTOR","effect":"VACILACION","duration_phases":3,"chance":0.15,"source":"narrative"}]'
    WHERE pool_tag = 'DEF_ATK_CONTRA';

UPDATE narrative_templates SET extra_effects = '[{"target":"ACTOR","effect":"VACILACION","duration_phases":2,"chance":0.12,"source":"narrative"},{"target":"RECEPTOR","effect":"VACILACION","duration_phases":2,"chance":0.12,"source":"narrative"}]'
    WHERE pool_tag = 'ATK_ATK_CHOQUE_EPICO';

-- ============================================================
-- CONFIG DE BATALLA
-- ============================================================
-- (se consulta en runtime, hardcodeado como constantes en config.py también)
-- No hay tabla separada de battle_config en MVP — las constantes viven en config.py
