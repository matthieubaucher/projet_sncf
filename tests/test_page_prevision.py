"""Tests de la page Streamlit « Prévision des perturbations ».

Les calculs sont testés sur de petits tableaux fabriqués à la main. L'affichage est testé avec
l'outil de test de Streamlit (``AppTest``), sur ces mêmes données : on vérifie que la page
s'affiche sans erreur, pour le mois prochain comme pour un mois passé.
"""

import pandas as pd
import pytest

from projet_sncf.pages.prevision_perturbations import (
    CAUSES,
    COL_ANNULES,
    COL_PREVUES,
    COL_RETARDS,
    causes_du_mois,
    charger_previsions,
    historique_liaisons,
    indicateurs_liaison,
    mois_disponibles,
    niveau_risque,
    previsions_du_mois,
)

CAUSE_EXTERNE, CAUSE_INFRA = list(CAUSES)[:2]


@pytest.fixture
def dossier_resultats(tmp_path):
    """Fichiers de prévisions : 2 liaisons, un mois passé (06/2026) et le mois prochain (07/2026)."""
    pd.DataFrame({
        "Gare de départ": ["PARIS LYON", "PARIS EST"],
        "Gare d'arrivée": ["NICE VILLE", "FRANCFORT"],
        "Service": ["National", "International"],
        "mois_prevu": ["2026-07-01", "2026-07-01"],
        "proba_perturbation": [0.3, 0.9],
        "prevision": ["Normal", "Perturbé"],
    }).to_csv(tmp_path / "predictions_liaisons.csv", index=False)
    pd.DataFrame({
        "Gare de départ": ["PARIS LYON", "PARIS EST"],
        "Gare d'arrivée": ["NICE VILLE", "FRANCFORT"],
        "Service": ["National", "International"],
        "Date": ["2026-06-01", "2026-06-01"],
        "taux_perturbation": [0.25, 0.30],
        "proba_perturbation": [0.7, 0.4],
        "prediction_foret": ["Perturbé", "Normal"],
        "realite": ["Perturbé", "Perturbé"],
    }).to_csv(tmp_path / "predictions_test.csv", index=False)
    return tmp_path


@pytest.fixture
def donnees():
    """Données nettoyées d'une liaison sur 13 mois (06/2025 à 06/2026)."""
    dates = pd.date_range("2025-06-01", "2026-06-01", freq="MS")
    df = pd.DataFrame({
        "Gare de départ": "PARIS LYON", "Gare d'arrivée": "NICE VILLE", "Service": "National",
        "Date": dates, COL_PREVUES: 100, COL_ANNULES: 0, COL_RETARDS: range(10, 23),
    })
    for cause in CAUSES:
        df[cause] = 0.0
    df[CAUSE_EXTERNE] = 70.0
    df[CAUSE_INFRA] = 30.0
    df.loc[df["Date"] == "2025-07-01", list(CAUSES)] = 0.0  # causes non renseignées
    df.loc[df["Date"] == "2025-08-01", COL_RETARDS] = 0  # aucun retard
    return df


@pytest.fixture
def historique(donnees):
    return historique_liaisons(donnees)


# --- prévisions --------------------------------------------------------------------------

def test_charger_previsions(dossier_resultats):
    previsions = charger_previsions(dossier_resultats)
    assert len(previsions) == 4
    assert previsions["liaison"].iloc[0] == "PARIS LYON → NICE VILLE"
    futur = previsions[previsions["mois_prevu"] == "2026-07-01"]
    assert futur["realite"].isna().all()


def test_mois_disponibles_commence_par_le_mois_prochain(dossier_resultats):
    mois = mois_disponibles(charger_previsions(dossier_resultats))
    assert [pd.Timestamp(m) for m in mois] == [pd.Timestamp("2026-07-01"), pd.Timestamp("2026-06-01")]


def test_previsions_du_mois_trie_et_filtre(dossier_resultats):
    previsions = charger_previsions(dossier_resultats)
    vue = previsions_du_mois(previsions, pd.Timestamp("2026-07-01"))
    assert vue["proba_perturbation"].tolist() == [0.9, 0.3]
    nationales = previsions_du_mois(previsions, pd.Timestamp("2026-07-01"), service="National")
    assert nationales["Service"].unique().tolist() == ["National"]


