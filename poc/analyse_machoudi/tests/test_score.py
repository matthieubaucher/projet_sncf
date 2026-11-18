"""Unit tests of the reliability score."""

import numpy as np
import pandas as pd
import pytest

from analyse_machoudi.constants import (
    CAUSE_COLUMNS,
    CONFIDENCE_ENOUGH,
    CONFIDENCE_LOW,
    TIER_LABELS,
)
from analyse_machoudi.score import compute_score, compute_tier_bounds, dominant_cause


def make_table(months, rates):
    """Build a table of liaisons with the columns used by the score.

    Args:
        months (list[int]): Number of months of each liaison.
        rates (list[float]): Disruption rate of each liaison.

    Returns:
        pd.DataFrame: One row per liaison, named L0, L1, and so on.
    """
    index = [f"L{i}" for i in range(len(months))]
    return pd.DataFrame({"mois": months, "taux_perturbation": rates}, index=index)


def test_score_is_100_times_one_minus_the_disruption_rate():
    """Check the formula of the score.

    Returns:
        None: Passes if a rate of 0.15 gives a score of 85.
    """
    result = compute_score(make_table([30], [0.15]))
    assert result.loc["L0", "score"] == pytest.approx(85.0)


def test_confidence_depends_on_the_number_of_months():
    """Check the confidence level at the limit of 24 months.

    Returns:
        None: Passes if 23 months is "peu fiable" and 24 months is "suffisante".
    """
    result = compute_score(make_table([23, 24], [0.1, 0.1]))
    assert result["confiance"].tolist() == [CONFIDENCE_LOW, CONFIDENCE_ENOUGH]


def test_tiers_split_reliable_liaisons_into_three_groups():
    """Check the tiers of nine reliable liaisons.

    Returns:
        None: Passes if each tier holds three liaisons, the lowest scores being in
        the "moins fiable" tier.
    """
    rates = [0.01 * i for i in range(1, 10)]
    result = compute_score(make_table([30] * 9, rates))
    assert result["tiers"].value_counts().tolist() == [3, 3, 3]
    assert list(result["tiers"].iloc[[0, 8]]) == [TIER_LABELS[2], TIER_LABELS[0]]


def test_unreliable_liaisons_do_not_set_the_tier_bounds():
    """Check that the bounds ignore liaisons with too few months.

    Returns:
        None: Passes if adding a very bad liaison with 3 months leaves the bounds
        unchanged, so the other tiers do not move, and the bad liaison is in the
        "moins fiable" tier.
    """
    base = make_table([30] * 9, [0.01 * i for i in range(1, 10)])
    extended = pd.concat([base, make_table([3], [0.9]).rename(index={"L0": "short"})])
    result_base = compute_score(base)
    result = compute_score(extended)
    assert result.loc[base.index, "tiers"].tolist() == result_base["tiers"].tolist()
    assert result.loc["short", "tiers"] == TIER_LABELS[0]


def test_tier_bounds_are_the_terciles_of_the_scores():
    """Check the bounds between the tiers.

    Returns:
        None: Passes if the bounds of the scores 0 to 90 are 30 and 60, and NaN for
        an empty series.
    """
    lower, upper = compute_tier_bounds(pd.Series(range(0, 100, 10)))
    assert lower == pytest.approx(30.0)
    assert upper == pytest.approx(60.0)
    assert np.isnan(compute_tier_bounds(pd.Series([], dtype=float))[0])


def test_tiers_are_nan_without_any_reliable_liaison():
    """Check the tiers when no liaison has enough months.

    Returns:
        None: Passes if every tier is NaN and the score is still computed.
    """
    result = compute_score(make_table([3, 5], [0.1, 0.2]))
    assert result["tiers"].isna().all()
    assert result["score"].notna().all()


def test_input_table_is_not_modified():
    """Check that the input table is left untouched.

    Returns:
        None: Passes if the input has no ``score`` column afterwards.
    """
    table = make_table([30], [0.1])
    compute_score(table)
    assert "score" not in table.columns


def test_missing_column_raises_key_error():
    """Check the error raised when the rate column is absent.

    Returns:
        None: Passes if a KeyError mentioning the missing columns is raised.
    """
    with pytest.raises(KeyError, match="Colonnes manquantes"):
        compute_score(make_table([30], [0.1]).drop(columns=["taux_perturbation"]))


def test_dominant_cause_is_the_largest_share():
    """Check the dominant cause and the liaison without any delay.

    Returns:
        None: Passes if the liaison with delays gets its largest cause and the
        liaison without delay is left out.
    """
    names = list(CAUSE_COLUMNS.values())
    profile = pd.DataFrame(
        [[10, 60, 30, 0, 0, 0], [np.nan] * 6], columns=names, index=["L0", "L1"]
    )
    result = dominant_cause(profile)
    assert result.to_dict() == {"L0": names[1]}
