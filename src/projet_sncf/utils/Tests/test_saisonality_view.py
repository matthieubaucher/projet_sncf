import logging
import numpy as np
import pytest
import pandas as pd
import matplotlib.figure

from month_variations import filter_route
from saisonality_view import (
    plot_heatmap_cancelations,
    plot_heatmap_annulations,
    plot_heatmap_annulations_global,
    plot_heatmap,
    plot_heatmap_delay,
    plot_heatmap_global,
)


@pytest.fixture
def sample_df_heatmap():
    rows = []
    for annee in [2022, 2023]:
        for mois in range(1, 13):
            rows.append({
                'gare_depart': 'Paris',
                'gare_arrive': 'Lyon',
                'annee': annee,
                'mois': mois,
                "Retard moyen de tous les trains à l'arrivée": mois * 0.5,
                'Nombre de trains annulés': mois * 2,
                'Nombre de circulations prévues': 100,
            })
    for annee in [2022, 2023]:
        for mois in range(1, 13):
            rows.append({
                'gare_depart': 'Paris',
                'gare_arrive': 'Marseille',
                'annee': annee,
                'mois': mois,
                "Retard moyen de tous les trains à l'arrivée": mois * 0.3,
                'Nombre de trains annulés': 1,
                'Nombre de circulations prévues': 50,
            })
    return pd.DataFrame(rows)


@pytest.fixture
def sample_pivot():
    """Pivot 2 années × 3 mois avec un NaN pour tester la cellule vide."""
    data = {
        1: [3.5, np.nan],
        2: [4.2, 5.1],
        3: [np.nan, 6.0],
    }
    return pd.DataFrame(data, index=pd.Index([2022, 2023], name='annee'))


class TestPlotHeatmapCancelations:
    def test_retourne_fig(self, sample_pivot):
        fig = plot_heatmap_cancelations(sample_pivot, 'Test')
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_pivot_sans_nan(self, sample_pivot):
        pivot_ok = sample_pivot.fillna(0)
        fig = plot_heatmap_cancelations(pivot_ok, 'Test')
        assert isinstance(fig, matplotlib.figure.Figure)


class TestPlotHeatmap:
    def test_retourne_fig(self, sample_pivot):
        fig = plot_heatmap(sample_pivot, 'Test')
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_pivot_sans_nan(self, sample_pivot):
        pivot_ok = sample_pivot.fillna(0)
        fig = plot_heatmap(pivot_ok, 'Test')
        assert isinstance(fig, matplotlib.figure.Figure)


class TestPlotHeatmapAnnulations:
    def test_retourne_fig(self, sample_df_heatmap):
        fig = plot_heatmap_annulations(sample_df_heatmap, 'Paris', 'Lyon')
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_trajet_inexistant(self, sample_df_heatmap):
        with pytest.raises(ValueError, match="Aucune donnée"):
            plot_heatmap_annulations(sample_df_heatmap, 'Paris', 'Brest')

    def test_log_error_trajet_inexistant(self, sample_df_heatmap, caplog):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                plot_heatmap_annulations(sample_df_heatmap, 'Paris', 'Brest')
        assert "Aucune donnée pour le trajet Paris -> Brest" in caplog.text


class TestPlotHeatmapAnnulationsGlobal:
    def test_retourne_fig(self, sample_df_heatmap):
        fig = plot_heatmap_annulations_global(sample_df_heatmap)
        assert isinstance(fig, matplotlib.figure.Figure)


class TestPlotHeatmapDelay:
    def test_retourne_fig(self, sample_df_heatmap):
        fig = plot_heatmap_delay(sample_df_heatmap, 'Paris', 'Lyon')
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_trajet_inexistant(self, sample_df_heatmap):
        with pytest.raises(ValueError, match="Aucune donnée"):
            plot_heatmap_delay(sample_df_heatmap, 'Paris', 'Brest')

    def test_log_error_trajet_inexistant(self, sample_df_heatmap, caplog):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                plot_heatmap_delay(sample_df_heatmap, 'Paris', 'Brest')
        assert "Aucune donnée pour le trajet Paris -> Brest" in caplog.text


class TestPlotHeatmapGlobal:
    def test_retourne_fig(self, sample_df_heatmap):
        fig = plot_heatmap_global(sample_df_heatmap)
        assert isinstance(fig, matplotlib.figure.Figure)   