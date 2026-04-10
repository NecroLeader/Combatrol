#!/usr/bin/env python3
"""
Harness de simulación batch para Combatrol.
Corre N batallas completas con IA y exporta métricas a CSV.

Uso:
  python scripts/simulate_batch.py [--battles 100] [--output metrics.csv] [--arena precipicio]

Métricas exportadas (una fila por batalla):
  battle_id, arena, weapon_p1, weapon_p2, winner, total_phases, total_turns,
  counters_p1_final, counters_p2_final,
  fatal_phases, effect_counts_* (por efecto), narrative_event_counts,
  weapon_crit_count, avg_dmg_p1, avg_dmg_p2,
  first_major_debuff_phase, lead_changes, max_lead
"""

import sys
import csv
import json
import random
import argparse
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine.resolver import resolve_phase
from app.engine.ai import choose_action
from app.repositories import battle_repo as repo
from app.repositories import rules_repo as rules
from app.config import DB_PATH


TRACKED_EFFECTS = [
    "CAIDO", "DESMEMBRADO", "PANICO", "VACILACION", "FATIGA",
    "POS_FAVORABLE", "POS_DESFAVORABLE", "DESARMADO", "HIPEROFFENSIVO",
]


def run_battle(arena_code: str | None, w1: str | None, w2: str | None) -> dict:
    """Corre una batalla completa con IA y retorna métricas."""
    # Setup
    if arena_code:
        arena = rules.fetch_one_arena(arena_code)
    else:
        arena = rules.get_random_arena()
    arena_code_used = arena["code"] if arena else None

    weapon1 = rules.get_weapon(w1) if w1 else rules.get_random_weapon()
    weapon2 = rules.get_weapon(w2) if w2 else rules.get_random_weapon()

    if not weapon1 or not weapon2:
        raise RuntimeError("No hay armas disponibles.")

    battle_id = repo.create_battle("SIMULATION", arena_code_used)
    repo.create_battle_state(battle_id, "P1", weapon1["code"])
    repo.create_battle_state(battle_id, "P2", weapon2["code"])
    repo.create_accumulators(battle_id, "P1")
    repo.create_accumulators(battle_id, "P2")

    if arena:
        raw_tags = arena.get("initial_state_tags")
        if raw_tags:
            tags = json.loads(raw_tags) if isinstance(raw_tags, str) else raw_tags
            for tag in tags:
                repo.add_effect(battle_id, "ENTORNO", tag, None, "arena_initial")

    # Metrics accumulators
    total_phases = 0
    total_dmg_p1 = 0.0
    total_dmg_p2 = 0.0
    fatal_phases = 0
    effect_counts = defaultdict(int)
    narrative_event_count = 0
    weapon_crit_count = 0
    outcome_codes = []

    first_major_debuff_phase = None
    lead_changes = 0
    max_lead = 0.0
    prev_leader = None

    # Run battle
    MAX_PHASES = 200  # safety cap
    while total_phases < MAX_PHASES:
        battle = repo.get_battle(battle_id)
        if not battle or battle["status"] == "FINISHED":
            break

        eff_p1 = repo.get_active_effect_codes(battle_id, "P1")
        eff_p2 = repo.get_active_effect_codes(battle_id, "P2")
        acc_p1 = repo.get_accumulators(battle_id, "P1")
        acc_p2 = repo.get_accumulators(battle_id, "P2")

        a1 = choose_action(eff_p1, acc_p1["low_streak"] if acc_p1 else 0)
        a2 = choose_action(eff_p2, acc_p2["low_streak"] if acc_p2 else 0)

        result = resolve_phase(battle_id, a1, a2)
        total_phases += 1
        total_dmg_p1 += result.counter_dmg_p1
        total_dmg_p2 += result.counter_dmg_p2
        outcome_codes.append(result.outcome_code)

        # Track snowball metrics
        s1 = repo.get_battle_state(battle_id, "P1")
        s2 = repo.get_battle_state(battle_id, "P2")
        if s1 and s2:
            lead = abs(s1["counters"] - s2["counters"])
            if lead > max_lead:
                max_lead = lead
            leader = "P1" if s1["counters"] > s2["counters"] else ("P2" if s2["counters"] > s1["counters"] else "TIE")
            if prev_leader is not None and leader != prev_leader and leader != "TIE" and prev_leader != "TIE":
                lead_changes += 1
            prev_leader = leader

        # First major debuff
        if first_major_debuff_phase is None:
            major = {"CAIDO", "DESMEMBRADO", "DESARMADO"}
            for side in ("P1", "P2"):
                effs = set(repo.get_active_effect_codes(battle_id, side))
                if major & effs:
                    first_major_debuff_phase = total_phases
                    break

        # Count fatal outcomes
        om_row = _get_outcome(result.outcome_code)
        if om_row and om_row.get("is_fatal"):
            fatal_phases += 1

        # Count effects applied this phase
        for eff in TRACKED_EFFECTS:
            if result.effect_applied_p1 == eff or result.effect_applied_p2 == eff:
                effect_counts[eff] += 1

        # Count narrative/crit events from log
        log_row = _get_last_log(battle_id)
        if log_row:
            evts = json.loads(log_row.get("narrative_effects_applied", "[]") or "[]")
            for evt in evts:
                if evt.get("source") == "weapon_crit":
                    weapon_crit_count += 1
                else:
                    narrative_event_count += 1

        if result.battle_over:
            break

    # Final state
    battle = repo.get_battle(battle_id)
    state_p1 = repo.get_battle_state(battle_id, "P1")
    state_p2 = repo.get_battle_state(battle_id, "P2")

    winner = battle["winner_side"] if battle else None
    total_turns = (total_phases + 2) // 3

    row = {
        "battle_id": battle_id,
        "arena": arena_code_used or "random",
        "weapon_p1": weapon1["code"],
        "weapon_p2": weapon2["code"],
        "winner": winner or "NONE",
        "total_phases": total_phases,
        "total_turns": total_turns,
        "fatal_phases": fatal_phases,
        "counters_p1_final": state_p1["counters"] if state_p1 else 0,
        "counters_p2_final": state_p2["counters"] if state_p2 else 0,
        "avg_dmg_p1": round(total_dmg_p1 / total_phases, 3) if total_phases else 0,
        "avg_dmg_p2": round(total_dmg_p2 / total_phases, 3) if total_phases else 0,
        "narrative_events": narrative_event_count,
        "weapon_crits": weapon_crit_count,
        "fatal_rate": round(fatal_phases / total_phases, 3) if total_phases else 0,
        "hit_cap": 1 if total_phases >= MAX_PHASES else 0,
        "first_major_debuff_phase": first_major_debuff_phase or 0,
        "lead_changes": lead_changes,
        "max_lead": round(max_lead, 2),
    }
    for eff in TRACKED_EFFECTS:
        row[f"eff_{eff.lower()}"] = effect_counts.get(eff, 0)

    return row


