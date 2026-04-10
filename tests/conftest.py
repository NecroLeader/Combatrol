"""
Configuración de pytest para Combatrol.
Redirige DB_PATH a una DB temporal en memoria para cada sesión de tests,
e inicializa schema + seed para que el motor funcione sin datos reales.
"""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

# Redirigir DB a archivo temporal ANTES de importar cualquier módulo de app
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DB_PATH"] = _tmp.name


def _run_script(db_path: str, script_path: str):
    conn = sqlite3.connect(db_path)
    with open(script_path, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def _import_matrix(db_path: str, csv_path: str):
    import csv as csv_mod
    conn = sqlite3.connect(db_path)
    inserted = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv_mod.DictReader(f)
        for row in reader:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO outcome_matrix "
                    "(action_pair, difference_band, power_context, outcome_code, "
                    "phase_winner, counter_dmg_A, counter_dmg_B, effect_A, effect_B, "
                    "base_weight, narrative_pool_tag, is_fatal) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        row["action_pair"].strip(),
                        row["difference_band"].strip(),
                        row["power_context"].strip(),
                        row["outcome_code"].strip(),
                        row["phase_winner"].strip(),
                        float(row["counter_dmg_A"]),
                        float(row["counter_dmg_B"]),
                        row["effect_A"].strip() if row["effect_A"].strip().upper() != "NULL" else None,
                        row["effect_B"].strip() if row["effect_B"].strip().upper() != "NULL" else None,
                        float(row["base_weight"]),
                        row["narrative_pool_tag"].strip(),
                        int(row["is_fatal"]),
                    ),
                )
                inserted += 1
            except Exception:
                pass
    conn.commit()
    conn.close()


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    """Inicializa la DB de tests con schema + seed completo."""
    db_path = os.environ["DB_PATH"]
    root = Path(__file__).parent.parent

    _run_script(db_path, str(root / "data" / "schema.sql"))
    _run_script(db_path, str(root / "data" / "seed.sql"))

    for script in ("seed_narratives_v2.sql", "seed_narratives_v3.sql"):
        path = root / "data" / script
        if path.exists():
            _run_script(db_path, str(path))

    # Importar matrices CSV si existen (están en la raíz del proyecto)
    for csv_name in ("outcome_matrix_seed.csv", "outcome_matrix_seed_v2.csv"):
        csv_path = root / csv_name
        if csv_path.exists():
            _import_matrix(db_path, str(csv_path))

    yield db_path

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass
