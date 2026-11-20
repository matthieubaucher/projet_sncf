"""Tests des cas d'échec de get_reliability_table."""

import logging
import pandas as pd
import pytest

from projet_sncf.business.analysis import reliability


def test_get_reliability_table_without_data_in_the_period(monkeypatch, caplog):
    """Sans ligne dans la période de l'analyse, on journalise et on lève une erreur."""
    outside = pd.DataFrame({"Date": ["2010-01-01"]})
    monkeypatch.setattr(reliability, "get_dataframe", lambda: outside)
    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValueError, match="Aucune donnée"):
            reliability.get_reliability_table()
    assert "Aucune donnée" in caplog.text