def _get_outcome(outcome_code: str) -> dict | None:
    from app.database import fetch_one
    return fetch_one("SELECT * FROM outcome_matrix WHERE outcome_code=?", (outcome_code,))


def _get_last_log(battle_id: int) -> dict | None:
    from app.database import fetch_one
    return fetch_one(
        "SELECT * FROM battle_log WHERE battle_id=? ORDER BY id DESC LIMIT 1",
        (battle_id,)
    )


def main():
    parser = argparse.ArgumentParser(description="Combatrol batch simulation")
    parser.add_argument("--battles", type=int, default=100, help="Número de batallas (default: 100)")
    parser.add_argument("--output", default="metrics.csv", help="Archivo CSV de salida (default: metrics.csv)")
    parser.add_argument("--arena", default=None, help="Arena fija (o random si no se especifica)")
    parser.add_argument("--weapon-p1", default=None, dest="w1")
    parser.add_argument("--weapon-p2", default=None, dest="w2")
    parser.add_argument("--seed", type=int, default=None, help="Semilla RNG para reproducibilidad")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    print(f"[simulate_batch] Corriendo {args.battles} batallas...")
    print(f"  DB: {DB_PATH}")
    print(f"  Arena: {args.arena or 'random'}")
    print(f"  Weapons: {args.w1 or 'random'} vs {args.w2 or 'random'}")
    print()

    rows = []
    p1_wins = 0
    p2_wins = 0
    for i in range(args.battles):
        try:
            row = run_battle(args.arena, args.w1, args.w2)
            rows.append(row)
            if row["winner"] == "P1":
                p1_wins += 1
            elif row["winner"] == "P2":
                p2_wins += 1
            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{args.battles} batallas completadas...")
        except Exception as e:
            print(f"  [ERROR] Batalla {i + 1}: {e}")

    if not rows:
        print("Sin datos — no se generó CSV.")
        return

    # Escribir CSV
    fieldnames = list(rows[0].keys())
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Resumen en consola
    n = len(rows)
    avg_phases = sum(r["total_phases"] for r in rows) / n
    avg_turns  = sum(r["total_turns"] for r in rows) / n
    avg_fatal  = sum(r["fatal_rate"] for r in rows) / n
    avg_crits  = sum(r["weapon_crits"] for r in rows) / n
    avg_narr   = sum(r["narrative_events"] for r in rows) / n
    cap_count  = sum(r["hit_cap"] for r in rows)

    print()
    print("=" * 50)
    print(f"RESULTADOS ({n} batallas)")
    print("=" * 50)
    print(f"  P1 wins: {p1_wins} ({100*p1_wins/n:.1f}%)")
    print(f"  P2 wins: {p2_wins} ({100*p2_wins/n:.1f}%)")
    print(f"  Avg fases/batalla:  {avg_phases:.1f}")
    print(f"  Avg turnos/batalla: {avg_turns:.1f}")
    print(f"  Avg fatal_rate:     {avg_fatal:.3f}")
    print(f"  Avg weapon_crits:   {avg_crits:.2f}")
    print(f"  Avg narrative_evts: {avg_narr:.2f}")
    avg_lead_changes = sum(r["lead_changes"] for r in rows) / n
    avg_first_debuff = sum(r["first_major_debuff_phase"] for r in rows if r["first_major_debuff_phase"] > 0)
    print(f"  Avg lead_changes:   {avg_lead_changes:.2f}")
    if cap_count:
        print(f"  ⚠ {cap_count} batallas alcanzaron el cap de 200 fases (sin fin)")
    print(f"\nCSV guardado: {args.output}")
    print("=" * 50)


if __name__ == "__main__":
    main()
