"""Constantes de l'analyse de fiabilité.

Chemins, paramètres de la méthode, noms de colonnes du jeu de données
et libellés utilisés par les modules de `business/analysis`.
"""

# Imports
import os

# Constants

# Racine du dépôt et dossier des données
ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
DATA_DIR = os.path.join(ROOT, "data")

# Motif pour trouver le CSV brut dans DATA_DIR
DEFAULT_PATTERN = "regularite*.csv"

# Période de l'analyse (les mois suivants ne sont pas utilisés)
ANALYSIS_START = "2018-01"
ANALYSIS_END = "2026-06"

# Paramètres de la méthode
MIN_MONTHS = 24
WORST_MONTHS_SHARE = 0.10
SHOCK_SIGMA = 3.0
MAD_TO_SIGMA = 1.4826

# Colonnes du jeu de données
COL_DATE = "Date"
COL_DEPARTURE = "Gare de départ"
COL_ARRIVAL = "Gare d'arrivée"
COL_SERVICE = "Service"
COL_SCHEDULED = "Nombre de circulations prévues"
COL_CANCELLED = "Nombre de trains annulés"
COL_DELAYED = "Nombre de trains en retard à l'arrivée"

# Clé d'une liaison : gare de départ, gare d'arrivée, service
LIAISON_KEY = [COL_DEPARTURE, COL_ARRIVAL, COL_SERVICE]

# Causes de retard : colonne du jeu de données et nom court
CAUSE_COLUMNS = {
    "Prct retard pour causes externes": "Externes",
    "Prct retard pour cause infrastructure": "Infrastructure",
    "Prct retard pour cause gestion trafic": "Gestion du trafic",
    "Prct retard pour cause matériel roulant": "Matériel roulant",
    (
        "Prct retard pour cause gestion en gare et réutilisation de matériel"
    ): "Gestion en gare",
    (
        "Prct retard pour cause prise en compte voyageurs "
        "(affluence, gestions PSH, correspondances)"
    ): "Prise en compte des voyageurs",
}

# Niveaux de confiance et niveaux de fiabilité
CONFIDENCE_ENOUGH = "suffisante"
CONFIDENCE_LOW = "peu fiable"
TIER_LABELS = ["moins fiable", "intermédiaire", "plus fiable"]

# Colonnes du tableau de fiabilité final
FINAL_COLUMNS = [
    "mois",
    "confiance",
    "score",
    "tiers",
    "taux_annulation",
    "taux_retard",
    "pires_mois_tous",
    "pires_mois_hors_chocs",
    "saisonnalite",
    "cause_dominante",
]
