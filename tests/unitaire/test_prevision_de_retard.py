from unittest.mock import patch
import numpy as np
import pandas as pd

from projet_sncf.business.service.Prevision_de_retard import simulation
from projet_sncf.business.service.Prevision_de_retard import clusterise



@patch("projet_sncf.business.service.Prevision_de_retard.get_inferance")
def test_simulation(mock_get_inferance):
    # Given
    parameters = pd.Series([10.0, 20.0, 30.0])

    mock_get_inferance.return_value = np.arange(1000)

    # When
    result = simulation(
        parameters,
        axe="PARIS-NICE",
        cible="retard"
    )

    # Then

    assert len(result) == 1000

    mock_get_inferance.assert_called_once()

    X = mock_get_inferance.call_args[0][0]

    assert isinstance(X, pd.DataFrame)
    assert len(X) == 1000

    # perturbation effective
    origine = parameters.values

    assert not np.allclose(
        X.iloc[0].values,
        origine
    )

    # les valeurs restent proches
    ecart_moyen = np.mean(
        np.abs(X.iloc[0].values - origine)
    )

    assert ecart_moyen < 5


@patch("projet_sncf.business.service.Prevision_de_retard.get_inferance")
@patch("projet_sncf.business.service.Prevision_de_retard.get_dataframe")
def test_clusterise(mock_get_dataframe, mock_get_inferance):
    # Given
    axes = [
        "PARIS-LYON",
        "PARIS-NICE",
        "PARIS-LILLE",
        "PARIS-RENNES",
        "PARIS-BORDEAUX",
        "PARIS-NANTES"
    ]
    mock_get_dataframe.return_value = pd.DataFrame({"A": np.random.rand(1500)})
    mock_get_inferance.side_effect = [
        np.random.rand(1000),
        np.random.rand(1000),
        np.random.rand(1000),
        np.random.rand(1000),
        np.random.rand(1000),
        np.random.rand(1000)
    ]

    # When
    result = clusterise(axes, cible="prct annulation")

    # Then
    mock_get_dataframe.assert_called_once()
    assert mock_get_inferance.call_count == len(axes)
    print(result)
    assert result.shape == (len(axes), 2)
    assert np.isfinite(result).all()    