import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH          = os.getenv("DB_PATH", "data/combatrol.db")
API_PREFIX       = "/api"
MAX_COUNTERS     = 15.0
PHASES_PER_TURN  = 3
RECOVERY_AMOUNT  = 0.5
RECOVERY_INTERVAL_TURNS = 3
ATK_SPAM_FATIGUE_THRESHOLD = 3   # ATKs consecutivos antes de FATIGA
LOW_STREAK_VACILACION = 3        # tiradas ≤4 consecutivas → VACILACION
LOW_STREAK_PANICO     = 5        # tiradas ≤4 consecutivas → PANICO
LOW_ROLL_THRESHOLD    = 4        # tirada efectiva ≤ este valor = "baja"

SKILL_THRESHOLDS = [
    (40,  "COMUN"),
    (70,  "POCO_COMUN"),
    (90,  "RARA"),
    (100, "LEGENDARIA"),
    (120, "EPICA"),
]

READ_TOKEN  = os.getenv("COMBATROL_READ_TOKEN", "")
ADMIN_TOKEN = os.getenv("COMBATROL_ADMIN_TOKEN", "")
