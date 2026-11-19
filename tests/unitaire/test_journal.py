import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from projet_sncf.utils.journal import NOM_GESTIONNAIRE, configurer_journal


@pytest.fixture(autouse=True)
def retirer_gestionnaires() -> Iterator[None]:
    """Retire les gestionnaires ajoutés, pour ne pas gêner les autres tests."""
    yield
    racine = logging.getLogger()
    for gestionnaire in list(racine.handlers):
        if gestionnaire.get_name() == NOM_GESTIONNAIRE:
            racine.removeHandler(gestionnaire)
            gestionnaire.close()


def test_configurer_journal_ecrit_un_fichier(tmp_path: Path) -> None:
    chemin = configurer_journal(dossier=tmp_path / "logs")
    logging.getLogger("test").info("message enregistré")
    assert chemin == tmp_path / "logs" / "sncf.log"
    assert "message enregistré" in chemin.read_text(encoding="utf-8")


def test_configurer_journal_n_ecrit_pas_en_double(tmp_path: Path) -> None:
    configurer_journal(dossier=tmp_path)
    chemin = configurer_journal(dossier=tmp_path)
    logging.getLogger("test").info("message unique")
    assert chemin.read_text(encoding="utf-8").count("message unique") == 1


def test_configurer_journal_affiche_aussi_a_l_ecran(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    chemin = configurer_journal(dossier=tmp_path, afficher=True)
    logging.getLogger("test").info("message visible")
    assert "message visible" in capsys.readouterr().err
    assert "message visible" in chemin.read_text(encoding="utf-8")
