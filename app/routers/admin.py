"""Endpoints de administración: leer/editar tablas de reglas."""

from fastapi import APIRouter, HTTPException
from app.database import fetch_all, fetch_one, execute

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/weapons")
def list_weapons():
    return fetch_all(
        "SELECT w.code, w.name, w.size_code, ws.hits, ws.dmg_per_hit, ws.crit_dmg "
        "FROM weapons w JOIN weapon_sizes ws ON w.size_code=ws.size_code"
    )


@router.get("/effects")
def list_effects():
    return fetch_all("SELECT * FROM combat_effects ORDER BY code")


@router.get("/outcome_matrix")
def list_outcomes(pair: str | None = None):
    if pair:
        return fetch_all(
            "SELECT * FROM outcome_matrix WHERE action_pair=? ORDER BY difference_band, power_context",
            (pair,)
        )
    return fetch_all("SELECT * FROM outcome_matrix ORDER BY action_pair, difference_band, power_context")


@router.get("/narrative_templates")
def list_templates(pool_tag: str | None = None):
    if pool_tag:
        return fetch_all(
            "SELECT * FROM narrative_templates WHERE pool_tag=?", (pool_tag,)
        )
    return fetch_all("SELECT * FROM narrative_templates ORDER BY pool_tag")


@router.get("/arena")
def list_arenas():
    return fetch_all("SELECT * FROM arena_pool")


@router.get("/dice_power")
def list_dice_power():
    return fetch_all("SELECT * FROM core_dice_power ORDER BY min_value")


@router.get("/difference_bands")
def list_bands():
    return fetch_all("SELECT * FROM core_difference_band ORDER BY min_diff")
