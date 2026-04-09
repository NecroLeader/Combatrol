from fastapi import APIRouter, HTTPException
from app.schemas.battle import BattleStartRequest, BattlePhaseRequest, PhaseResult, SimulateTurnRequest
from app.repositories import battle_repo as repo
from app.repositories import rules_repo as rules
from app.engine.resolver import resolve_phase
from app.engine.ai import choose_action

router = APIRouter(prefix="/battle", tags=["battle"])


@router.post("/start")
def start_battle(payload: BattleStartRequest) -> dict:
    # Arena
    if payload.arena_code:
        arena = rules.fetch_one_arena(payload.arena_code)
    else:
        arena = rules.get_random_arena()

    arena_code = arena["code"] if arena else None

    # Armas
    w1 = rules.get_weapon(payload.weapon_p1) if payload.weapon_p1 else rules.get_random_weapon()
    w2 = rules.get_weapon(payload.weapon_p2) if payload.weapon_p2 else rules.get_random_weapon()

    if not w1 or not w2:
        raise HTTPException(status_code=400, detail="No hay armas disponibles en la DB.")

    battle_id = repo.create_battle(payload.mode, arena_code)
    repo.create_battle_state(battle_id, "P1", w1["code"])
    repo.create_battle_state(battle_id, "P2", w2["code"])
    repo.create_accumulators(battle_id, "P1")
    repo.create_accumulators(battle_id, "P2")

    return {
        "battle_id": battle_id,
        "mode": payload.mode,
        "arena": arena_code,
        "p1": {"name": payload.name_p1, "weapon": w1["name"]},
        "p2": {"name": payload.name_p2, "weapon": w2["name"]},
    }


@router.get("/{battle_id}")
def get_battle(battle_id: int) -> dict:
    battle = repo.get_battle(battle_id)
    if not battle:
        raise HTTPException(status_code=404, detail="Batalla no encontrada.")

    state_p1 = repo.get_battle_state(battle_id, "P1")
    state_p2 = repo.get_battle_state(battle_id, "P2")
    effects_p1 = repo.get_active_effect_codes(battle_id, "P1")
    effects_p2 = repo.get_active_effect_codes(battle_id, "P2")
    effects_entorno = repo.get_active_effect_codes(battle_id, "ENTORNO")
    acc_p1 = repo.get_accumulators(battle_id, "P1")
    acc_p2 = repo.get_accumulators(battle_id, "P2")

    return {
        "battle": dict(battle),
        "p1": {
            "state": dict(state_p1) if state_p1 else None,
            "effects": effects_p1,
            "accumulators": dict(acc_p1) if acc_p1 else None,
        },
        "p2": {
            "state": dict(state_p2) if state_p2 else None,
            "effects": effects_p2,
            "accumulators": dict(acc_p2) if acc_p2 else None,
        },
        "entorno": effects_entorno,
    }


@router.post("/{battle_id}/phase")
def do_phase(battle_id: int, payload: BattlePhaseRequest) -> PhaseResult:
    battle = repo.get_battle(battle_id)
    if not battle:
        raise HTTPException(status_code=404, detail="Batalla no encontrada.")
    if battle["status"] == "FINISHED":
        raise HTTPException(status_code=409, detail="La batalla ya terminó.")

    return resolve_phase(battle_id, payload.action_p1, payload.action_p2)


@router.post("/{battle_id}/simulate")
def simulate_turn(battle_id: int, payload: SimulateTurnRequest = None) -> dict:
    """
    Resuelve las 3 fases de un turno.
    - SIMULATION: sin payload → IA elige para ambos
    - PVE:        payload.p1_actions → IA elige solo para P2
    - PVP:        payload.p1_actions + payload.p2_actions
    """
    if payload is None:
        payload = SimulateTurnRequest()

    battle = repo.get_battle(battle_id)
    if not battle:
        raise HTTPException(status_code=404, detail="Batalla no encontrada.")
    if battle["status"] == "FINISHED":
        raise HTTPException(status_code=409, detail="La batalla ya terminó.")

    results = []
    for i in range(3):
        b = repo.get_battle(battle_id)
        if b["status"] == "FINISHED":
            break

        eff_p1 = repo.get_active_effect_codes(battle_id, "P1")
        eff_p2 = repo.get_active_effect_codes(battle_id, "P2")
        acc_p1 = repo.get_accumulators(battle_id, "P1")
        acc_p2 = repo.get_accumulators(battle_id, "P2")

        a1 = payload.p1_actions[i] if payload.p1_actions else choose_action(eff_p1, acc_p1["low_streak"] if acc_p1 else 0)
        a2 = payload.p2_actions[i] if payload.p2_actions else choose_action(eff_p2, acc_p2["low_streak"] if acc_p2 else 0)

        result = resolve_phase(battle_id, a1, a2)
        results.append(result.model_dump())

        if result.battle_over:
            break

    return {"phases": results}


@router.get("/{battle_id}/log")
def get_log(battle_id: int) -> dict:
    log = repo.get_battle_log(battle_id)
    return {"battle_id": battle_id, "log": log}
