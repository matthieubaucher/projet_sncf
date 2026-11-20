import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from projet_sncf.utils.logging_config import (
    HANDLER_NAME,
    LOG_DIR,
    setup_logging,
)


@pytest.fixture(autouse=True)
def retirer_gestionnaires() -> Iterator[None]:
    """Retire les gestionnaires ajoutés, pour ne pas gêner les autres tests."""
    racine = logging.getLogger()
    niveau = racine.level
    yield
    for gestionnaire in list(racine.handlers):
        if gestionnaire.get_name() == HANDLER_NAME:
            racine.removeHandler(gestionnaire)
            gestionnaire.close()
    racine.setLevel(niveau)


def test_setup_logging_ecrit_un_fichier(tmp_path: Path) -> None:
    chemin = setup_logging(log_dir=tmp_path / "logs", console=False)
    logging.getLogger("test").info("message enregistré")
    assert chemin == tmp_path / "logs" / "sncf.log"
    assert "message enregistré" in chemin.read_text(encoding="utf-8")


def test_setup_logging_n_ecrit_pas_en_double(tmp_path: Path) -> None:
    setup_logging(log_dir=tmp_path, console=False)
    chemin = setup_logging(log_dir=tmp_path, console=False)
    assert chemin is not None
    logging.getLogger("test").info("message unique")
    assert chemin.read_text(encoding="utf-8").count("message unique") == 1


def test_setup_logging_affiche_aussi_a_l_ecran(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    chemin = setup_logging(log_dir=tmp_path)
    assert chemin is not None
    logging.getLogger("test").info("message visible")
    assert "message visible" in capsys.readouterr().err
    assert "message visible" in chemin.read_text(encoding="utf-8")


def test_setup_logging_sans_fichier(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert setup_logging(log_dir=None) is None
    logging.getLogger("test").info("seulement à l'écran")
    assert "seulement à l'écran" in capsys.readouterr().err


def test_setup_logging_accepte_un_niveau_en_texte(tmp_path: Path) -> None:
    chemin = setup_logging(level="WARNING", log_dir=tmp_path, console=False)
    assert chemin is not None
    logging.getLogger("test").info("ignoré")
    logging.getLogger("test").warning("gardé")
    texte = chemin.read_text(encoding="utf-8")
    assert "ignoré" not in texte
    assert "gardé" in texte


def test_dossier_par_defaut_a_la_racine_du_projet() -> None:
    assert LOG_DIR.name == "logs"
    assert (LOG_DIR.parent / "pyproject.toml").exists()
