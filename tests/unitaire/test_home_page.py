"""Tests de la page d'accueil."""

import logging
from pathlib import Path

from streamlit.testing.v1 import AppTest

from projet_sncf.business.analysis import reliability

PAGE = Path(__file__).resolve().parents[2] / "src" / "projet_sncf" / "pages" / "home.py"


def test_home_shows_an_error_when_scores_cannot_be_loaded(monkeypatch, caplog):
    """Si les scores ne se chargent pas, la page affiche une erreur et le journalise."""

    def fail():
        raise ValueError("Aucune donnée entre 2018-01 et 2026-06.")

    monkeypatch.setattr(reliability, "get_reliability_table", fail)
    app = AppTest.from_file(str(PAGE), default_timeout=30)
    with caplog.at_level(logging.ERROR):
        app.run()
    assert not app.exception
    assert len(app.error) == 1
    assert "Aucune donnée" in app.error[0].value
    assert "Aucune donnée" in caplog.text
