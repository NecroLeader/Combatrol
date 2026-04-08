from pydantic import BaseModel
from typing import Literal, Optional


class BattleStartRequest(BaseModel):
    mode: Literal["SIMULATION", "PVE", "PVP"] = "SIMULATION"
    arena_code: Optional[str] = None        # None = random
    weapon_p1: Optional[str] = None         # None = random
    weapon_p2: Optional[str] = None         # None = random
    name_p1: str = "P1"
    name_p2: str = "P2"


class BattlePhaseRequest(BaseModel):
    action_p1: Literal["ATK", "DEF", "INT"]
    action_p2: Literal["ATK", "DEF", "INT"]


class PhaseResult(BaseModel):
    battle_id: int
    turn_number: int
    phase_number: int
    action_p1: str
    action_p2: str
    roll_p1: int
    roll_p2: int
    effective_p1: float
    effective_p2: float
    power_p1: int
    power_p2: int
    difference: float
    difference_band: str
    power_context: str
    action_pair: str
    outcome_code: str
    phase_winner: str
    roll_winner: str
    counter_dmg_p1: float
    counter_dmg_p2: float
    counters_p1: float
    counters_p2: float
    effect_applied_p1: Optional[str]
    effect_applied_p2: Optional[str]
    narrative_text: str
    battle_over: bool
    winner: Optional[str]
