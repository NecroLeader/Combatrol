#!/usr/bin/env python3
"""
Inicializa la base de datos: aplica schema.sql y seed.sql.
Uso: python scripts/init_db.py [--seed-matrix outcome_matrix_seed.csv]
"""

import sys
import csv
import sqlite3
import argparse
from pathlib import Path

# Asegura que el módulo app sea encontrable desde la raíz
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import execute_script, get_connection
from app.config import DB_PATH


def init_db():
    print(f"[init_db] DB: {DB_PATH}")
    execute_script("data/schema.sql")
    print("[init_db] Schema aplicado.")
    execute_script("data/seed.sql")
    print("[init_db] Seed aplicado.")
    if Path("data/seed_narratives_v2.sql").exists():
        execute_script("data/seed_narratives_v2.sql")
        print("[init_db] Narrativas v2 aplicadas.")


def import_matrix_csv(csv_path: str):
    """Importa outcome_matrix_seed.csv generado por GPT."""
    path = Path(csv_path)
    if not path.exists():
        print(f"[ERROR] No se encontró {csv_path}")
        sys.exit(1)

    conn = get_connection()
    inserted = 0
    skipped = 0

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
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
            except Exception as e:
                print(f"[SKIP] {row.get('outcome_code','?')}: {e}")
                skipped += 1

    conn.commit()
    conn.close()
    print(f"[import_matrix] Insertadas: {inserted} | Saltadas: {skipped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-matrix", metavar="CSV", action="append",
                        help="Path a un CSV de outcome_matrix (se puede repetir)")
    args = parser.parse_args()

    init_db()

    for csv_path in (args.seed_matrix or []):
        import_matrix_csv(csv_path)

    print("[init_db] Listo.")
