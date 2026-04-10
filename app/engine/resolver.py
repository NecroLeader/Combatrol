"""
Resolver principal — implementa el flujo de 11 pasos del GDD.

resolve_phase(battle_id, action_p1, action_p2) → PhaseResult
"""

import random
import json
from app import config
from app.repositories import rules_repo as rules
from app.repositories import battle_repo as repo
from app.engine.narrative import select_narrative, collect_active_tags
from app.schemas.battle import PhaseResult

CAP = 25.0   # máximo de tirada efectiva antes de MOMENTUM_OVERFLOW


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _phase_abs(turn: int, phase: int) -> int:
    """Número de fase absoluta (para expiración de efectos)."""
    return (turn - 1) * config.PHASES_PER_TURN + phase


def _sum_mods(battle_id: int, side: str) -> float:
    """Suma los power_mod de todos los efectos activos para un lado."""
    effects = repo.get_active_effects(battle_id, side)
    total = 0.0
    for eff in effects:
        code = eff["effect_code"]
        if code == "MOMENTUM_OVERFLOW":
            # El valor real del overflow se guarda en source como "overflow:X.X"
            source = eff.get("source", "")
            if source.startswith("overflow:"):
                try:
                    total += float(source.split(":", 1)[1])
                except (IndexError, ValueError):
                    pass
        else:
            effect_def = rules.get_combat_effect(code)
            if effect_def:
                total += effect_def["power_mod"]
    return total


def _roll_dice(battle_id: int, side: str, phase_abs: int) -> tuple[int, float]:
    """Tira 1d20 y aplica modificadores. Devuelve (raw, effective)."""
    raw = random.randint(1, 20)
    mods = _sum_mods(battle_id, side)
    effective = raw + mods
    # DESMEMBRADO: reduce el cap de tirada de 25 a 20 (miembro perdido limita el poder).
    cap = 20.0 if repo.has_effect(battle_id, side, "DESMEMBRADO") else CAP
    # Cap superior: overflow → MOMENTUM_OVERFLOW para la siguiente fase.
    # expires_at = phase_abs + 2: survive expire_effects(phase_abs+1) y disponible
    # en _sum_mods de fase phase_abs+1; eliminado al inicio de phase_abs+2.
    if effective > cap:
        overflow = effective - cap
        effective = cap
        repo.remove_effect(battle_id, side, "MOMENTUM_OVERFLOW")
        repo.add_effect(battle_id, side, "MOMENTUM_OVERFLOW",
                        expires_at_phase=phase_abs + 2,
                        source=f"overflow:{overflow:.1f}")
    # Cap inferior: -4 mínimo (COLAPSO)
    effective = max(-4.0, effective)
    return raw, effective


# Sesgo por ganador del dado, escala con la magnitud de diferencia.
# A mayor banda, más determinista el resultado hacia quien dominó el dado.
_BAND_BIAS = {
    # Estrictamente monótono con la magnitud de diferencia (core_difference_band):
    # BAJA(0-3) < MODERADA(4-7) < REGULAR(8-10) < ALTA(11-13) < MUY_ALTA(14-16) < MAXIMA(17-19) < EXTREMA(20+)
    'BAJA':     1.4,
    'MODERADA': 2.5,
    'REGULAR':  4.0,
    'ALTA':     6.0,
    'MUY_ALTA': 9.0,
    'MAXIMA':   14.0,
    'EXTREMA':  22.0,
    'DEFAULT':  1.0,
}

# Bono de banda: ganador de fase recibe modificador temporal para la siguiente fase.
# GDD sección 4: "el bono se aplica al ganador de la fase como modificador temporal".
_BAND_BONUS_EFFECT = {
    'MODERADA': 'BANDA_MODERADA_BONUS',
    'REGULAR':  'BANDA_REGULAR_BONUS',
    'ALTA':     'BANDA_ALTA_BONUS',
    'MUY_ALTA': 'BANDA_MUY_ALTA_BONUS',
    'MAXIMA':   'BANDA_MAXIMA_BONUS',
    'EXTREMA':  'BANDA_EXTREMA_BONUS',
}


