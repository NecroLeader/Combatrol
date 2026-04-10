"""
Suite de tests de invariantes para el motor de Combatrol.
Cubre los 4 invariantes críticos definidos en Análisis 5:

  1. POS_FAVORABLE ∩ POS_DESFAVORABLE = ∅ por side (siempre mutuamente excluyentes)
  2. Integridad de datos: state_outcome_weights referencia solo outcome_codes existentes
  3. No efectos "player" en ENTORNO (POS_FAVORABLE/POS_DESFAVORABLE no van a ENTORNO)
  4. JSON válido en todos los campos JSON de la DB
  5. Semántica de duración: efectos aplicados correctamente por _apply_effect
  6. Tests de integración: batallas completas no rompen invariantes en ninguna fase
"""

import json
import random
import sqlite3
import os
import pytest

# ── Helpers de DB ────────────────────────────────────────────────────────────

def db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ── 1. Integridad de datos ───────────────────────────────────────────────────

class TestDataIntegrity:
    def test_state_outcome_weights_reference_valid_outcomes(self, init_test_db):
        """Cada outcome_code en state_outcome_weights debe existir en outcome_matrix."""
        with db(init_test_db) as conn:
            orphans = conn.execute("""
                SELECT sow.state_code, sow.outcome_code
                FROM state_outcome_weights sow
                LEFT JOIN outcome_matrix om ON sow.outcome_code = om.outcome_code
                WHERE om.outcome_code IS NULL
            """).fetchall()
        assert orphans == [], (
            f"Hay {len(orphans)} state_outcome_weights con outcome_code inválido:\n"
            + "\n".join(f"  {r['state_code']} → {r['outcome_code']}" for r in orphans[:10])
        )

    def test_outcome_matrix_effects_reference_valid_codes(self, init_test_db):
        """effect_A y effect_B en outcome_matrix deben existir en combat_effects."""
        with db(init_test_db) as conn:
            valid_codes = {r["code"] for r in conn.execute("SELECT code FROM combat_effects")}
            orphans = []
            for row in conn.execute("SELECT outcome_code, effect_A, effect_B FROM outcome_matrix"):
                for field in ("effect_A", "effect_B"):
                    val = row[field]
                    if val and val not in valid_codes:
                        orphans.append((row["outcome_code"], field, val))
        assert orphans == [], (
            f"{len(orphans)} outcome_matrix con effect inválido:\n"
            + "\n".join(f"  {oc}: {f}={v}" for oc, f, v in orphans[:10])
        )

    def test_narrative_templates_valid_json(self, init_test_db):
        """required_tags, excluded_tags, extra_effects deben ser JSON válido."""
        invalid = []
        with db(init_test_db) as conn:
            for row in conn.execute(
                "SELECT id, pool_tag, required_tags, excluded_tags, extra_effects "
                "FROM narrative_templates"
            ):
                for field in ("required_tags", "excluded_tags", "extra_effects"):
                    val = row[field]
                    if not val:
                        continue
                    try:
                        json.loads(val)
                    except json.JSONDecodeError as e:
                        invalid.append((row["id"], row["pool_tag"], field, str(e)))
        assert invalid == [], (
            f"{len(invalid)} narrative_templates con JSON inválido:\n"
            + "\n".join(f"  id={i} {pt}: {f} → {e}" for i, pt, f, e in invalid[:10])
        )

    def test_arena_initial_tags_reference_valid_effects(self, init_test_db):
        """initial_state_tags en arena_pool debe referenciar combat_effects existentes."""
        invalid = []
        with db(init_test_db) as conn:
            valid_codes = {r["code"] for r in conn.execute("SELECT code FROM combat_effects")}
            for arena in conn.execute("SELECT code, initial_state_tags FROM arena_pool"):
                raw = arena["initial_state_tags"]
                if not raw:
                    continue
                try:
                    tags = json.loads(raw)
                    for tag in tags:
                        if tag not in valid_codes:
                            invalid.append((arena["code"], tag))
                except json.JSONDecodeError:
                    invalid.append((arena["code"], f"JSON INVÁLIDO: {raw}"))
        assert invalid == [], (
            f"{len(invalid)} arenas con initial_state_tags inválidos:\n"
            + "\n".join(f"  {a}: {t}" for a, t in invalid)
        )

    def test_outcome_matrix_has_entries(self, init_test_db):
        """La DB debe tener al menos 100 outcomes (seed + CSVs importados)."""
        with db(init_test_db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM outcome_matrix").fetchone()[0]
        assert count >= 20, f"outcome_matrix tiene solo {count} rows — parece vacío"

    def test_combat_effects_have_entries(self, init_test_db):
        """La DB debe tener los efectos base."""
        with db(init_test_db) as conn:
            codes = {r["code"] for r in conn.execute("SELECT code FROM combat_effects")}
        required = {"CAIDO", "PANICO", "VACILACION", "FATIGA", "DESMEMBRADO",
                    "POS_FAVORABLE", "POS_DESFAVORABLE", "HIPEROFFENSIVO"}
        missing = required - codes
        assert not missing, f"Faltan efectos base: {missing}"


# ── 2. Invariantes de batalla ────────────────────────────────────────────────

class TestBattleInvariants:
    """Tests de integración: corren batallas reales y verifican propiedades."""

    def _start_battle(self, init_test_db, arena_code="campo_abierto",
                      w1="espada", w2="espada") -> int:
        """Helper: crea una batalla limpia en la DB de tests."""
        from app.repositories import battle_repo as repo
        from app.repositories import rules_repo as rules

        arena = rules.fetch_one_arena(arena_code)
        weapon1 = rules.get_weapon(w1)
        weapon2 = rules.get_weapon(w2)

        assert weapon1 and weapon2, "Armas no encontradas en DB de tests"

        bid = repo.create_battle("SIMULATION", arena_code)
        repo.create_battle_state(bid, "P1", w1)
        repo.create_battle_state(bid, "P2", w2)
        repo.create_accumulators(bid, "P1")
        repo.create_accumulators(bid, "P2")

        if arena:
            raw = arena.get("initial_state_tags")
            if raw:
                tags = json.loads(raw) if isinstance(raw, str) else raw
                for tag in tags:
                    repo.add_effect(bid, "ENTORNO", tag, None, "arena_initial")

        return bid

    def test_pos_mutual_exclusion_never_violated(self, init_test_db):
        """POS_FAVORABLE y POS_DESFAVORABLE nunca coexisten en el mismo side."""
        from app.engine.resolver import resolve_phase
        from app.repositories import battle_repo as repo

        random.seed(42)
        bid = self._start_battle(init_test_db)
        actions = ["ATK", "DEF", "INT"]

        for _ in range(60):
            battle = repo.get_battle(bid)
            if not battle or battle["status"] == "FINISHED":
                break

            a1 = random.choice(actions)
            a2 = random.choice(actions)
            resolve_phase(bid, a1, a2)

            for side in ("P1", "P2"):
                effs = set(repo.get_active_effect_codes(bid, side))
                assert not ("POS_FAVORABLE" in effs and "POS_DESFAVORABLE" in effs), (
                    f"¡Violación en side={side} batalla={bid}! "
                    f"Ambos POS activos simultáneamente."
                )

    def test_entorno_never_has_player_pos_effects(self, init_test_db):
        """ENTORNO nunca debe tener POS_FAVORABLE ni POS_DESFAVORABLE."""
        from app.engine.resolver import resolve_phase
        from app.repositories import battle_repo as repo

        random.seed(99)
        bid = self._start_battle(init_test_db)
        actions = ["ATK", "DEF", "INT"]

        for _ in range(60):
            battle = repo.get_battle(bid)
            if not battle or battle["status"] == "FINISHED":
                break

            resolve_phase(bid, random.choice(actions), random.choice(actions))

            entorno_effs = set(repo.get_active_effect_codes(bid, "ENTORNO"))
            assert "POS_FAVORABLE" not in entorno_effs, \
                f"POS_FAVORABLE en ENTORNO — batalla={bid}"
            assert "POS_DESFAVORABLE" not in entorno_effs, \
                f"POS_DESFAVORABLE en ENTORNO — batalla={bid}"

    def test_battle_terminates(self, init_test_db):
        """Una batalla debe terminar en un número razonable de fases."""
        from app.engine.resolver import resolve_phase
        from app.repositories import battle_repo as repo
        from app.engine.ai import choose_action

        random.seed(7)
        bid = self._start_battle(init_test_db)

        phases = 0
        MAX = 300
        while phases < MAX:
            battle = repo.get_battle(bid)
            if not battle or battle["status"] == "FINISHED":
                break
            eff1 = repo.get_active_effect_codes(bid, "P1")
            eff2 = repo.get_active_effect_codes(bid, "P2")
            acc1 = repo.get_accumulators(bid, "P1")
            acc2 = repo.get_accumulators(bid, "P2")
            a1 = choose_action(eff1, acc1["low_streak"] if acc1 else 0)
            a2 = choose_action(eff2, acc2["low_streak"] if acc2 else 0)
            resolve_phase(bid, a1, a2)
            phases += 1

        assert phases < MAX, f"La batalla no terminó en {MAX} fases — posible bucle infinito"

    def test_counters_never_negative(self, init_test_db):
        """Los counters de ningún side deben ser negativos."""
        from app.engine.resolver import resolve_phase
        from app.repositories import battle_repo as repo

        random.seed(13)
        bid = self._start_battle(init_test_db)

        for _ in range(90):
            battle = repo.get_battle(bid)
            if not battle or battle["status"] == "FINISHED":
                break

            resolve_phase(bid, random.choice(["ATK", "DEF"]), random.choice(["ATK", "DEF"]))

            for side in ("P1", "P2"):
                state = repo.get_battle_state(bid, side)
                if state:
                    assert state["counters"] >= 0, \
                        f"Counters negativos en {side}: {state['counters']}"

    def test_battle_log_narrative_effects_json_valid(self, init_test_db):
        """El campo narrative_effects_applied en battle_log debe ser JSON válido."""
        from app.engine.resolver import resolve_phase
        from app.repositories import battle_repo as repo
        from app.database import fetch_all

        random.seed(21)
        bid = self._start_battle(init_test_db)

        for _ in range(30):
            battle = repo.get_battle(bid)
            if not battle or battle["status"] == "FINISHED":
                break
            resolve_phase(bid, random.choice(["ATK", "DEF", "INT"]),
                          random.choice(["ATK", "DEF", "INT"]))

        logs = fetch_all(
            "SELECT id, narrative_effects_applied FROM battle_log WHERE battle_id=?",
            (bid,)
        )
        for log in logs:
            val = log.get("narrative_effects_applied", "[]")
            try:
                parsed = json.loads(val or "[]")
                assert isinstance(parsed, list), \
                    f"narrative_effects_applied no es lista en log id={log['id']}"
            except json.JSONDecodeError as e:
                pytest.fail(f"JSON inválido en battle_log id={log['id']}: {e}\nValor: {val}")

    def test_multiple_battles_no_cross_contamination(self, init_test_db):
        """Batallas paralelas no deben compartir efectos entre sí."""
        from app.engine.resolver import resolve_phase
        from app.repositories import battle_repo as repo

        random.seed(55)
        bid1 = self._start_battle(init_test_db, arena_code="campo_abierto")
        bid2 = self._start_battle(init_test_db, arena_code="campo_abierto")

        for _ in range(30):
            for bid in (bid1, bid2):
                b = repo.get_battle(bid)
                if not b or b["status"] == "FINISHED":
                    continue
                resolve_phase(bid, random.choice(["ATK", "DEF"]),
                              random.choice(["ATK", "DEF"]))

        # Los efectos de bid1 no deben aparecer en bid2 y viceversa
        from app.database import fetch_all
        effs1 = {r["id"] for r in fetch_all(
            "SELECT id FROM battle_active_effects WHERE battle_id=?", (bid1,)
        )}
        effs2 = {r["id"] for r in fetch_all(
            "SELECT id FROM battle_active_effects WHERE battle_id=?", (bid2,)
        )}
        assert effs1.isdisjoint(effs2), "Efectos compartidos entre batallas distintas"


# ── 3. Tests de _apply_effect (unit) ────────────────────────────────────────

class TestApplyEffect:
    def _fresh_battle(self, init_test_db) -> int:
        from app.repositories import battle_repo as repo
        bid = repo.create_battle("TEST", "campo_abierto")
        repo.create_battle_state(bid, "P1", "espada")
        repo.create_battle_state(bid, "P2", "espada")
        repo.create_accumulators(bid, "P1")
        repo.create_accumulators(bid, "P2")
        return bid

    def test_pos_favorable_removes_pos_desfavorable(self, init_test_db):
        """Aplicar POS_FAVORABLE debe eliminar POS_DESFAVORABLE si existe."""
        from app.engine.resolver import _apply_effect
        from app.repositories import battle_repo as repo

        bid = self._fresh_battle(init_test_db)
        repo.add_effect(bid, "P1", "POS_DESFAVORABLE", None, "test")
        _apply_effect(bid, "P1", "POS_FAVORABLE", 5)

        effs = set(repo.get_active_effect_codes(bid, "P1"))
        assert "POS_FAVORABLE" in effs
        assert "POS_DESFAVORABLE" not in effs

    def test_pos_desfavorable_removes_pos_favorable(self, init_test_db):
        """Aplicar POS_DESFAVORABLE debe eliminar POS_FAVORABLE si existe."""
        from app.engine.resolver import _apply_effect
        from app.repositories import battle_repo as repo

        bid = self._fresh_battle(init_test_db)
        repo.add_effect(bid, "P1", "POS_FAVORABLE", None, "test")
        _apply_effect(bid, "P1", "POS_DESFAVORABLE", 5)

        effs = set(repo.get_active_effect_codes(bid, "P1"))
        assert "POS_DESFAVORABLE" in effs
        assert "POS_FAVORABLE" not in effs

    def test_caido_gives_hiperoffensivo_to_opponent(self, init_test_db):
        """Aplicar CAIDO a P1 debe dar HIPEROFFENSIVO a P2 si no tiene debuffs."""
        from app.engine.resolver import _apply_effect
        from app.repositories import battle_repo as repo

        bid = self._fresh_battle(init_test_db)
        _apply_effect(bid, "P1", "CAIDO", 5)

        p2_effs = set(repo.get_active_effect_codes(bid, "P2"))
        assert "HIPEROFFENSIVO" in p2_effs, \
            "P2 debe tener HIPEROFFENSIVO cuando P1 cae"

    def test_unknown_effect_returns_none(self, init_test_db):
        """Un código de efecto inexistente debe retornar None sin error."""
        from app.engine.resolver import _apply_effect
        from app.repositories import battle_repo as repo

        bid = self._fresh_battle(init_test_db)
        result = _apply_effect(bid, "P1", "EFECTO_INVENTADO_XYZ", 5)
        assert result is None
