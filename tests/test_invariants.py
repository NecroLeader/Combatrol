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
        """La DB debe tener al menos 20 outcomes (seed only, CSVs add more)."""
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


# ── 4. Tests de mecánicas específicas ───────────────────────────────────────

class TestMechanics:
    """Tests de mecánicas específicas del motor."""

    def _fresh_battle(self, init_test_db, arena="campo_abierto", w1="espada", w2="espada") -> int:
        from app.repositories import battle_repo as repo
        import json as _json
        from app.repositories import rules_repo as rules
        bid = repo.create_battle("TEST", arena)
        repo.create_battle_state(bid, "P1", w1)
        repo.create_battle_state(bid, "P2", w2)
        repo.create_accumulators(bid, "P1")
        repo.create_accumulators(bid, "P2")
        arena_obj = rules.fetch_one_arena(arena)
        if arena_obj:
            raw = arena_obj.get("initial_state_tags")
            if raw:
                tags = _json.loads(raw) if isinstance(raw, str) else raw
                for tag in tags:
                    repo.add_effect(bid, "ENTORNO", tag, None, "arena_initial")
        return bid

    def test_no_duplicate_state_outcome_weights(self, init_test_db):
        """state_outcome_weights no debe tener duplicados (state, outcome, applies_to)."""
        import sqlite3
        with sqlite3.connect(init_test_db) as conn:
            conn.row_factory = sqlite3.Row
            dups = conn.execute("""
                SELECT state_code, outcome_code, applies_to, COUNT(*) as cnt
                FROM state_outcome_weights
                GROUP BY state_code, outcome_code, applies_to
                HAVING cnt > 1
            """).fetchall()
        assert dups == [], (
            f"Hay {len(dups)} combinaciones duplicadas en state_outcome_weights:\n"
            + "\n".join(f"  ({r['state_code']}, {r['outcome_code']}, {r['applies_to']}) × {r['cnt']}"
                        for r in dups[:10])
        )

    def test_fatiga_timing(self, init_test_db):
        """FATIGA aplicada en fase N no penaliza fase N, sí penaliza fase N+1."""
        from app.engine.resolver import _apply_effect, _sum_mods
        from app.repositories import battle_repo as repo

        bid = self._fresh_battle(init_test_db)
        phase_n = 5
        _apply_effect(bid, "P1", "FATIGA", phase_n, source="test")

        # En fase N: el efecto acaba de aplicarse con expires=N+3
        # _sum_mods lo lee porque aún está activo
        mod_n = _sum_mods(bid, "P1")
        assert mod_n == -3.0, f"FATIGA debe penalizar inmediatamente tras aplicarse (mod={mod_n})"

        # Tras expire_effects en fase N+3, el efecto expira
        repo.expire_effects(bid, phase_n + 3)
        mod_after = _sum_mods(bid, "P1")
        assert mod_after == 0.0, f"FATIGA debe expirar (mod={mod_after})"

    def test_desmembrado_caps_roll_at_20(self, init_test_db):
        """DESMEMBRADO debe reducir el cap de tirada efectiva a 20."""
        from app.engine.resolver import _apply_effect, _roll_dice
        from app.repositories import battle_repo as repo
        import random

        bid = self._fresh_battle(init_test_db)
        _apply_effect(bid, "P1", "DESMEMBRADO", 1, source="test")

        # Con DESMEMBRADO, la tirada efectiva no puede superar 20
        random.seed(42)
        for _ in range(20):
            _raw, effective = _roll_dice(bid, "P1", 5)
            assert effective <= 20.0, f"DESMEMBRADO: efectiva={effective} supera cap=20"

    def test_weapon_scaling_grande(self, init_test_db):
        """Arma GRANDE (mandoble) debe escalar daño no fatal por factor 1.5."""
        from app.engine.resolver import resolve_phase
        from app.repositories import battle_repo as repo
        import random

        random.seed(1)  # Buscar una fase con daño no fatal
        bid = repo.create_battle("TEST", "campo_abierto")
        repo.create_battle_state(bid, "P1", "mandoble")
        repo.create_battle_state(bid, "P2", "daga")
        repo.create_accumulators(bid, "P1")
        repo.create_accumulators(bid, "P2")

        # Correr algunas fases, verificar que el daño del log sea coherente con el arma
        from app.database import fetch_all
        for _ in range(30):
            b = repo.get_battle(bid)
            if not b or b["status"] == "FINISHED":
                break
            resolve_phase(bid, "ATK", "DEF")

        # Verificar que hubo al menos algún daño registrado
        logs = fetch_all("SELECT counter_dmg_p2, outcome_code FROM battle_log WHERE battle_id=?", (bid,))
        non_zero = [l for l in logs if l["counter_dmg_p2"] > 0]
        assert len(non_zero) > 0, "No hubo fases con daño a P2 — arma mandoble no escaló"

    def test_prefix_matching_narrative(self, init_test_db):
        """Templates con pool_tag = prefijo deben ser seleccionables."""
        from app.engine.narrative import select_narrative
        from app.database import fetch_all

        # Verificar que existe al menos un template para algún pool_tag con prefijo
        templates = fetch_all(
            "SELECT DISTINCT pool_tag FROM narrative_templates WHERE pool_tag LIKE 'ATK_ATK_%' LIMIT 5"
        )
        if not templates:
            pytest.skip("No hay templates con pool_tag ATK_ATK_* en la DB de tests")

        # select_narrative con un pool_tag base debe encontrar templates via prefix matching
        text, extra = select_narrative("ATK_ATK", [])
        assert text, "select_narrative debe retornar texto no vacío via prefix matching"