def _weighted_choice(candidates: list[dict], battle_id: int,
                     active_states_p1: list[str],
                     active_states_p2: list[str],
                     active_states_entorno: list[str] | None = None,
                     dice_leader: str = 'NONE',
                     diff_band: str = 'DEFAULT') -> dict:
    """Elige un outcome aplicando multiplicadores de estado con applies_to (ACTOR/RECEPTOR/BOTH/ENTORNO)
    y sesgo hacia el ganador del dado proporcional a la banda de diferencia.

    A en el par = P1, B = P2. actor = quien gana la fase (phase_winner), receptor = quien pierde.
    """
    active_states_entorno = active_states_entorno or []

    # Regla especial: AMBOS CAÍDOS → multiplicadores de CAIDO se anulan.
    states_p1 = active_states_p1
    states_p2 = active_states_p2
    if "CAIDO" in states_p1 and "CAIDO" in states_p2:
        states_p1 = [s for s in states_p1 if s != "CAIDO"]
        states_p2 = [s for s in states_p2 if s != "CAIDO"]

    bias = _BAND_BIAS.get(diff_band, 1.0)
    weights = []
    for c in candidates:
        # Determinar actor/receptor según phase_winner del candidate.
        # A=P1, B=P2; para NONE (empate) no hay actor ni receptor → listas vacías.
        pw = c["phase_winner"]
        if pw == 'A':
            actor, receptor = states_p1, states_p2
        elif pw == 'B':
            actor, receptor = states_p2, states_p1
        else:
            # NONE (empate): no hay actor ni receptor — solo multiplicadores BOTH/ENTORNO aplican.
            # Evita sesgo estructural hacia P1 en outcomes de empate.
            actor, receptor = [], []

        w = c["base_weight"] * rules.get_state_multipliers(
            c["outcome_code"], actor, receptor, active_states_entorno
        )
        if dice_leader != 'NONE' and bias > 1.0:
            if c["phase_winner"] == dice_leader:
                w *= bias
            elif c["phase_winner"] != 'NONE':
                w /= bias
        weights.append(max(w, 0.001))
    return random.choices(candidates, weights=weights, k=1)[0]


def _add_effect_safe(battle_id: int, side: str, effect_code: str,
                     expires_at_phase: int | None, source: str) -> None:
    """Agrega efecto solo si no está ya activo (evita duplicados de permanentes)."""
    if not repo.has_effect(battle_id, side, effect_code):
        repo.add_effect(battle_id, side, effect_code, expires_at_phase, source)


