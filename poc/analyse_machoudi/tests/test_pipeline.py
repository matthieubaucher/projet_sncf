"""Integration test of the full pipeline on a small synthetic dataset."""

import numpy as np
import pandas as pd
import pytest

from analyse_machoudi.constants import (
    CAUSE_COLUMNS,
    COL_ARRIVAL,
    COL_CANCELLED,
    COL_DATE,
    COL_DELAYED,
    COL_DEPARTURE,
    COL_SCHEDULED,
    COL_SERVICE,
    CONFIDENCE_ENOUGH,
    CONFIDENCE_LOW,
    FINAL_COLUMNS,
    LIAISON_KEY,
)
from analyse_machoudi.pipeline import build_reliability_table

SHOCK_DATE = "2023-06"


@pytest.fixture
def dataset():
    """Build a dataset of four liaisons over 36 months, with one national shock.

    Liaisons B, C and D have 36 months, D being worse than B and C. Liaison E has
    only 10 months. All liaisons are hit in June 2023, which is the shock month.

    Returns:
        pd.DataFrame: The monthly data, with the six cause columns.
    """
    rng = np.random.default_rng(42)
    months = pd.period_range("2022-01", periods=36, freq="M").astype(str)
    frames = []
    for station, level in [("B", 0.05), ("C", 0.10), ("D", 0.20), ("E", 0.08)]:
        liaison_months = months[:10] if station == "E" else months
        scheduled = 1000
        delayed = (
            level * scheduled * rng.uniform(0.8, 1.2, len(liaison_months))
        ).astype(int)
        delayed = np.where(liaison_months == SHOCK_DATE, 600, delayed)
        frame = pd.DataFrame(
            {
                COL_DEPARTURE: "A",
                COL_ARRIVAL: station,
                COL_SERVICE: "National",
                COL_DATE: liaison_months,
                COL_SCHEDULED: scheduled,
                COL_CANCELLED: 10,
                COL_DELAYED: delayed,
            }
        )
        for i, cause in enumerate(CAUSE_COLUMNS):
            frame[cause] = 100.0 if i == 1 else 0.0
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def test_table_has_one_row_per_liaison_and_the_final_columns(dataset):
    """Check the shape and the columns of the final table.

    Args:
        dataset (pd.DataFrame): Synthetic dataset of the fixture.

    Returns:
        None: Passes if there are four rows indexed by the liaison key and the
        columns of ``FINAL_COLUMNS``.
    """
    table = build_reliability_table(dataset)
    assert len(table) == 4
    assert list(table.columns) == FINAL_COLUMNS
    assert table.index.names == LIAISON_KEY


def test_table_is_sorted_by_score_and_ranks_liaisons_correctly(dataset):
    """Check the order of the liaisons.

    Args:
        dataset (pd.DataFrame): Synthetic dataset of the fixture.

    Returns:
        None: Passes if the scores increase down the table and the worst liaison
        (D) comes first and the best (B) among the reliable ones comes last.
    """
    table = build_reliability_table(dataset)
    assert table["score"].is_monotonic_increasing
    assert table["score"].between(0, 100).all()
    assert table.index[0][1] == "D"
    reliable = table[table["confiance"] == CONFIDENCE_ENOUGH]
    assert reliable.index[-1][1] == "B"


def test_confidence_and_missing_indicators_of_the_short_liaison(dataset):
    """Check the liaison with only 10 months.

    Args:
        dataset (pd.DataFrame): Synthetic dataset of the fixture.

    Returns:
        None: Passes if it is "peu fiable" with a score, but without seasonality
        nor regularity.
    """
    row = build_reliability_table(dataset).loc[("A", "E", "National")]
    assert row["confiance"] == CONFIDENCE_LOW
    assert not np.isnan(row["score"])
    assert np.isnan(row["saisonnalite"])
    assert np.isnan(row["pires_mois_tous"])


def test_shock_month_is_removed_from_regularity_but_kept_in_the_score(dataset):
    """Check how the national shock month is used.

    Args:
        dataset (pd.DataFrame): Synthetic dataset of the fixture.

    Returns:
        None: Passes if regularity is lower without the shock month than with it,
        and if the score matches the rates computed on all months.
    """
    row = build_reliability_table(dataset).loc[("A", "B", "National")]
    assert row["pires_mois_hors_chocs"] < row["pires_mois_tous"]
    liaison = dataset[dataset[COL_ARRIVAL] == "B"]
    disrupted = liaison[COL_CANCELLED].sum() + liaison[COL_DELAYED].sum()
    assert row["score"] == pytest.approx(
        100 * (1 - disrupted / liaison[COL_SCHEDULED].sum())
    )


def test_dominant_cause_and_input_left_unchanged(dataset):
    """Check the dominant cause and that the input is not modified.

    Args:
        dataset (pd.DataFrame): Synthetic dataset of the fixture.

    Returns:
        None: Passes if every liaison has "Infrastructure" as dominant cause and the
        input dataset is identical afterwards.
    """
    before = dataset.copy()
    table = build_reliability_table(dataset)
    assert (table["cause_dominante"] == "Infrastructure").all()
    pd.testing.assert_frame_equal(dataset, before)
