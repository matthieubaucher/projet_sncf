from projet_sncf.database.dataloader import get_dataframe
from projet_sncf.business.model.Modele_prevision_retard import ModelePrevisionRetard
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
import pytest

colonnes_X = ["Temps", "Saison", "Nombre de circulations prévues", "Prct retard pour causes externes", 
"Prct retard pour cause infrastructure", "Prct retard pour cause gestion trafic", "Prct retard pour cause matériel roulant",
"Prct retard pour cause gestion en gare et réutilisation de matériel", 
"Prct retard pour cause prise en compte voyageurs (affluence, gestions PSH, correspondances)"]


@pytest.mark.parametrize(
    "depart,arrivee,cible,seuil",
    [
        ("PARIS LYON", "NICE VILLE", "prct Nombre trains en retard > 30min", 0.32),
        ("PARIS LYON", "NICE VILLE", "prct annulation", 0.4),
        ("PARIS LYON", "NICE VILLE", "Retard moyen de tous les trains à l'arrivée", 0.28),

        #("PARIS MONTPARNASSE", "RENNES", "prct Nombre trains en retard > 30min", 0),
        #("PARIS MONTPARNASSE", "RENNES", "prct annulation", 0),
        #("PARIS MONTPARNASSE", "RENNES", "Retard moyen de tous les trains à l'arrivée", 0),

        ("PARIS NORD", "LILLE", "prct Nombre trains en retard > 30min", 0.26),
        #("PARIS NORD", "LILLE", "prct annulation", 0),
        ("PARIS NORD", "LILLE", "Retard moyen de tous les trains à l'arrivée", 0.4)
    ]
)
def test_modelePrevisionRetard(depart, arrivee, cible, seuil):
    df = get_dataframe()
    df = df[(df["Gare de départ"]==depart) & (df["Gare d'arrivée"]==arrivee)]
    modele = ModelePrevisionRetard(depart, arrivee, colonnes_X, colonne_Y=cible)
    df_train, df_test = train_test_split(
        df,
        test_size=0.2,
        random_state=42
    )
    modele.train(df_train)
    prediction = modele.predict(df_test)
    reel = df_test[cible]

    score = r2_score(reel, prediction)

    assert score > seuil, f"le r2 de la prévision \"{cible}\" est bas pour la ligne {depart} -> {arrivee}"

