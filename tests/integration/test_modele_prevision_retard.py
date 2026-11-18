from projet_sncf.database.dataloader import get_dataframe
from projet_sncf.business.model.Modele_prevision_retard import ModelePrevisionRetard
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
import pytest  # type: ignore[import-not-found]

colonnes_X = ["Temps", "Saison", "Nombre de circulations prévues", "Prct retard pour causes externes", 
"Prct retard pour cause infrastructure", "Prct retard pour cause gestion trafic", "Prct retard pour cause matériel roulant",
"Prct retard pour cause gestion en gare et réutilisation de matériel", 
"Prct retard pour cause prise en compte voyageurs (affluence, gestions PSH, correspondances)"]

def compute_score(depart, arrivee, cible):
    df = get_dataframe()
    df = df[(df["Gare de départ"]==depart) & (df["Gare d'arrivée"]==arrivee) | (df["Gare de départ"]==arrivee) & (df["Gare d'arrivée"]==depart)]
    df = df.dropna(subset=colonnes_X + [cible])  # lignes où la cible ou une variable est vide
    modele = ModelePrevisionRetard(depart, arrivee, colonnes_X, colonne_Y=cible)
    df_train, df_test = train_test_split(
        df,
        test_size=0.2,
        random_state=42
    )
    modele.train(df_train)
    prediction = modele.predict(df_test)
    reel = df_test[cible]

    return r2_score(reel, prediction)

tests = [
        ("PARIS LYON", "NICE VILLE", "prct Nombre trains en retard > 30min", -0.13),
        ("PARIS LYON", "NICE VILLE", "prct annulation", 0.38), 
        ("PARIS LYON", "NICE VILLE", "Retard moyen de tous les trains à l'arrivée", 0.19),

        ("PARIS MONTPARNASSE", "RENNES", "prct Nombre trains en retard > 30min", 0.11),
        ("PARIS MONTPARNASSE", "RENNES", "prct annulation", 0.39),
        ("PARIS MONTPARNASSE", "RENNES", "Retard moyen de tous les trains à l'arrivée", 0.07),

        ("PARIS NORD", "LILLE", "prct Nombre trains en retard > 30min", -0.30),  
        ("PARIS NORD", "LILLE", "prct annulation", 0.13),
        ("PARIS NORD", "LILLE", "Retard moyen de tous les trains à l'arrivée", 0.23)
    ]


@pytest.mark.parametrize("depart,arrivee,cible,seuil", tests)
def test_modelePrevisionRetard(depart, arrivee, cible, seuil):
    score = compute_score(depart, arrivee, cible)
    assert score > seuil, f"le r2 de la prévision \"{cible}\" est bas ({score:5.3f}) pour la ligne {depart} -> {arrivee}"


if __name__ == "__main__":
    score = 0
    for test in tests:
        score_local = compute_score(test[0],test[1],test[2])
        print(score_local)
        score += score_local

    print("score final = ",score)
