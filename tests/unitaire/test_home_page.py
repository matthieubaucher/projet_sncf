"""Tests de la page d'accueil."""

import json
import logging
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

from projet_sncf.business.analysis import reliability
from projet_sncf.business.map.home_kpis import TIERS

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


def test_home_displays_tier_chart(monkeypatch):
    """La page affiche les barres et leurs étiquettes."""
    scores = pd.DataFrame(
        {"tiers": [TIERS[0]], "taux_perturbation": [0.1], "mois": [12]}
    )
    monkeypatch.setattr(reliability, "get_reliability_table", lambda: scores)
    st.cache_data.clear()
    app = AppTest.from_file(str(PAGE), default_timeout=30).run()

    assert not app.exception
    charts = app.get("vega_lite_chart")
    assert len(charts) == 1
    spec = json.loads(charts[0].proto.spec)
    assert [layer["mark"]["type"] for layer in spec["layer"]] == [
        "bar",
        "text",
    ]