def _apply_effect(battle_id: int, side: str, effect_code: str | None,
                  current_phase_abs: int, *,
                  duration_override: int | None = None,
                  source: str = "outcome_matrix") -> str | None:
    """Aplica un efecto a un side. Función unificada usada por outcome_matrix y narrativa.

    Parámetros opcionales (keyword-only):
    - duration_override: sobreescribe la duración del efecto definida en DB.
      Para extra_effects narrativos, se aplica min(dur, 2) para garantizar
      que el efecto sobreviva al menos un expire_effects. dur=0 es válido
      (bloqueo de acción en la siguiente fase únicamente).
    - source: etiqueta de origen para trazabilidad en battle_active_effects.

    Efectos con applies_to=ENTORNO se guardan siempre bajo side='ENTORNO'.
    POS_FAVORABLE y POS_DESFAVORABLE son mutuamente excluyentes — siempre.
    """
    if not effect_code:
        return None
    effect_def = rules.get_combat_effect(effect_code)
    if not effect_def:
        return None

    # Efectos de entorno van al lado ENTORNO sin importar quién los activó
    effective_side = "ENTORNO" if effect_def["applies_to"] == "ENTORNO" else side

    # POS_FAVORABLE y POS_DESFAVORABLE son mutuamente excluyentes por jugador.
    # Se aplica siempre, sin importar si el efecto viene de outcome_matrix o narrativa.
    if effect_code == "POS_FAVORABLE":
        repo.remove_effect(battle_id, effective_side, "POS_DESFAVORABLE")
    elif effect_code == "POS_DESFAVORABLE":
        repo.remove_effect(battle_id, effective_side, "POS_FAVORABLE")

    duration = duration_override if duration_override is not None else effect_def["duration_phases"]
    if duration == -1:
        expires = None
    elif duration == 0:
        # Duración 0 = bloqueo de acción en la siguiente fase (visible en state-checks,
        # eliminado por expire_effects al principio de esa fase).
        expires = current_phase_abs
    else:
        if duration_override is not None:
            # Extra_effects: mínimo 2 para sobrevivir expire_effects de la siguiente fase
            # y ser visible en _sum_mods al tirar dados de esa fase.
            expires = current_phase_abs + max(duration, 2)
        else:
            expires = current_phase_abs + duration

    _add_effect_safe(battle_id, effective_side, effect_code, expires, source)

    # CAIDO: automáticamente da HIPEROFFENSIVO al oponente si no tiene debuff
    if effect_code == "CAIDO":
        opp = "P2" if side == "P1" else "P1"
        opp_effects = repo.get_active_effect_codes(battle_id, opp)
        debuffs = {"DESARMADO", "ARMA_ROTA", "DESMEMBRADO", "CAIDO",
                   "POS_DESFAVORABLE", "FATIGA", "VACILACION", "PANICO"}
        if not any(e in debuffs for e in opp_effects):
            # +2 para que sobreviva expire_effects de la siguiente fase
            # y sea visible para _sum_mods en los dados de esa fase.
            _add_effect_safe(battle_id, opp, "HIPEROFFENSIVO", current_phase_abs + 2, "caido_bonus")

    return effect_code


def _apply_narrative_effects(battle_id: int, extra_effects_json: str,
                              outcome: dict, phase_abs: int) -> list[dict]:
    """Aplica efectos adicionales probabilísticos definidos en el template narrativo.

    Delega en _apply_effect para garantizar coherencia de exclusiones y timing
    idénticos a los efectos de outcome_matrix (POS_FAVORABLE/POS_DESFAVORABLE
    mutuamente excluyentes, ENTORNO routing, etc.).

    Formato de extra_effects_json (array JSON):
    [
      {"target":"ACTOR","effect":"POS_FAVORABLE","duration_phases":2,"chance":0.25,"source":"narrative"},
      {"target":"RECEPTOR","effect":"VACILACION","duration_phases":3,"chance":0.10}
    ]
    target puede ser ACTOR, RECEPTOR, P1, P2 o ENTORNO.
    Si chance no está, se aplica siempre (chance=1.0).
    Si duration_phases no está, usa el valor de DB del efecto.
    Retorna lista de eventos aplicados para logging de observabilidad.
    """
    try:
        effects = json.loads(extra_effects_json or "[]")
    except (json.JSONDecodeError, TypeError):
        return []

    phase_winner = outcome.get("phase_winner", "NONE")
    events: list[dict] = []

    for e in effects:
        roll = random.random()
        chance = e.get("chance", 1.0)
        if roll > chance:
            continue

        target_key = e.get("target", "NONE")
        if target_key == "ACTOR":
            side = "P1" if phase_winner == "A" else ("P2" if phase_winner == "B" else None)
        elif target_key == "RECEPTOR":
            side = "P2" if phase_winner == "A" else ("P1" if phase_winner == "B" else None)
        elif target_key in ("P1", "P2", "ENTORNO"):
            side = target_key
        else:
            continue

        if side is None:
            continue

        effect_code = e.get("effect")
        if not effect_code:
            continue

        # Delegar en _apply_effect para respetar todas las reglas del sistema
        # (exclusiones, ENTORNO routing, CAIDO → HIPEROFFENSIVO, etc.)
        applied = _apply_effect(battle_id, side, effect_code, phase_abs,
                                duration_override=e.get("duration_phases"),
                                source=e.get("source", "narrative"))
        if applied:
            events.append({
                "source": e.get("source", "narrative"),
                "target": target_key,
                "side": side,
                "effect": effect_code,
                "roll": round(roll, 3),
                "chance": chance,
            })

    return events


