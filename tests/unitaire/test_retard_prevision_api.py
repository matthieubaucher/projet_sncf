import pytest
import numpy as np
from unittest.mock import patch

from projet_sncf.api.Retard_prevision_API import simulation_scenario_utilisateur

@patch("projet_sncf.database.dataloader.get_axes")
@patch("projet_sncf.database.dataloader.get_temps")
@patch("projet_sncf.api.Retard_prevision_API.simulation")
def test_simulation_scenario_utilisateur_nominal(
    mock_simulation,
    mock_get_temps,
    mock_get_axes
):
    mock_simulation.return_value = np.array([1,2,3])
    mock_get_temps.return_value = 3
    mock_get_axes.return_value = [["PARIS LYON", "NICE"]]

    parameters = {"Temps": 15, "Cause toto": 42}

    result = simulation_scenario_utilisateur(
        parameters,
        ["PARIS LYON", "NICE"],
        "Nombre trains en retard > 30min"
    )

    mock_get_temps.assert_called_once_with(1, 4)

    mock_simulation.assert_called_once_with(
        {"Temps": 3, "Cause toto": 42},
        ["PARIS LYON", "NICE"],
        "Nombre trains en retard > 30min"
    )

    np.testing.assert_array_equal(
        result,
        np.array([1, 2, 3])
    )

@patch("projet_sncf.database.dataloader.get_axes")
def test_simulation_scenario_utilisateur_axe_inconnu(mock_get_axes):
    mock_get_axes.return_value = [["PARIS LYON", "NICE"]]
    with pytest.raises(ValueError, match="Axe.* non disponible.*"):
        simulation_scenario_utilisateur(
            {"Temps": 15},
            ["FOO", "BAR"],
            "Nombre trains en retard > 30min"
        )

@patch("projet_sncf.database.dataloader.get_axes")
def test_simulation_scenario_utilisateur_cible_inconnue(mock_get_axes):
    mock_get_axes.return_value = [["PARIS LYON", "NICE"]]
    with pytest.raises(ValueError, match="Cible.* non disponible.*"):
        simulation_scenario_utilisateur(
            {"Temps": 15},
            ["PARIS LYON", "NICE"],
            "CIBLE_KO"
        )            