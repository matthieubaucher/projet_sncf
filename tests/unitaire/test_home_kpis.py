"""Tests for the home page numbers."""

# Imports
import pandas as pd
import pytest

from projet_sncf.business.map.home_kpis import TIERS, home_metrics, tier_counts
from projet_sncf.business.map.map_sncf import TIER_LESS, TIER_MIDDLE, TIER_MORE


# Test data
def make_scores() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "tiers": [TIER_MORE, TIER_MORE, TIER_LESS],
            "taux_perturbation": [0.10, 0.20, 0.30],
            "mois": [24, 60, 105],
        }
    )


# Tests
def test_home_metrics_counts_and_averages():
    """The four numbers are right."""
    metrics = home_metrics(make_scores())
    assert metrics["liaisons"] == 3
    assert metrics["plus_fiables"] == 2
    assert metrics["taux_perturbation"] == pytest.approx(0.2)
    assert metrics["mois"] == 105


def test_home_metrics_of_empty_table_are_zero():
    """No liaison gives zeros, not an error."""
    metrics = home_metrics(make_scores().iloc[0:0])
    assert metrics == {
        "liaisons": 0,
        "plus_fiables": 0,
        "taux_perturbation": 0.0,
        "mois": 0,
    }


def test_tier_counts_keeps_the_fixed_order_and_zeros():
    """Every tier is listed, even without liaison."""
    counts = tier_counts(make_scores())
    assert list(counts["Niveau"]) == TIERS
    assert dict(zip(counts["Niveau"], counts["Liaisons"])) == {
        TIER_MORE: 2,
        TIER_MIDDLE: 0,
        TIER_LESS: 1,
    }