def _check_fatiga(battle_id: int, side: str, action: str, current_phase_abs: int) -> None:
    """Penaliza spam de ATK con FATIGA."""
    state = repo.get_battle_state(battle_id, side)
    if not state:
        return
    streak = state["atk_streak"]
    if action == "ATK":
        streak += 1
        if streak >= config.ATK_SPAM_FATIGUE_THRESHOLD:
            # Dura hasta la primera fase del turno siguiente (≈3 fases)
            _add_effect_safe(battle_id, side, "FATIGA", current_phase_abs + 3, "atk_spam")
            streak = 0
    else:
        streak = 0
    repo.update_atk_streak(battle_id, side, streak)


def _update_accumulators(battle_id: int, side: str, opp_side: str,
                         effective: float, opp_effective: float,
                         roll_winner_is_me: bool, turn: int) -> None:
    acc = repo.get_accumulators(battle_id, side)
    if not acc:
        return

    new_roll_sum = acc["roll_sum"] + effective
    new_roll_sum_opp = acc["roll_sum_opp"] + opp_effective
    new_20s = acc["twenties_count"] + (1 if effective >= 20 else 0)
    new_consec_high = (acc["consecutive_high"] + 1) if effective >= 17 else 0

    # low_streak: tiradas efectivas ≤ threshold
    if effective <= config.LOW_ROLL_THRESHOLD:
        new_low_streak = acc["low_streak"] + 1
    else:
        new_low_streak = 0

    new_turns_won = acc["turns_won"] + (1 if roll_winner_is_me else 0)
    new_consec_wins = (acc["consecutive_wins"] + 1) if roll_winner_is_me else 0

    repo.update_accumulators(
        battle_id, side,
        roll_sum=new_roll_sum,
        roll_sum_opp=new_roll_sum_opp,
        twenties_count=new_20s,
        low_streak=new_low_streak,
        turns_won=new_turns_won,
        consecutive_high=new_consec_high,
        consecutive_wins=new_consec_wins,
    )

    # Punición por low_streak
    phase_abs = _phase_abs(turn, 1)  # se activa en la siguiente fase
    if new_low_streak >= config.LOW_STREAK_PANICO and not repo.has_effect(battle_id, side, "PANICO"):
        _add_effect_safe(battle_id, side, "PANICO", phase_abs + 3, "low_streak")
    elif new_low_streak >= config.LOW_STREAK_VACILACION and not repo.has_effect(battle_id, side, "VACILACION"):
        _add_effect_safe(battle_id, side, "VACILACION", phase_abs + 6, "low_streak")


def _apply_recovery(battle_id: int, turn: int) -> None:
    """Cada RECOVERY_INTERVAL_TURNS recupera 0.5 contadores a quienes corresponda."""
    if turn % config.RECOVERY_INTERVAL_TURNS != 0:
        return
    for side in ("P1", "P2"):
        state = repo.get_battle_state(battle_id, side)
        if not state:
            continue
        if state["recovery_blocked_until_turn"] >= turn:
            continue
        # Efectos con blocks_recovery=1 (ej: DESMEMBRADO) impiden recuperación permanentemente.
        active_effects = repo.get_active_effects(battle_id, side)
        if any(eff.get("blocks_recovery") for eff in active_effects):
            continue
        new_cnt = max(0.0, state["counters"] - config.RECOVERY_AMOUNT)
        repo.update_counters(battle_id, side, new_cnt)


def _counter_dmg_for_side(outcome: dict, is_player_A: bool) -> float:
    """Devuelve el daño que recibe este jugador según si es A o B en el par."""
    if is_player_A:
        return outcome["counter_dmg_A"]
    return outcome["counter_dmg_B"]


