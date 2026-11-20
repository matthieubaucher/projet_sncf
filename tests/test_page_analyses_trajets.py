"""Tests du changement entre les vues d'analyse des trajets."""

import pandas as pd

from projet_sncf.pages import analyses_trajets
from projet_sncf.utils.evolution_causes import CAUSES_PERTURBATION


def test_afficher_vue_saisonnalite(monkeypatch):
    appels = []
    monkeypatch.setattr(analyses_trajets.saisonnalite, "main", lambda: appels.append("saisonnalite"))
    monkeypatch.setattr(analyses_trajets.classement_pire_trajets, "main", lambda: appels.append("classement"))

    analyses_trajets.afficher_vue(analyses_trajets.VUE_SAISONNALITE)

    assert appels == ["saisonnalite"]


def test_afficher_vue_classement(monkeypatch):
    appels = []
    monkeypatch.setattr(analyses_trajets.saisonnalite, "main", lambda: appels.append("saisonnalite"))
    monkeypatch.setattr(analyses_trajets.classement_pire_trajets, "main", lambda: appels.append("classement"))

    analyses_trajets.afficher_vue(analyses_trajets.VUE_CLASSEMENT)

    assert appels == ["classement"]


def test_afficher_vue_causes(monkeypatch):
    appels = []
    monkeypatch.setattr(analyses_trajets, "afficher_evolution_causes", lambda: appels.append("causes"))

    analyses_trajets.afficher_vue(analyses_trajets.VUE_CAUSES)

    assert appels == ["causes"]


def test_raccourcir_intitules_causes_nettoie_les_noms_bruts():
    donnees = pd.DataFrame({
        "cause": [*CAUSES_PERTURBATION, "Prct retard pour cause inconnue"],
        "pourcentage": [1.0] * (len(CAUSES_PERTURBATION) + 1),
    })

    resultat = analyses_trajets.raccourcir_intitules_causes(donnees)

    assert resultat["cause"].tolist() == [
        *CAUSES_PERTURBATION.values(),
        "cause inconnue",
    ]
    assert not resultat["cause"].str.startswith("Prct retard pour ").any()


def test_graphique_causes_isole_une_ligne_avec_double_clic():
    evolution = pd.DataFrame({
        "mois": pd.to_datetime(["2024-01-01", "2024-02-01"]),
        "cause": ["Infrastructure", "Infrastructure"],
        "pourcentage": [0.2, 0.3],
    })

    figure = analyses_trajets.construire_graphique_causes(evolution)

    assert figure.layout.legend.itemclick == "toggle"
    assert figure.layout.legend.itemdoubleclick == "toggleothers"
    assert list(figure.data[0].y) == [0.2, 0.3]