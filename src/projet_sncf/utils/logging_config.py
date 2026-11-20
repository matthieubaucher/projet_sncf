"""Configuration de la journalisation (logs) du projet.

Les modules du projet envoient leurs messages avec
``logging.getLogger(__name__)``, sans décider où ils sont écrits. Ce module
s'en charge, une seule fois au démarrage (application, notebook ou script) :
il écrit les messages dans le fichier ``logs/sncf.log`` à la racine du projet
et, si on le souhaite, les affiche aussi à l'écran.
"""

# Imports
import logging
from pathlib import Path

# Constants
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL = "INFO"

#: Dossier des logs : ``logs/`` à la racine du projet, quel que soit le
#: dossier depuis lequel on lance le code.
LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
LOG_FILE = "sncf.log"

#: Nom donné à nos gestionnaires, pour ne jamais les ajouter deux fois.
HANDLER_NAME = "projet_sncf"


# Functions
def setup_logging(
    level: str | int = LOG_LEVEL,
    log_dir: str | Path | None = LOG_DIR,
    log_file: str = LOG_FILE,
    console: bool = True,
) -> Path | None:
    """Configure le logger racine : un fichier de logs et, au choix, l'écran.

    La fonction peut être appelée plusieurs fois (relance d'une cellule de
    notebook, nouvelle exécution de l'application Streamlit) sans que les
    messages soient écrits en double : les gestionnaires ajoutés par un appel
    précédent sont retirés avant d'en ajouter de nouveaux.

    Args:
        level (str): Nom du niveau de journalisation, par exemple "INFO".
            Par défaut `LOG_LEVEL`.

    Returns:
        pathlib.Path | None: Chemin du fichier de logs, ou ``None`` si aucun
        fichier n'est écrit.

    Raises:
        OSError: Si le dossier ne peut pas être créé ou le fichier ne peut pas
            être ouvert.

    Example:
        >>> import logging, tempfile
        >>> chemin = setup_logging(log_dir=tempfile.mkdtemp(), console=False)
        >>> logging.getLogger("demo").info("Un message")
        >>> "Un message" in chemin.read_text(encoding="utf-8")
        True
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        if handler.get_name() == HANDLER_NAME:
            root.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    handlers: list[logging.Handler] = []

    path = None
    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / log_file
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    if console:
        handlers.append(logging.StreamHandler())

    for handler in handlers:
        handler.setFormatter(formatter)
        handler.set_name(HANDLER_NAME)  # pour le retrouver au prochain appel
        root.addHandler(handler)

    root.setLevel(level)
    return path