def _effect_for_side(outcome: dict, is_player_A: bool) -> str | None:
    if is_player_A:
        return outcome.get("effect_A")
    return outcome.get("effect_B")


# ─────────────────────────────────────────────────────────────────────────────
# RESOLVE PHASE — flujo principal
# ─────────────────────────────────────────────────────────────────────────────

def resolve_phase(battle_id: int, action_p1: str, action_p2: str) -> PhaseResult:
    """Implementa el flujo de 11 pasos del GDD."""

    # ── Paso 0: estado actual ────────────────────────────────────────────────
    battle = repo.get_battle(battle_id)
    if not battle or battle["status"] == "FINISHED":
        raise ValueError(f"Batalla {battle_id} no existe o ya terminó.")

    turn   = battle["turn_number"]
    phase  = battle["phase_number"]
    phase_abs = _phase_abs(turn, phase)

    # ── Restricciones de estado ANTES de expirar efectos ────────────────────
    # Los efectos con expires_at = prev_phase_abs siguen activos hasta que
    # expire_effects los elimina. Para que restrinjan la acción actual, el
    # check debe ocurrir ANTES de expire_effects.
    #
    # CAIDO: fuerza INT (única opción válida desde el suelo).
    if repo.has_effect(battle_id, "P1", "CAIDO"):
        action_p1 = "INT"
    if repo.has_effect(battle_id, "P2", "CAIDO"):
        action_p2 = "INT"
    # PANICO: bloquea ATK, fuerza DEF (supervivencia).
    # GDD sección 9: PANICO "bloquea ATAQUE".
    if repo.has_effect(battle_id, "P1", "PANICO") and action_p1 == "ATK":
        action_p1 = "DEF"
    if repo.has_effect(battle_id, "P2", "PANICO") and action_p2 == "ATK":
        action_p2 = "DEF"

    # Expirar efectos vencidos (DESPUÉS de los checks de bloqueo de acción)
    repo.expire_effects(battle_id, phase_abs)

    state_p1 = repo.get_battle_state(battle_id, "P1")
    state_p2 = repo.get_battle_state(battle_id, "P2")

    # ── Paso 2: tiradas ──────────────────────────────────────────────────────
    roll_p1, eff_p1 = _roll_dice(battle_id, "P1", phase_abs)
    roll_p2, eff_p2 = _roll_dice(battle_id, "P2", phase_abs)

    # ── Paso 1: spam ATK check (DESPUÉS de tirar dados) ──────────────────────
    # FATIGA se aplica DESPUÉS de la tirada para que no penalice la fase actual,
    # sino la siguiente (cuando el efecto ya esté activo en _sum_mods).
    _check_fatiga(battle_id, "P1", action_p1, phase_abs)
    _check_fatiga(battle_id, "P2", action_p2, phase_abs)

    # ── Paso 3: clasificar ───────────────────────────────────────────────────
    power_p1 = rules.get_power_level(eff_p1)
    power_p2 = rules.get_power_level(eff_p2)
    difference = abs(eff_p1 - eff_p2)
    diff_band = rules.get_difference_band(difference)
    power_context = rules.get_power_context(power_p1, power_p2)

    # ── Paso 4: par de acción ────────────────────────────────────────────────
    action_pair = f"{action_p1}_{action_p2}"

    # "A" en el par = quien eligió la acción de la izquierda = P1
    # "B" = P2
    p1_is_A = True

    # ── Paso 5: consultar outcome_matrix ────────────────────────────────────
    active_p1 = repo.get_active_effect_codes(battle_id, "P1")
    active_p2 = repo.get_active_effect_codes(battle_id, "P2")
    active_entorno = repo.get_active_effect_codes(battle_id, "ENTORNO")

    # Tags de arma incluidos en estados del jugador para state_outcome_weights.
    # Permite que "pesado", "rapido", etc. afecten el peso de outcomes vía DB.
    def _weapon_tags(state: dict | None) -> list[str]:
        if not state:
            return []
        w = rules.get_weapon(state["weapon_code"])
        return json.loads(w.get("narrative_tags") or "[]") if w else []

    active_p1_full = active_p1 + _weapon_tags(state_p1)
    active_p2_full = active_p2 + _weapon_tags(state_p2)

    # Quién gana el dado (A=P1, B=P2, NONE=empate) — se usa para sesgar el DEFAULT
    dice_leader = "A" if eff_p1 > eff_p2 else ("B" if eff_p2 > eff_p1 else "NONE")

    candidates = rules.get_outcome(action_pair, diff_band, power_context)
    if not candidates:
        candidates = rules.get_outcome(action_pair, "DEFAULT", "DEFAULT")
    if not candidates:
        # Emergencia absoluta (solo si la propia fila DEFAULT falta)
        outcome = {
            "outcome_code": "FALLBACK_EMERGENCIA",
            "phase_winner": "NONE",
            "counter_dmg_A": 0.5,
            "counter_dmg_B": 0.5,
            "effect_A": None,
            "effect_B": None,
            "base_weight": 1.0,
            "narrative_pool_tag": "GENERIC_INTERCAMBIO",
            "is_fatal": 0,
        }
    else:
        outcome = _weighted_choice(
            candidates, battle_id,
            active_p1_full, active_p2_full, active_entorno,
            dice_leader=dice_leader, diff_band=diff_band,
        )

    # ── Paso 6: aplicar efectos ──────────────────────────────────────────────
    # Determinar qué efecto va a P1 (A) y cuál a P2 (B)
    effect_for_p1 = _effect_for_side(outcome, is_player_A=p1_is_A)
    effect_for_p2 = _effect_for_side(outcome, is_player_A=not p1_is_A)

    applied_p1 = _apply_effect(battle_id, "P1", effect_for_p1, phase_abs)
    applied_p2 = _apply_effect(battle_id, "P2", effect_for_p2, phase_abs)

    # ── Bono por banda de diferencia ─────────────────────────────────────────
    # GDD sección 4: el ganador de la fase recibe modificador temporal para
    # la siguiente fase, proporcional a la banda de diferencia.
    # expires_at = phase_abs + 2 → survives expire_effects de la siguiente fase
    # y es visible en _sum_mods cuando se tiran los dados de esa fase.
    if diff_band in _BAND_BONUS_EFFECT and outcome["phase_winner"] in ('A', 'B'):
        winner_side = "P1" if outcome["phase_winner"] == 'A' else "P2"
        band_eff = _BAND_BONUS_EFFECT[diff_band]
        # Eliminar bono de banda previo (solo aplica el más reciente)
        for old_eff in _BAND_BONUS_EFFECT.values():
            repo.remove_effect(battle_id, winner_side, old_eff)
        repo.add_effect(battle_id, winner_side, band_eff, phase_abs + 2, "band_bonus")

    # ── Paso 7: actualizar contadores ────────────────────────────────────────
    dmg_p1 = _counter_dmg_for_side(outcome, is_player_A=p1_is_A)
    dmg_p2 = _counter_dmg_for_side(outcome, is_player_A=not p1_is_A)

    # Escalado de daño por arma: el atacante golpea más fuerte según su tamaño de arma.
    # factor = hits × dmg_per_hit (PEQUEÑA=1.0, MEDIANA=1.0, GRANDE=1.5).
    # Solo se aplica en outcomes no fatales — los fatales ya están calibrados a MAX_COUNTERS.
    if not outcome.get("is_fatal"):
        def _weapon_dmg_factor(state: dict | None) -> float:
            if not state:
                return 1.0
            w = rules.get_weapon(state["weapon_code"])
            return (w["hits"] * w["dmg_per_hit"]) if w else 1.0

        # P2 toma el daño del ataque de P1 → escala por arma de P1
        if dmg_p2 > 0:
            dmg_p2 = round(dmg_p2 * _weapon_dmg_factor(state_p1), 2)
        # P1 toma el daño del ataque de P2 → escala por arma de P2
        if dmg_p1 > 0:
            dmg_p1 = round(dmg_p1 * _weapon_dmg_factor(state_p2), 2)

    new_cnt_p1 = state_p1["counters"] + dmg_p1
    new_cnt_p2 = state_p2["counters"] + dmg_p2

    # DESMEMBRADO: cap de 15 baja a 10 (permanente)
    max_p1 = 10.0 if repo.has_effect(battle_id, "P1", "DESMEMBRADO") else config.MAX_COUNTERS
    max_p2 = 10.0 if repo.has_effect(battle_id, "P2", "DESMEMBRADO") else config.MAX_COUNTERS

    repo.update_counters(battle_id, "P1", min(new_cnt_p1, max_p1))
    repo.update_counters(battle_id, "P2", min(new_cnt_p2, max_p2))

    state_p1 = repo.get_battle_state(battle_id, "P1")
    state_p2 = repo.get_battle_state(battle_id, "P2")

    # Bloquear recovery si recibió crítico (daño ≥ 3.0)
    if dmg_p1 >= 3.0:
        repo.block_recovery(battle_id, "P1", turn + config.RECOVERY_INTERVAL_TURNS)
    if dmg_p2 >= 3.0:
        repo.block_recovery(battle_id, "P2", turn + config.RECOVERY_INTERVAL_TURNS)

    # ── Crits por arma: golpes significativos (≥ 2.5) pueden infligir debuffs extra ──
    # GRANDE (crit_dmg=4.0): 20% → DESMEMBRADO en el receptor
    # MEDIANA (crit_dmg=2.0): 15% → POS_DESFAVORABLE en el receptor
    # PEQUEÑA (crit_dmg=1.0): sin efecto adicional
    phase_events: list[dict] = []
    if not outcome.get("is_fatal"):
        def _try_weapon_crit(attacker_state: dict | None, receptor_side: str, dmg_dealt: float):
            if not attacker_state or dmg_dealt < 2.5:
                return
            w = rules.get_weapon(attacker_state["weapon_code"])
            if not w:
                return
            crit = w.get("crit_dmg", 0.0)
            roll = random.random()
            if crit >= 4.0 and roll < 0.20:   # GRANDE
                applied = _apply_effect(battle_id, receptor_side, "DESMEMBRADO", phase_abs, source="weapon_crit")
                if applied:
                    phase_events.append({"source": "weapon_crit", "side": receptor_side,
                                         "effect": "DESMEMBRADO", "roll": round(roll, 3), "chance": 0.20})
            elif crit >= 2.0 and roll < 0.15:  # MEDIANA
                applied = _apply_effect(battle_id, receptor_side, "POS_DESFAVORABLE", phase_abs, source="weapon_crit")
                if applied:
                    phase_events.append({"source": "weapon_crit", "side": receptor_side,
                                         "effect": "POS_DESFAVORABLE", "roll": round(roll, 3), "chance": 0.15})

        _try_weapon_crit(state_p1, "P2", dmg_p2)
        _try_weapon_crit(state_p2, "P1", dmg_p1)

    # ── Paso 8: acumuladores y racha ─────────────────────────────────────────
    roll_winner_p1 = eff_p1 > eff_p2
    roll_winner_p2 = eff_p2 > eff_p1
    _update_accumulators(battle_id, "P1", "P2", eff_p1, eff_p2, roll_winner_p1, turn)
    _update_accumulators(battle_id, "P2", "P1", eff_p2, eff_p1, roll_winner_p2, turn)

    if eff_p1 == eff_p2:
        roll_winner = "NONE"
    elif eff_p1 > eff_p2:
        roll_winner = "P1"
    else:
        roll_winner = "P2"

    # Recuperación cada 3 turnos completos (solo al final de la fase 3)
    if phase == config.PHASES_PER_TURN:
        _apply_recovery(battle_id, turn)

    # ── Paso 9: narrativa ────────────────────────────────────────────────────
    all_active_effects_p1 = repo.get_active_effects(battle_id, "P1")
    all_active_effects_p2 = repo.get_active_effects(battle_id, "P2")
    all_active_effects_entorno = repo.get_active_effects(battle_id, "ENTORNO")
    all_active_effects = all_active_effects_p1 + all_active_effects_p2 + all_active_effects_entorno

    # Incluir tags de armas y arena para que los templates puedan filtrar por contexto.
    weapon_tags = []
    for ws in (state_p1, state_p2):
        if ws:
            w = rules.get_weapon(ws["weapon_code"])
            if w:
                weapon_tags.extend(json.loads(w.get("narrative_tags") or "[]"))

    arena_tags = []
    if battle.get("arena_code"):
        arena_obj = rules.fetch_one_arena(battle["arena_code"])
        if arena_obj:
            arena_tags = json.loads(arena_obj.get("narrative_tags") or "[]")

    active_tags = collect_active_tags(all_active_effects, list(set(weapon_tags)), arena_tags)
    narrative, narrative_extra = select_narrative(outcome["narrative_pool_tag"], active_tags)

    # ── Efectos narrativos adicionales (probabilísticos desde el template) ────
    narrative_events = _apply_narrative_effects(battle_id, narrative_extra, outcome, phase_abs)
    phase_events.extend(narrative_events)

    # ── Paso 10: verificar condición de fin ──────────────────────────────────
    battle_over = False
    winner = None
    cnt_p1 = state_p1["counters"]
    cnt_p2 = state_p2["counters"]

    if cnt_p1 >= max_p1:
        battle_over = True
        winner = "P2"
        repo.finish_battle(battle_id, "P2")
    elif cnt_p2 >= max_p2:
        battle_over = True
        winner = "P1"
        repo.finish_battle(battle_id, "P1")

    # ── Paso 11: persistir log ───────────────────────────────────────────────
    repo.log_phase(battle_id, {
        "turn_number": turn,
        "phase_number": phase,
        "action_p1": action_p1,
        "action_p2": action_p2,
        "roll_p1": roll_p1,
        "roll_p2": roll_p2,
        "effective_p1": eff_p1,
        "effective_p2": eff_p2,
        "power_p1": power_p1,
        "power_p2": power_p2,
        "difference": difference,
        "difference_band": diff_band,
        "power_context": power_context,
        "action_pair": action_pair,
        "outcome_code": outcome["outcome_code"],
        "phase_winner": outcome["phase_winner"],
        "roll_winner": roll_winner,
        "counter_dmg_p1": dmg_p1,
        "counter_dmg_p2": dmg_p2,
        "counters_p1": cnt_p1,
        "counters_p2": cnt_p2,
        "effect_applied_p1": applied_p1,
        "effect_applied_p2": applied_p2,
        "narrative_text": narrative,
        "narrative_effects_applied": json.dumps(phase_events),
    })

    # Avanzar turn/phase
    if not battle_over:
        next_phase = phase + 1
        next_turn = turn
        if next_phase > config.PHASES_PER_TURN:
            next_phase = 1
            next_turn = turn + 1
        repo.update_battle_turn(battle_id, next_turn, next_phase)

    return PhaseResult(
        battle_id=battle_id,
        turn_number=turn,
        phase_number=phase,
        action_p1=action_p1,
        action_p2=action_p2,
        roll_p1=roll_p1,
        roll_p2=roll_p2,
        effective_p1=eff_p1,
        effective_p2=eff_p2,
        power_p1=power_p1,
        power_p2=power_p2,
        difference=difference,
        difference_band=diff_band,
        power_context=power_context,
        action_pair=action_pair,
        outcome_code=outcome["outcome_code"],
        phase_winner=outcome["phase_winner"],
        roll_winner=roll_winner,
        counter_dmg_p1=dmg_p1,
        counter_dmg_p2=dmg_p2,
        counters_p1=cnt_p1,
        counters_p2=cnt_p2,
        effect_applied_p1=applied_p1,
        effect_applied_p2=applied_p2,
        narrative_text=narrative,
        battle_over=battle_over,
        winner=winner,
    )
