"""Tests unitaires du module ``utils.diagnostic``.

Chaque ligne du petit tableau fabriqué illustre un défaut précis : on sait donc exactement
ce que chaque contrôle doit trouver.
"""

import numpy as np
import pandas as pd
import pytest

from utils.diagnostic import (
    chercher_doublons,
    compter_inclusions,
    compter_valeurs_manquantes,
    masques_valeurs_impossibles,
    negatifs_par_annee,
    tableau_controles,
    verifier_apres_nettoyage,
)
from utils.nettoyage import nettoyer

RETARD_EN_RETARD = "Retard moyen des trains en retard à l'arrivée"
RETARD_15 = "Retard moyen trains en retard > 15 (si liaison concurrencée par vol)"


@pytest.fixture
def donnees():
    """Données brutes, une ligne par cas.

    - ligne 0 : valide ;
    - ligne 1 : aucune circulation prévue (et durée nulle, retards > circulés) ;
    - ligne 2 : « > 30 min » négatif ;
    - ligne 3 : « > 60 min » > « > 30 min » et annulés > prévues ;
    - ligne 4 : retards moyens négatifs, même date et liaison que la ligne 0 mais autre service.
    """
    return pd.DataFrame({
        "Date": ["2024-01", "2024-02", "2024-03", "2025-04", "2024-01"],
        "Service": ["National", "National", "National", "National", "International"],
        "Gare de départ": ["PARIS LYON"] * 5,
        "Gare d'arrivée": ["MARSEILLE ST CHARLES"] * 5,
        "Durée moyenne du trajet": [200.0, 0.0, 190.0, 195.0, 205.0],
        "Nombre de circulations prévues": [300, 0, 250, 280, 260],
        "Nombre de trains annulés": [2, 0, 1, 290, 3],
        "Nombre de trains en retard à l'arrivée": [40, 5, 35, 0, 20],
        "Nombre trains en retard > 30min": [10, 0, -4, 3, 5],
        "Nombre trains en retard > 60min": [4, 0, 1, 6, 2],
        RETARD_EN_RETARD: [25.0, 0.0, 30.0, 40.0, -3.0],
        RETARD_15: [35.0, 0.0, 40.0, 50.0, -1.0],
        "Retard moyen de tous les trains au départ": [2.5, 0.0, 3.0, 4.0, -0.4],
        "Retard moyen de tous les trains à l'arrivée": [4.0, 0.0, 5.0, 7.0, -2.0],
        "Commentaire annulations": [np.nan] * 5,
        "Commentaire retards au départ": [np.nan] * 5,
        "Commentaire retards à l'arrivée": [np.nan, np.nan, "Heurt d'un animal", np.nan, np.nan],
    })


def test_compter_valeurs_manquantes_ignore_les_commentaires(donnees):
    assert compter_valeurs_manquantes(donnees) == 0


def test_compter_valeurs_manquantes_repere_les_faux_vides(donnees):
    donnees["Service"] = donnees["Service"].astype(object)
    donnees.loc[0, "Service"] = " - "
    donnees.loc[1, "Durée moyenne du trajet"] = np.nan
    assert compter_valeurs_manquantes(donnees) == 2
    assert compter_valeurs_manquantes(donnees, exclure=[]) == 2 + 14  # commentaires vides comptés


def test_chercher_doublons(donnees):
    resume, doublons = chercher_doublons(donnees)
    assert resume["Lignes entièrement identiques"] == 0
    assert resume["Lignes en double sur la clé"] == 2
    assert resume["Mois concernés"] == ["2024-01"]
    assert resume["Liaisons concernées"] == 1
    assert resume["Doublons si l'on ajoute le service"] == 0
    assert sorted(doublons.index) == [0, 4]


def test_chercher_doublons_cle_d_une_colonne(donnees):
    resume, _ = chercher_doublons(donnees.drop(columns="Service"), cle=["Date"])
    assert resume["Liaisons concernées"] == 0
    assert "Doublons si l'on ajoute le service" not in resume


def test_chercher_doublons_colonne_manquante(donnees):
    with pytest.raises(KeyError):
        chercher_doublons(donnees.drop(columns="Gare de départ"))


def test_masques_valeurs_impossibles(donnees):
    masques = masques_valeurs_impossibles(donnees)
    lignes = {nom: masque[masque].index.tolist() for nom, masque in masques.items()}
    assert lignes == {
        "Circulations prévues = 0": [1],
        "Durée moyenne du trajet = 0": [1],
        "Trains annulés > circulations prévues": [3],
        "Trains en retard > trains réellement circulés": [1, 3],  # ligne 3 : 280 - 290 < 0
        "Trains en retard > 30 min négatif": [2],
        "Trains en retard > 60 min plus nombreux que > 30 min": [2, 3],  # ligne 2 : 1 > -4
        "Retard moyen des trains en retard à l'arrivée négatif": [4],
        "Retard moyen des trains en retard > 15 min négatif": [4],
    }


def test_masques_colonne_manquante(donnees):
    with pytest.raises(KeyError, match="Durée moyenne du trajet"):
        masques_valeurs_impossibles(donnees.drop(columns="Durée moyenne du trajet"))


def test_tableau_controles(donnees):
    tableau = tableau_controles(masques_valeurs_impossibles(donnees))
    assert tableau.loc["Circulations prévues = 0", "lignes"] == 1
    assert tableau.loc["Circulations prévues = 0", "part (%)"] == 20.0


def test_compter_inclusions(donnees):
    resultat = compter_inclusions(masques_valeurs_impossibles(donnees), "Circulations prévues = 0")
    assert "Circulations prévues = 0" not in resultat.index
    assert resultat.loc["Durée moyenne du trajet = 0"].tolist() == [1, 1]
    assert resultat.loc["Trains en retard > 30 min négatif"].tolist() == [1, 0]


def test_compter_inclusions_reference_inconnue(donnees):
    with pytest.raises(KeyError, match="inconnu"):
        compter_inclusions(masques_valeurs_impossibles(donnees), "pas un contrôle")


def test_negatifs_par_annee(donnees):
    resultat = negatifs_par_annee(donnees, [RETARD_EN_RETARD, "Nombre trains en retard > 30min"])
    assert resultat.index.name == "Année"
    assert resultat.loc["2024"].tolist() == [1, 1]
    assert resultat.loc["2025"].tolist() == [0, 0]


def test_verifier_apres_nettoyage_sur_donnees_saines(donnees):
    saines = donnees.drop(index=[1, 3])
    df_propre, _ = nettoyer(saines)
    assert verifier_apres_nettoyage(df_propre).sum() == 0


def test_verifier_apres_nettoyage_signale_les_defauts(donnees):
    resultat = verifier_apres_nettoyage(donnees)
    assert resultat["Circulations prévues = 0"] == 1
    assert resultat["Trains annulés > circulations prévues"] == 1
    assert resultat["Valeurs négatives (toutes colonnes numériques)"] == 5
