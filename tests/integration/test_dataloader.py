from projet_sncf.database.dataloader import get_dataframe
import pandas as pd

def test_get_dataframe_charge_le_dataset():
    df = get_dataframe()

    # colonnes supprimées
    assert "Service" not in df.columns
    assert "Commentaire annulations" not in df.columns
    assert "Commentaire retards au départ" not in df.columns
    assert "Commentaire retards à l'arrivée" not in df.columns

    # type Date
    assert pd.api.types.is_datetime64_any_dtype(df["Date"])

    # catégories
    assert str(df["Gare de départ"].dtype) == "category"
    assert str(df["Gare d'arrivée"].dtype) == "category"

    # nombre de circulations valide
    assert (df["Nombre de circulations prévues"] > 0).all()

    # nouvelles colonnes bien créées et correctement
    assert "Temps" in df.columns
    assert "Mois" in df.columns
    assert "Saison" in df.columns
    assert "prct Nombre de trains en retard à l'arrivée" in df.columns
    assert "prct Nombre trains en retard > 15min" in df.columns
    assert "prct Nombre trains en retard > 30min" in df.columns
    assert "prct Nombre trains en retard > 60min" in df.columns
    assert "prct annulation" in df.columns
    assert (df["Temps"]>=0).all()
    assert df["Mois"].between(1, 12).all()
    assert df["Saison"].between(-10, 30).all()
    assert df["prct Nombre de trains en retard à l'arrivée"].between(0, 1).all()
    assert df["prct Nombre trains en retard > 15min"].between(0, 1).all()
    assert df["prct Nombre trains en retard > 30min"].between(0, 1).all()
    assert df["prct Nombre trains en retard > 60min"].between(0, 1).all()
    assert df["prct annulation"].between(0, 1).all()
