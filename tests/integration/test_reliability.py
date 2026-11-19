"""Test du tableau de fiabilité sur les vraies données."""

from projet_sncf.business.analysis.constants import FINAL_COLUMNS
from projet_sncf.business.analysis.reliability import get_reliability_table


def test_reliability_table_matches_the_frozen_analysis():
    """Le tableau garde les liaisons et les colonnes de l'analyse figée."""
    table = get_reliability_table()
    assert set(FINAL_COLUMNS) <= set(table.columns)
    assert {"Gare de départ", "Gare d'arrivée", "Service"} <= set(table.columns)
    assert len(table) == 146
    assert table["score"].between(0, 100).all()
