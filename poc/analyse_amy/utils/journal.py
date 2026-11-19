"""Configuration des logs (journal d'exécution) du projet.

Les modules du projet envoient leurs messages avec ``logging.getLogger(__name__)``,
sans décider où ils sont écrits. Ce module s'en charge : il écrit les messages dans un
fichier du dossier ``logs/`` et, si on le souhaite, les affiche aussi à l'écran.

Example:
    >>> from utils.journal import configurer_journal
    >>> chemin = configurer_journal()  # doctest: +SKIP
    >>> print(chemin)  # doctest: +SKIP
    logs/sncf.log
"""

import logging
from pathlib import Path

FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
FORMAT_DATE = "%Y-%m-%d %H:%M:%S"


def configurer_journal(dossier="logs", nom_fichier="sncf.log", niveau=logging.INFO, afficher=False):
    """Configure l'écriture des logs dans un fichier.

    La fonction peut être appelée plusieurs fois (par exemple en relançant une cellule de
    notebook) sans que les messages soient écrits en double : les anciens gestionnaires
    ajoutés par cette fonction sont retirés avant d'en ajouter de nouveaux.

    Args:
        dossier (str | pathlib.Path): Dossier où écrire le fichier de logs. Il est créé
            s'il n'existe pas. Par défaut ``"logs"``.
        nom_fichier (str): Nom du fichier de logs. Par défaut ``"sncf.log"``.
        niveau (int): Niveau minimal des messages enregistrés, par exemple
            ``logging.INFO`` ou ``logging.DEBUG``. Par défaut ``logging.INFO``.
        afficher (bool): Si ``True``, affiche aussi les messages à l'écran. Par défaut ``False``.

    Returns:
        pathlib.Path: Chemin du fichier de logs.

    Raises:
        OSError: Si le dossier ne peut pas être créé ou le fichier ne peut pas être ouvert.

    Example:
        >>> import logging, tempfile
        >>> chemin = configurer_journal(dossier=tempfile.mkdtemp())
        >>> logging.getLogger("demo").info("Un message")
        >>> "Un message" in chemin.read_text(encoding="utf-8")
        True
    """
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / nom_fichier

    racine = logging.getLogger()
    for gestionnaire in list(racine.handlers):
        if getattr(gestionnaire, "_journal_sncf", False):
            racine.removeHandler(gestionnaire)
            gestionnaire.close()

    format_ = logging.Formatter(FORMAT, datefmt=FORMAT_DATE)
    fichier = logging.FileHandler(chemin, encoding="utf-8")
    fichier.setFormatter(format_)
    fichier._journal_sncf = True
    racine.addHandler(fichier)

    if afficher:
        ecran = logging.StreamHandler()
        ecran.setFormatter(format_)
        ecran._journal_sncf = True
        racine.addHandler(ecran)

    racine.setLevel(niveau)
    return chemin
