import pandas as pd
from pathlib import Path

DATA_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "regularite-mensuelle-tgv-aqst.csv"
)



def get_dataframe():
    df = get_initial_dataframe()
    df = clean(df)
    df = add_usefull_column(df)
    return df

# récupération du csv pour fabriquer le dataframe initial
def get_initial_dataframe():
    return pd.read_csv(DATA_PATH, sep=";")

# nettoyage du dataframe fourni
def clean(df):
    df_clean = df.drop(columns=["Service", "Commentaire annulations", "Commentaire retards au départ", "Commentaire retards à l'arrivée"])
    df_clean["Date"] = pd.to_datetime(df_clean["Date"])
    df_clean["Gare de départ"] = df_clean["Gare de départ"].astype("category")
    df_clean["Gare d'arrivée"] = df_clean["Gare d'arrivée"].astype("category")
    return df_clean

# ajoute certaines nouvelles colonnes utiles pour nos analyses
def add_usefull_column(df):
    df_augmented = df.copy()

    # ajout des mois
    df_augmented["Mois"] = df_augmented["Date"].dt.month
    df_augmented["Mois"] = df_augmented["Mois"].astype("int8")

    # ajout des saisons
    temps = [5, 6, 9, 12, 16, 20, 23, 23, 20, 15, 10, 6] # temperatures moyennes en france par mois
    saison = {i+1: t for i, t in enumerate(temps)}
    df_augmented["Saison"] = df_augmented["Mois"].map(saison)
    df_augmented["Saison"] = df_augmented["Saison"].astype("int8")

    return df_augmented