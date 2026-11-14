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