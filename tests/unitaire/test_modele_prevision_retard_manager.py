from projet_sncf.business.model.Modele_prevision_retard_manager import ModelManager
from unittest.mock import MagicMock, patch

def test_get_id_modele_inverse_les_gares():
    manager = ModelManager()

    id1 = manager.get_id_axe(
        ["annee", "mois"],
        ("PARIS", "NICE"),
        "retard"
    )

    id2 = manager.get_id_axe(
        ["annee", "mois"],
        ("NICE", "PARIS"),
        "retard"
    )

    assert id1 == id2


from unittest.mock import MagicMock, patch


@patch("projet_sncf.business.model.Modele_prevision_retard_manager.ModelePrevisionRetard")
def test_get_trained_modele_utilise_le_cache_et_entraine_une_seule_fois(
    mock_modele
):
    # Given
    manager = ModelManager()

    manager.dataframe = MagicMock(name="global_dataframe")

    X = MagicMock()
    X.columns = ["annee", "mois"]

    instance = mock_modele.return_value

    # When
    modele_1 = manager.get_trained_modele(
        X,
        ("PARIS", "NICE"),
        "retard"
    )

    modele_2 = manager.get_trained_modele(
        X,
        ("NICE", "PARIS"),
        "retard"
    )

    # Then
    assert modele_1 is modele_2

    # modèle créé une seule fois
    mock_modele.assert_called_once()

    # entraîné une seule fois
    instance.train.assert_called_once_with(
        manager.dataframe
    )


from unittest.mock import MagicMock


def test_get_inferance_appelle_predict():
    # Given
    manager = ModelManager()

    modele_mock = MagicMock()
    modele_mock.predict.return_value = [1, 2, 3]

    manager.get_trained_modele = MagicMock(
        return_value=modele_mock
    )

    X = MagicMock()

    # When
    result = manager.get_inferance(
        X,
        ("PARIS", "NICE"),
        "retard"
    )

    # Then
    modele_mock.predict.assert_called_once_with(X)
    assert result == [1, 2, 3]    