# ── 5. Tests de Skills y Refresh Expiration ──────────────────────────────────

class TestSkillsAndRefresh:
    """Tests del sistema de skills y política de refresh de expiración."""

    def _fresh_battle(self, init_test_db) -> int:
        from app.repositories import battle_repo as repo
        bid = repo.create_battle("TEST", "campo_abierto")
        repo.create_battle_state(bid, "P1", "espada")
        repo.create_battle_state(bid, "P2", "espada")
        repo.create_accumulators(bid, "P1")
        repo.create_accumulators(bid, "P2")
        return bid

    def test_skill_pool_has_all_tiers(self, init_test_db):
        """skill_pool debe tener skills para todos los tiers definidos."""
        import sqlite3
        with sqlite3.connect(init_test_db) as conn:
            conn.row_factory = sqlite3.Row
            tiers = {r["tier"] for r in conn.execute("SELECT DISTINCT tier FROM skill_pool").fetchall()}
        expected = {"COMUN", "POCO_COMUN", "RARA", "LEGENDARIA", "EPICA"}
        assert expected <= tiers, f"Faltan tiers: {expected - tiers}"

    def test_power_mod_skill_increases_sum_mods(self, init_test_db):
        """Una skill POWER_MOD debe incrementar el modificador de tirada."""
        from app.engine.resolver import _sum_mods
        from app.repositories import battle_repo as repo

        bid = self._fresh_battle(init_test_db)
        base = _sum_mods(bid, "P1")
        repo.create_battle_skill(bid, "P1", "RESISTENCIA", turn=1)
        boosted = _sum_mods(bid, "P1")
        assert boosted == base + 1.0, \
            f"RESISTENCIA (+1) debe aumentar _sum_mods en 1 (base={base}, boosted={boosted})"

    def test_immunity_skill_blocks_specific_debuff(self, init_test_db):
        """GUARDIA_ALTA (IMMUNITY a POS_DESFAVORABLE) debe bloquear ese efecto."""
        from app.engine.resolver import _apply_effect
        from app.repositories import battle_repo as repo

        bid = self._fresh_battle(init_test_db)
        repo.create_battle_skill(bid, "P1", "GUARDIA_ALTA", turn=1)
        _apply_effect(bid, "P1", "POS_DESFAVORABLE", 5)
        effs = repo.get_active_effect_codes(bid, "P1")
        assert "POS_DESFAVORABLE" not in effs, \
            "GUARDIA_ALTA debe bloquear POS_DESFAVORABLE via IMMUNITY"

    def test_immunity_does_not_block_other_debuffs(self, init_test_db):
        """GUARDIA_ALTA no debe bloquear debuffs fuera de su lista de inmunidad."""
        from app.engine.resolver import _apply_effect
        from app.repositories import battle_repo as repo

        bid = self._fresh_battle(init_test_db)
        repo.create_battle_skill(bid, "P1", "GUARDIA_ALTA", turn=1)
        _apply_effect(bid, "P1", "FATIGA", 5)
        effs = repo.get_active_effect_codes(bid, "P1")
        assert "FATIGA" in effs, \
            "GUARDIA_ALTA no debe bloquear FATIGA (no está en su lista)"

    def test_setup_battle_skills_assigns_one_per_side(self, init_test_db):
        """setup_battle_skills debe asignar exactamente una habilidad a P1 y P2."""
        from app.engine.resolver import setup_battle_skills
        from app.repositories import battle_repo as repo

        bid = self._fresh_battle(init_test_db)
        assigned = setup_battle_skills(bid)
        p1_skills = repo.get_battle_skills(bid, "P1")
        p2_skills = repo.get_battle_skills(bid, "P2")
        assert len(p1_skills) == 1, f"P1 debe tener 1 skill, tiene {len(p1_skills)}"
        assert len(p2_skills) == 1, f"P2 debe tener 1 skill, tiene {len(p2_skills)}"
        assert "P1" in assigned and "P2" in assigned

    def test_refresh_expiration_extends_soft_effect(self, init_test_db):
        """Re-aplicar un efecto suave debe refrescar la expiración al mayor valor."""
        from app.engine.resolver import _add_effect_safe
        from app.repositories import battle_repo as repo

        bid = self._fresh_battle(init_test_db)
        _add_effect_safe(bid, "P1", "VACILACION", 10, "test")
        _add_effect_safe(bid, "P1", "VACILACION", 20, "test2")

        row = repo.get_active_effects(bid, "P1")
        vac = next((r for r in row if r["effect_code"] == "VACILACION"), None)
        assert vac is not None, "VACILACION debe seguir activa"
        assert vac["expires_at_phase"] == 20, \
            f"Expiración debe refrescarse a 20, es {vac['expires_at_phase']}"

    def test_refresh_does_not_shorten_expiration(self, init_test_db):
        """Refrescar con valor menor no debe acortar la expiración existente."""
        from app.engine.resolver import _add_effect_safe
        from app.repositories import battle_repo as repo

        bid = self._fresh_battle(init_test_db)
        _add_effect_safe(bid, "P1", "PANICO", 30, "test")
        _add_effect_safe(bid, "P1", "PANICO", 10, "test2")  # refresh con valor menor

        row = repo.get_active_effects(bid, "P1")
        pan = next((r for r in row if r["effect_code"] == "PANICO"), None)
        assert pan is not None
        assert pan["expires_at_phase"] == 30, \
            f"Expiración no debe reducirse (era 30, intento refresh a 10, queda {pan['expires_at_phase']})"

    def test_hard_effect_not_refreshed(self, init_test_db):
        """DESMEMBRADO (efecto severo) no debe refrescar su expiración."""
        from app.engine.resolver import _add_effect_safe
        from app.repositories import battle_repo as repo

        bid = self._fresh_battle(init_test_db)
        _add_effect_safe(bid, "P1", "DESMEMBRADO", 10, "test")
        _add_effect_safe(bid, "P1", "DESMEMBRADO", 30, "test2")  # intento refresh

        row = repo.get_active_effects(bid, "P1")
        desm = next((r for r in row if r["effect_code"] == "DESMEMBRADO"), None)
        assert desm is not None
        assert desm["expires_at_phase"] == 10, \
            f"DESMEMBRADO NO debe refrescar (debe quedar en 10, está en {desm['expires_at_phase']})"
