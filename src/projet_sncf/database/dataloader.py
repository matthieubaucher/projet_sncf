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
    # retrait des colonnes inutiles
    df_clean = df.drop(columns=["Service", "Commentaire annulations", "Commentaire retards au départ", "Commentaire retards à l'arrivée"])
    
    # bon type pour les dates et les gares
    df_clean["Date"] = pd.to_datetime(df_clean["Date"])
    df_clean["Gare de départ"] = df_clean["Gare de départ"].astype("category")
    df_clean["Gare d'arrivée"] = df_clean["Gare d'arrivée"].astype("category")
    
    # pas de circulation négatives ou nulles dans le dataset
    df_clean = df_clean[df_clean["Nombre de circulations prévues"] > 0]

    return df_clean

# ajoute certaines nouvelles colonnes utiles pour nos analyses
def add_usefull_column(df):
    df_augmented = df.copy()

    # Ajout du Temps
    origine = pd.Timestamp("2018-01-01")
    df_augmented["Temps"] = (
        (df_augmented["Date"].dt.year - origine.year) * 12
        + (df_augmented["Date"].dt.month - origine.month)
    )
    df_augmented["Temps"].astype("int16")

    # Ajout des mois
    df_augmented["Mois"] = df_augmented["Date"].dt.month
    df_augmented["Mois"] = df_augmented["Mois"].astype("int8")

    # Ajout des saisons
    temps = [5, 6, 9, 12, 16, 20, 23, 23, 20, 15, 10, 6] # temperatures moyennes en france par mois
    saison = {i+1: t for i, t in enumerate(temps)}
    df_augmented["Saison"] = df_augmented["Mois"].map(saison)
    df_augmented["Saison"] = df_augmented["Saison"].astype("int8")
    
    # Ajout des pourcentages de retard/annulation à analyser ...
    colonne_retard = ["Nombre de trains en retard à l'arrivée", "Retard moyen de tous les trains à l'arrivée",
        "Nombre trains en retard > 15min", "Nombre trains en retard > 30min", "Nombre trains en retard > 60min"]
    col_nb_circ = "Nombre de circulations prévues"
    colonne_prct_retard = []
    for retard in colonne_retard:
        df_augmented = df_augmented[df_augmented[retard] >= 0]
        if retard == "Retard moyen de tous les trains à l'arrivée":
            colonne_prct_retard.append(retard)
        else:
            col = f"prct {retard}"
            colonne_prct_retard.append(col)
            df_augmented[col] = df_augmented[retard]/df_augmented[col_nb_circ]
    colonne_prct_retard.append("prct annulation")        
    df_augmented["prct annulation"] = df_augmented["Nombre de trains annulés"] / df_augmented[col_nb_circ]    

    return df_augmented