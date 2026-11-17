import os

# Folder containing this file
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
DATA_DIR = os.path.join(ROOT, "data")

# Default pattern used to find the raw CSV file
DEFAULT_PATTERN = "*.csv"

# Logging configuration
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_LEVEL = "INFO"

# Method parameters
MIN_MONTHS = 24
WORST_MONTHS_SHARE = 0.10
SHOCK_SIGMA = 3.0
MAD_TO_SIGMA = 1.4826

# Dataset columns
COL_DATE = "Date"
COL_DEPARTURE = "Gare de départ"
COL_ARRIVAL = "Gare d'arrivée"
COL_SERVICE = "Service"
COL_SCHEDULED = "Nombre de circulations prévues"
COL_CANCELLED = "Nombre de trains annulés"
COL_DELAYED = "Nombre de trains en retard à l'arrivée"

# A liaison is a trpilet :: departure, arrival, service
LIAISON_KEY = [COL_DEPARTURE, COL_ARRIVAL, COL_SERVICE]

# Delay causes: dataset column and short name
CAUSE_COLUMNS = {
    "Prct retard pour causes externes": "Externes",
    "Prct retard pour cause infrastructure": "Infrastructure",
    "Prct retard pour cause gestion trafic": "Gestion du trafic",
    "Prct retard pour cause matériel roulant": "Matériel roulant",
    "Prct retard pour cause gestion en gare et réutilisation de matériel": "Gestion en gare",
    "Prct retard pour cause prise en compte voyageurs (affluence, gestions PSH, correspondances)": "Prise en compte des voyageurs",
}
