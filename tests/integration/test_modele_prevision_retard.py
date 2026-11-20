from projet_sncf.database.dataloader import get_dataframe
from projet_sncf.business.model.Modele_prevision_retard import ModelePrevisionRetard
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
import pytest  # type: ignore[import-not-found]

feature_columns = ["Temps", "Saison", "Nombre de circulations prévues", "Prct retard pour causes externes", 
"Prct retard pour cause infrastructure", "Prct retard pour cause gestion trafic", "Prct retard pour cause matériel roulant",
"Prct retard pour cause gestion en gare et réutilisation de matériel", 
"Prct retard pour cause prise en compte voyageurs (affluence, gestions PSH, correspondances)"]

def compute_score(depart, arrivee, cible):
    df = get_dataframe()
    df = df[(df["Gare de départ"]==depart) & (df["Gare d'arrivée"]==arrivee) | (df["Gare de départ"]==arrivee) & (df["Gare d'arrivée"]==depart)]
    df = df.dropna(subset=feature_columns + [cible])  # lignes où la cible ou une variable est vide
    modele = ModelePrevisionRetard(
        depart, arrivee, feature_columns, target_column=cible
    )
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
        ("PARIS LYON", "MARSEILLE ST CHARLES", "Nombre de trains en retard à l'arrivée", 0.45),
        ("PARIS LYON", "MARSEILLE ST CHARLES", "Nombre trains en retard > 60min", 0.15), # <- résultat mitigé partout : on garde ? 
        ("PARIS LYON", "MARSEILLE ST CHARLES", "prct Nombre trains en retard > 30min", .17),
        ("PARIS LYON", "MARSEILLE ST CHARLES", "prct annulation", 0.5), # <- tous les "prct annulation" sont bien
        ("PARIS LYON", "MARSEILLE ST CHARLES", "Retard moyen de tous les trains à l'arrivée", 0), # <- celui la il est vraiment variable : on prend pas

        ("PARIS LYON", "NICE VILLE", "Nombre de trains en retard à l'arrivée", 0.66),
        ("PARIS LYON", "NICE VILLE", "Nombre trains en retard > 60min", 0.27),
        ("PARIS LYON", "NICE VILLE", "prct Nombre trains en retard > 30min", 0.32),
        ("PARIS LYON", "NICE VILLE", "prct annulation", 0.48), 
        ("PARIS LYON", "NICE VILLE", "Retard moyen de tous les trains à l'arrivée", 0.42),

        ("PARIS MONTPARNASSE", "RENNES", "Nombre de trains en retard à l'arrivée", 0.15), # <- on garde quand même : les autres sont bons 
        ("PARIS MONTPARNASSE", "RENNES", "Nombre trains en retard > 60min", 0.145),
        ("PARIS MONTPARNASSE", "RENNES", "prct Nombre trains en retard > 30min", -0.1), # <- celui la il est vraiment pas terrible : on prend pas
        ("PARIS MONTPARNASSE", "RENNES", "prct annulation", 0.56),
        ("PARIS MONTPARNASSE", "RENNES", "Retard moyen de tous les trains à l'arrivée", 0.139),

        ("PARIS NORD", "LILLE", "Nombre de trains en retard à l'arrivée", 0.44),
        ("PARIS NORD", "LILLE", "Nombre trains en retard > 60min", 0.23),
        ("PARIS NORD", "LILLE", "prct Nombre trains en retard > 30min", 0.269),  
        ("PARIS NORD", "LILLE", "prct annulation", 0.5),
        ("PARIS NORD", "LILLE", "Retard moyen de tous les trains à l'arrivée", 0.34),

        ("PARIS MONTPARNASSE", "BORDEAUX ST JEAN", "Nombre de trains en retard à l'arrivée", 0.39),
        ("PARIS MONTPARNASSE", "BORDEAUX ST JEAN", "Nombre trains en retard > 60min", 0.139),
        ("PARIS MONTPARNASSE", "BORDEAUX ST JEAN", "prct Nombre trains en retard > 30min", 0.34), # <- c'est pas si mal, ca fait hésiter  
        ("PARIS MONTPARNASSE", "BORDEAUX ST JEAN", "prct annulation", 0.609),
        ("PARIS MONTPARNASSE", "BORDEAUX ST JEAN", "Retard moyen de tous les trains à l'arrivée", 0.21)
    ] 
# => je pense proposer "prct annulation", "Nombre de trains en retard à l'arrivée", "Nombre trains en retard > 60min" à l'utilisateur
# et c'est raccord avec le theme de l'assurance

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
