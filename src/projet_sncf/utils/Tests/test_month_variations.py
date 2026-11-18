import logging
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import matplotlib.pyplot as plt

from projet_sncf.utils.month_variations import (
    plot_month_lateness,
    filter_route,
    plotMonthlyLateness,
    plotMonthlyLatenessAll,
)


@pytest.fixture
def sample_df():
    rows = []
    for annee in [2022, 2023]:
        for mois in range(1, 13):
            rows.append({
                'gare_depart': 'Paris',
                'gare_arrive': 'Lyon',
                'annee': annee,
                'mois': mois,
                'nb_retard_depart': mois * 10,
                'nb_retard_arrive': mois * 5,
            })
    for annee in [2022, 2023]:
        for mois in range(1, 13):
            rows.append({
                'gare_depart': 'Paris',
                'gare_arrive': 'Marseille',
                'annee': annee,
                'mois': mois,
                'nb_retard_depart': 1,
                'nb_retard_arrive': 2,
            })
    return pd.DataFrame(rows)


class TestFilterRoute:
    def test_trajet_existant(self, sample_df):
        d = filter_route(sample_df, 'Paris', 'Lyon')
        assert len(d) == 24

    def test_trajet_inexistant(self, sample_df):
        with pytest.raises(ValueError, match="Aucune donnée"):
            filter_route(sample_df, 'Paris', 'Brest')

    def test_log_error_trajet_inexistant(self, sample_df, caplog):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                filter_route(sample_df, 'Paris', 'Brest')
        assert "Aucune donnée pour le trajet Paris -> Brest" in caplog.text


class TestPlotMonthLateness:
    def test_mois_avec_donnees(self, sample_df):
        ax = MagicMock()
        plot_month_lateness(ax, sample_df, 6, 'Paris', 'Lyon')
        assert ax.plot.call_count == 2
        ax.set_title.assert_called_with('Mois 6')

    def test_mois_sans_donnees(self, sample_df):
        ax = MagicMock()
        plot_month_lateness(ax, sample_df, 13, 'Paris', 'Lyon')
        ax.plot.assert_not_called()
        ax.set_axis_off.assert_called_once()
        ax.text.assert_called_once()

    def test_log_warning_mois_vide(self, sample_df, caplog):
        ax = MagicMock()
        with caplog.at_level(logging.WARNING):
            plot_month_lateness(ax, sample_df, 13, 'Paris', 'Lyon')
        assert "Aucune donnée pour le mois 13" in caplog.text



class TestPlotMonthlyLateness:
    @patch('matplotlib.pyplot.show')
    @patch('matplotlib.pyplot.subplots')
    def test_mois_valide(self, mock_subplots, mock_show, sample_df):
        mock_subplots.return_value = (MagicMock(), MagicMock())
        plotMonthlyLateness(sample_df, 'Paris', 'Lyon', mois=6)
        mock_show.assert_called_once()

    @patch('matplotlib.pyplot.show')
    @patch('matplotlib.pyplot.subplots')
    def test_mois_vide(self, mock_subplots, mock_show, sample_df):
        with pytest.raises(ValueError, match="Aucune donnée pour le mois"):
            plotMonthlyLateness(sample_df, 'Paris', 'Lyon', mois=13)
        mock_show.assert_not_called()

    @patch('matplotlib.pyplot.show')
    @patch('matplotlib.pyplot.subplots')
    def test_trajet_inexistant(self, mock_subplots, mock_show, sample_df):
        with pytest.raises(ValueError, match="Aucune donnée pour"):
            plotMonthlyLateness(sample_df, 'Paris', 'Brest', mois=6)
        mock_show.assert_not_called()



class TestPlotMonthlyLatenessAll:
    @patch('matplotlib.pyplot.show')
    @patch('matplotlib.pyplot.subplots')
    def test_12_mois(self, mock_subplots, mock_show, sample_df):
        fig = MagicMock()
        axes = np.empty((4, 3), dtype=object)
        for i in range(4):
            for j in range(3):
                axes[i, j] = MagicMock()
        mock_subplots.return_value = (fig, axes)
        plotMonthlyLatenessAll(sample_df, 'Paris', 'Lyon')
        mock_show.assert_called_once()
        fig.tight_layout.assert_called_with(rect=[0, 0, 1, 0.95])

    @patch('matplotlib.pyplot.show')
    @patch('matplotlib.pyplot.subplots')
    def test_trajet_inexistant(self, mock_subplots, mock_show, sample_df):
        with pytest.raises(ValueError):
            plotMonthlyLatenessAll(sample_df, 'Paris', 'Brest')
        mock_show.assert_not_called()   