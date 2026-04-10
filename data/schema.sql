PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ============================================================
-- TABLAS DE REGLAS CORE (configurables desde bases.html)
-- ============================================================

CREATE TABLE IF NOT EXISTS core_dice_power (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    min_value   INTEGER NOT NULL,
    max_value   INTEGER NOT NULL,
    power_level INTEGER NOT NULL,
    label       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS core_difference_band (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    min_diff    INTEGER NOT NULL,
    max_diff    INTEGER NOT NULL,
    band_code   TEXT NOT NULL UNIQUE,
    bono_value  INTEGER NOT NULL DEFAULT 0
);

-- ============================================================
-- ARMAS
-- ============================================================

CREATE TABLE IF NOT EXISTS weapon_sizes (
    size_code      TEXT PRIMARY KEY,
    hits           INTEGER NOT NULL,
    dmg_per_hit    REAL NOT NULL,
    crit_dmg       REAL NOT NULL,
    dual_allowed   INTEGER NOT NULL DEFAULT 0,
    shield_allowed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS weapons (
    code           TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    size_code      TEXT NOT NULL,
    narrative_tags TEXT NOT NULL DEFAULT '[]',  -- JSON array de strings
    FOREIGN KEY (size_code) REFERENCES weapon_sizes(size_code)
);

-- ============================================================
-- ESTADOS Y EFECTOS DE COMBATE
-- ============================================================

CREATE TABLE IF NOT EXISTS combat_effects (
    code                TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    duration_phases     INTEGER NOT NULL,   -- -1 = permanente, 0 = next_phase, N = N fases
    applies_to          TEXT NOT NULL,      -- P1 | P2 | BOTH | ENTORNO
    power_mod           INTEGER NOT NULL DEFAULT 0,
    blocks_next_action  INTEGER NOT NULL DEFAULT 0,
    blocks_recovery     INTEGER NOT NULL DEFAULT 0,
    narrative_tags      TEXT NOT NULL DEFAULT '[]'  -- JSON array
);

-- ============================================================
-- OUTCOME MATRIX
-- ============================================================

CREATE TABLE IF NOT EXISTS outcome_matrix (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    action_pair       TEXT NOT NULL,   -- ATK_ATK | ATK_DEF | ... | GENERIC
    difference_band   TEXT NOT NULL,   -- BAJA | MODERADA | ... | DEFAULT
    power_context     TEXT NOT NULL,   -- BOTH_HIGH | BOTH_LOW | MIXED_EXTREME | BALANCED | DEFAULT
    outcome_code      TEXT NOT NULL UNIQUE,
    phase_winner      TEXT NOT NULL,   -- A | B | NONE
    counter_dmg_A     REAL NOT NULL DEFAULT 0,
    counter_dmg_B     REAL NOT NULL DEFAULT 0,
    effect_A          TEXT,            -- FK a combat_effects.code o NULL
    effect_B          TEXT,            -- FK a combat_effects.code o NULL
    base_weight       REAL NOT NULL DEFAULT 1.0,
    narrative_pool_tag TEXT NOT NULL,
    is_fatal          INTEGER NOT NULL DEFAULT 0
);

-- Multiplicadores de estado sobre pesos de outcomes
CREATE TABLE IF NOT EXISTS state_outcome_weights (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    state_code   TEXT NOT NULL,    -- combat_effects.code
    outcome_code TEXT NOT NULL,    -- outcome_matrix.outcome_code
    multiplier   REAL NOT NULL,
    applies_to   TEXT NOT NULL     -- RECEPTOR | ACTOR | BOTH
);

-- ============================================================
-- NARRATIVA
-- ============================================================

CREATE TABLE IF NOT EXISTS narrative_templates (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    pool_tag          TEXT NOT NULL,
    template_text     TEXT NOT NULL,
    required_tags     TEXT NOT NULL DEFAULT '[]',   -- JSON: todos deben estar activos
    excluded_tags     TEXT NOT NULL DEFAULT '[]',   -- JSON: ninguno debe estar activo
    extra_effects     TEXT NOT NULL DEFAULT '[]',   -- JSON: efectos adicionales que activa
    weight            REAL NOT NULL DEFAULT 1.0
);

-- ============================================================
-- ARENA
-- ============================================================

CREATE TABLE IF NOT EXISTS arena_pool (
    code                  TEXT PRIMARY KEY,
    name                  TEXT NOT NULL,
    initial_state_tags    TEXT NOT NULL DEFAULT '[]',  -- JSON: estados activos desde turno 1
    fatal_multiplier_base REAL NOT NULL DEFAULT 1.0,
    narrative_tags        TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS arena_throwables (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    arena_code  TEXT NOT NULL,
    object_code TEXT NOT NULL,
    object_name TEXT NOT NULL,
    type        TEXT NOT NULL,   -- LIGERO | MEDIO | PESADO
    weight      REAL NOT NULL DEFAULT 1.0,
    FOREIGN KEY (arena_code) REFERENCES arena_pool(code)
);

-- ============================================================
-- SKILLS
-- ============================================================

CREATE TABLE IF NOT EXISTS skill_pool (
    code         TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    tier         TEXT NOT NULL,  -- COMUN | POCO_COMUN | RARA | LEGENDARIA | EPICA
    effect_type  TEXT NOT NULL,
    power_mod    INTEGER NOT NULL DEFAULT 0,
    duration_phases INTEGER NOT NULL DEFAULT -1,
    special_tags TEXT NOT NULL DEFAULT '[]'
);

-- ============================================================
-- BATALLA RUNTIME
-- ============================================================

CREATE TABLE IF NOT EXISTS battles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mode            TEXT NOT NULL,   -- SIMULATION | PVE | PVP
    arena_code      TEXT,
    status          TEXT NOT NULL DEFAULT 'IN_PROGRESS',  -- IN_PROGRESS | FINISHED
    winner_side     TEXT,            -- P1 | P2
    turn_number     INTEGER NOT NULL DEFAULT 1,
    phase_number    INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at     TEXT,
    FOREIGN KEY (arena_code) REFERENCES arena_pool(code)
);

-- Estado en tiempo real de cada combatiente
CREATE TABLE IF NOT EXISTS battle_state (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    battle_id       INTEGER NOT NULL,
    side            TEXT NOT NULL,  -- P1 | P2
    counters        REAL NOT NULL DEFAULT 0,
    weapon_code     TEXT,
    weapon2_code    TEXT,           -- segunda arma si DUAL
    combat_style    TEXT NOT NULL DEFAULT 'ONE_HANDED',
    recovery_blocked_until_turn INTEGER NOT NULL DEFAULT 0,
    atk_streak      INTEGER NOT NULL DEFAULT 0,  -- para detectar spam ATK
    FOREIGN KEY (battle_id) REFERENCES battles(id) ON DELETE CASCADE,
    FOREIGN KEY (weapon_code) REFERENCES weapons(code),
    FOREIGN KEY (weapon2_code) REFERENCES weapons(code)
);

-- Efectos activos en batalla
CREATE TABLE IF NOT EXISTS battle_active_effects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    battle_id       INTEGER NOT NULL,
    side            TEXT NOT NULL,  -- P1 | P2 | ENTORNO
    effect_code     TEXT NOT NULL,
    expires_at_phase INTEGER,       -- fase absoluta (turn*3+phase) en que expira, NULL=permanente
    source          TEXT,           -- qué lo activó
    FOREIGN KEY (battle_id) REFERENCES battles(id) ON DELETE CASCADE
);

-- Acumuladores por jugador
CREATE TABLE IF NOT EXISTS battle_accumulators (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    battle_id           INTEGER NOT NULL,
    side                TEXT NOT NULL,
    roll_sum            REAL NOT NULL DEFAULT 0,
    roll_sum_opp        REAL NOT NULL DEFAULT 0,
    twenties_count      INTEGER NOT NULL DEFAULT 0,
    low_streak          INTEGER NOT NULL DEFAULT 0,
    turns_won           INTEGER NOT NULL DEFAULT 0,
    consecutive_high    INTEGER NOT NULL DEFAULT 0,
    consecutive_wins    INTEGER NOT NULL DEFAULT 0,
    last_threshold      INTEGER NOT NULL DEFAULT 0,
    crit_received_turn  INTEGER NOT NULL DEFAULT 0,  -- turno del último crítico recibido
    FOREIGN KEY (battle_id) REFERENCES battles(id) ON DELETE CASCADE
);

-- Skills activas en batalla
CREATE TABLE IF NOT EXISTS battle_skills (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    battle_id       INTEGER NOT NULL,
    side            TEXT NOT NULL,
    skill_code      TEXT NOT NULL,
    activated_at_turn INTEGER NOT NULL,
    expires_at_phase INTEGER,
    FOREIGN KEY (battle_id) REFERENCES battles(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_code) REFERENCES skill_pool(code)
);

-- Log completo de batalla
CREATE TABLE IF NOT EXISTS battle_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    battle_id       INTEGER NOT NULL,
    turn_number     INTEGER NOT NULL,
    phase_number    INTEGER NOT NULL,
    action_p1       TEXT NOT NULL,
    action_p2       TEXT NOT NULL,
    roll_p1         INTEGER NOT NULL,
    roll_p2         INTEGER NOT NULL,
    effective_p1    REAL NOT NULL,
    effective_p2    REAL NOT NULL,
    power_p1        INTEGER NOT NULL,
    power_p2        INTEGER NOT NULL,
    difference      REAL NOT NULL,
    difference_band TEXT NOT NULL,
    power_context   TEXT NOT NULL,
    action_pair     TEXT NOT NULL,
    outcome_code    TEXT NOT NULL,
    phase_winner    TEXT NOT NULL,   -- A | B | NONE (según perspectiva del par)
    roll_winner     TEXT NOT NULL,   -- P1 | P2 | NONE
    counter_dmg_p1  REAL NOT NULL DEFAULT 0,
    counter_dmg_p2  REAL NOT NULL DEFAULT 0,
    counters_p1     REAL NOT NULL,
    counters_p2     REAL NOT NULL,
    effect_applied_p1 TEXT,
    effect_applied_p2 TEXT,
    narrative_text  TEXT NOT NULL,
    narrative_effects_applied TEXT NOT NULL DEFAULT '[]',
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (battle_id) REFERENCES battles(id) ON DELETE CASCADE
);
