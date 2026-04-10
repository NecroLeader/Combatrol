"""
fix_engine_v6.py — Patch live DB con cambios del batch 6:
  - Extra_effects en más pool_tags de narrative_templates
  (Los cambios en resolver.py no requieren patch de DB, solo redeploy del código)

Correr dentro del container:
  docker cp fix_engine_v6.py combatrol_app:/app/fix_engine_v6.py
  docker exec combatrol_app python /app/fix_engine_v6.py
"""

import sqlite3

DB = "/app/data/combatrol.db"

EXTRA_EFFECTS = [
    (
        'ATK_ATK_DOMINA',
        '[{"target":"RECEPTOR","effect":"PANICO","duration_phases":3,"chance":0.20,"source":"narrative"},'
        '{"target":"ACTOR","effect":"POS_FAVORABLE","duration_phases":2,"chance":0.45,"source":"narrative"}]'
    ),
    (
        'DEF_DEF_REPOSICION',
        '[{"target":"ACTOR","effect":"POS_FAVORABLE","duration_phases":3,"chance":0.40,"source":"narrative"}]'
    ),
    (
        'ATK_ATK_BRUTAL_A',
        '[{"target":"ACTOR","effect":"POS_DESFAVORABLE","duration_phases":2,"chance":0.15,"source":"narrative"},'
        '{"target":"RECEPTOR","effect":"POS_DESFAVORABLE","duration_phases":2,"chance":0.15,"source":"narrative"}]'
    ),
    (
        'ATK_ATK_BRUTAL_B',
        '[{"target":"ACTOR","effect":"POS_DESFAVORABLE","duration_phases":2,"chance":0.15,"source":"narrative"},'
        '{"target":"RECEPTOR","effect":"POS_DESFAVORABLE","duration_phases":2,"chance":0.15,"source":"narrative"}]'
    ),
    (
        'DEF_ATK_CONTRA_EPICO',
        '[{"target":"RECEPTOR","effect":"VACILACION","duration_phases":3,"chance":0.30,"source":"narrative"},'
        '{"target":"ACTOR","effect":"POS_FAVORABLE","duration_phases":3,"chance":0.35,"source":"narrative"}]'
    ),
]

def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    for pool_tag, extra_effects in EXTRA_EFFECTS:
        cur.execute(
            "UPDATE narrative_templates SET extra_effects=? WHERE pool_tag=?",
            (extra_effects, pool_tag)
        )
        rows = cur.rowcount
        print(f"  {pool_tag}: {rows} template(s) actualizados")

    con.commit()
    con.close()
    print("\nfix_engine_v6 completado.")

if __name__ == "__main__":
    main()