@pytest.mark.parametrize("proba,niveau", [(0.1, "Faible"), (0.35, "Moyen"), (0.64, "Moyen"), (0.65, "Élevé")])
def test_niveau_risque(proba, niveau):
    assert niveau_risque(proba)[0] == niveau


# --- historique ----------------------------------------------------------------------------

def test_historique_liaisons_calcule_le_taux(historique):
    juin = historique[historique["Date"] == "2026-06-01"].iloc[0]
    assert juin["taux"] == pytest.approx(22 / 100)


def test_historique_liaisons_gares_en_texte(donnees):
    donnees["Gare de départ"] = donnees["Gare de départ"].astype("category")
    assert str(historique_liaisons(donnees)["Gare de départ"].dtype) != "category"


def test_indicateurs_liaison(historique):
    ind = indicateurs_liaison(historique, "PARIS LYON", "NICE VILLE", "National", pd.Timestamp("2026-07-01"))
    assert ind["mois_dernier"] == pytest.approx(0.22)  # juin 2026 : 22 retards pour 100 trains
    assert ind["an_dernier"] == pytest.approx(0.11)  # juillet 2025 : 11 retards pour 100 trains


def test_indicateurs_liaison_moyenne_12_mois(historique):
    ind = indicateurs_liaison(historique, "PARIS LYON", "NICE VILLE", "National", pd.Timestamp("2026-07-01"))
    attendu = historique[historique["Date"] >= "2025-07-01"]["taux"].mean()
    assert ind["moyenne_12_mois"] == pytest.approx(attendu)


def test_indicateurs_liaison_inconnue(historique):
    ind = indicateurs_liaison(historique, "X", "Y", "National", pd.Timestamp("2026-07-01"))
    assert ind == {"mois_dernier": None, "moyenne_12_mois": None, "an_dernier": None}


# --- causes --------------------------------------------------------------------------------

def test_causes_du_mois_renseignees(historique):
    etat, parts = causes_du_mois(historique, "PARIS LYON", "NICE VILLE", "National", pd.Timestamp("2026-06-01"))
    assert etat == "ok"
    assert parts.tolist() == [70.0, 30.0]  # de la plus fréquente à la moins fréquente, sans les 0
    assert parts.index[0] == CAUSES[CAUSE_EXTERNE]


def test_causes_du_mois_non_renseignees(historique):
    etat, parts = causes_du_mois(historique, "PARIS LYON", "NICE VILLE", "National", pd.Timestamp("2025-07-01"))
    assert (etat, parts) == ("non renseignées", None)


def test_causes_du_mois_aucun_retard(historique):
    assert causes_du_mois(historique, "PARIS LYON", "NICE VILLE", "National",
                          pd.Timestamp("2025-08-01"))[0] == "aucun retard"


def test_causes_du_mois_absent(historique):
    assert causes_du_mois(historique, "PARIS LYON", "NICE VILLE", "National",
                          pd.Timestamp("2020-01-01"))[0] == "mois absent"


# --- affichage -------------------------------------------------------------------------------

def _page(dossier, donnees):
    from projet_sncf.pages.prevision_perturbations import (
        afficher_page,
        charger_previsions,
        historique_liaisons,
    )

    afficher_page(charger_previsions(dossier), historique_liaisons(donnees))


def test_page_mois_prochain(dossier_resultats, donnees):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_page, args=(dossier_resultats, donnees)).run()
    assert not at.exception
    assert [m.value for m in at.metric] == ["1 / 2", "1 / 2", "90%"]


def test_page_mois_passe(dossier_resultats, donnees):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_page, args=(dossier_resultats, donnees)).run()
    at.selectbox[0].select_index(1).run()  # 06/2026
    assert not at.exception
    assert [m.value for m in at.metric] == ["1 / 2", "2 / 2", "50%"]
    at.selectbox[1].select_index(1).run()  # deuxième liaison
    assert not at.exception
