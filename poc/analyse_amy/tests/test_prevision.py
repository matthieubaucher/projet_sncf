"""Tests unitaires du module ``utils.prevision``.

Les tests utilisent deux liaisons fabriquées à la main, sur 36 mois, dont on connaît
exactement les comptages : on peut donc recalculer chaque variable à la main.
"""

import logging

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")

from utils.prevision import (
    COL_ANNULES,
    COL_PREVUES,
    COL_RETARDS,
    VARIABLES,
    ajouter_cible,
    calculer_variables,
    chercher_resultat,
    controler_comptages,
    creer_modele,
    decouper_train_test,
    detecter_mois_choc,
    entrainer_et_predire,
    entrainer_modele_final,
    exporter_predictions,
    importance_variables,
    mesurer,
    part_perturbee_selon_seuil,
    preparer_donnees,
    preparer_matrices,
    prevoir_mois_suivant,
    regle_mois_dernier,
    resultats_test,
    sensibilite_seuils,
    table_calibration,
)

DATES = pd.date_range("2022-01-01", periods=36, freq="MS")


def fabriquer_donnees():
    """Deux liaisons sur 36 mois : A (nationale, peu perturbée) et B (internationale, souvent perturbée)."""
    i = np.arange(36)
    lignes = []
    for gare, service, base_retard in [("A", "National", 5), ("B", "International", 15)]:
        lignes.append(pd.DataFrame({
            "Gare de départ": "PARIS",
            "Gare d'arrivée": gare,
            "Service": service,
            "Date": DATES,
            COL_PREVUES: 100,
            COL_ANNULES: i % 3,
            # retards qui varient d'un mois à l'autre, avec un pic tous les 4 mois
            COL_RETARDS: base_retard + (i % 7) + 12 * (i % 4 == 0),
        }))
    return pd.concat(lignes, ignore_index=True)


@pytest.fixture
def df_pred():
    return ajouter_cible(preparer_donnees(fabriquer_donnees()))


@pytest.fixture
def table(df_pred):
    return calculer_variables(df_pred)


def ligne(table, gare, date):
    return table[(table["Gare d'arrivée"] == gare) & (table["Date"] == pd.Timestamp(date))].iloc[0]


# --- données et cible -------------------------------------------------------

def test_preparer_donnees_ajoute_les_circulations_reelles():
    df = preparer_donnees(fabriquer_donnees())
    assert (df["circulations_reelles"] == df[COL_PREVUES] - df[COL_ANNULES]).all()


def test_preparer_donnees_colonne_manquante():
    with pytest.raises(KeyError, match="Service"):
        preparer_donnees(fabriquer_donnees().drop(columns="Service"))


def test_controler_comptages_tout_a_zero(df_pred):
    assert controler_comptages(df_pred).sum() == 0


def test_ajouter_cible(df_pred):
    attendu = (df_pred[COL_ANNULES] + df_pred[COL_RETARDS]) / df_pred[COL_PREVUES]
    np.testing.assert_allclose(df_pred["taux_perturbation"], attendu)
    assert (df_pred["perturbe"] == (attendu > 0.20).astype(int)).all()


@pytest.mark.parametrize("seuil", [0, 1, -0.1, 1.5])
def test_ajouter_cible_seuil_invalide(seuil):
    with pytest.raises(ValueError):
        ajouter_cible(preparer_donnees(fabriquer_donnees()), seuil=seuil)


def test_part_perturbee_selon_seuil(df_pred):
    parts = part_perturbee_selon_seuil(df_pred, [0.0, 1.0])
    assert parts.tolist() == [1.0, 0.0]
    assert parts.index.tolist() == ["0%", "100%"]


# --- variables explicatives ---------------------------------------------------

def test_variables_mois_dernier(df_pred, table):
    avril = df_pred[(df_pred["Gare d'arrivée"] == "A") & (df_pred["Date"] == "2022-04-01")].iloc[0]
    mai = ligne(table, "A", "2022-05-01")
    assert mai["retard_mois_dernier"] == pytest.approx(avril[COL_RETARDS] / avril["circulations_reelles"])
    assert mai["annulation_mois_dernier"] == pytest.approx(avril[COL_ANNULES] / avril[COL_PREVUES])


def test_variables_12_mois_somme_puis_division(df_pred, table):
    a = df_pred[df_pred["Gare d'arrivée"] == "A"].set_index("Date")
    periode = a.loc["2022-01-01":"2022-12-01"]
    janvier_2023 = ligne(table, "A", "2023-01-01")
    assert janvier_2023["retard_12_mois"] == pytest.approx(
        periode[COL_RETARDS].sum() / periode["circulations_reelles"].sum())
    assert janvier_2023["annulation_12_mois"] == pytest.approx(periode[COL_ANNULES].sum() / periode[COL_PREVUES].sum())


def test_variables_12_mois_demande_au_moins_6_mois(table):
    assert np.isnan(ligne(table, "A", "2022-06-01")["retard_12_mois"])  # 5 mois connus
    assert not np.isnan(ligne(table, "A", "2022-07-01")["retard_12_mois"])  # 6 mois connus


def test_variables_an_dernier(df_pred, table):
    mars_2022 = df_pred[(df_pred["Gare d'arrivée"] == "A") & (df_pred["Date"] == "2022-03-01")].iloc[0]
    assert ligne(table, "A", "2023-03-01")["retard_an_dernier"] == pytest.approx(
        mars_2022[COL_RETARDS] / mars_2022["circulations_reelles"])


def test_variables_mois_et_international(table):
    assert ligne(table, "A", "2022-07-01")["mois"] == 7
    assert ligne(table, "A", "2022-07-01")["international"] == 0
    assert ligne(table, "B", "2022-07-01")["international"] == 1


def test_variables_sans_fuite_de_donnees(df_pred, table):
    """Modifier les comptages d'un mois ne doit pas changer les variables de ce même mois."""
    modifie = df_pred.copy()
    masque = (modifie["Gare d'arrivée"] == "A") & (modifie["Date"] == "2023-06-01")
    modifie.loc[masque, COL_RETARDS] = 90
    modifie = ajouter_cible(modifie)
    avant = ligne(table, "A", "2023-06-01")[VARIABLES]
    apres = ligne(calculer_variables(modifie), "A", "2023-06-01")[VARIABLES]
    pd.testing.assert_series_equal(avant, apres)


def test_variables_ajoutent_le_mois_a_prevoir(table):
    dernier = table[table["Gare d'arrivée"] == "A"].sort_values("Date").iloc[-1]
    assert dernier["Date"] == DATES[-1] + pd.DateOffset(months=1)
    assert np.isnan(dernier["perturbe"])
    assert not np.isnan(dernier["retard_mois_dernier"])


def test_variables_mois_manquant(df_pred):
    """Un mois absent devient une ligne vide : le mois suivant n'a pas de « mois dernier »."""
    trou = df_pred[~((df_pred["Gare d'arrivée"] == "A") & (df_pred["Date"] == "2023-02-01"))]
    table = calculer_variables(trou)
    assert np.isnan(ligne(table, "A", "2023-03-01")["retard_mois_dernier"])


# --- mois de choc et découpage -------------------------------------------------

def test_detecter_mois_choc(df_pred):
    choc = df_pred.copy()
    choc.loc[choc["Date"] == "2023-04-01", COL_ANNULES] = 80
    assert pd.Timestamp("2023-04-01") not in detecter_mois_choc(df_pred)
    assert pd.Timestamp("2023-04-01") in detecter_mois_choc(choc)


def test_decouper_train_test(table):
    connues, train, test = decouper_train_test(table, "2024-01-01", mois_choc=pd.DatetimeIndex(["2023-04-01"]))
    assert train["Date"].max() < pd.Timestamp("2024-01-01") <= test["Date"].min()
    assert pd.Timestamp("2023-04-01") not in set(train["Date"])
    assert pd.Timestamp("2023-04-01") in set(connues["Date"])
    assert connues[["perturbe", "retard_mois_dernier", "retard_12_mois"]].notna().all().all()


def test_preparer_matrices_utilise_les_medianes_de_l_apprentissage(table):
    _, train, test = decouper_train_test(table, "2024-01-01")
    test = test.copy()
    test.loc[test.index[0], "retard_an_dernier"] = np.nan
    X_train, y_train, X_test, y_test, medianes = preparer_matrices(train, test)
    assert list(X_train.columns) == VARIABLES
    assert X_test.loc[test.index[0], "retard_an_dernier"] == medianes["retard_an_dernier"]
    assert not X_train.isna().any().any() and not X_test.isna().any().any()


# --- modèles et mesures ---------------------------------------------------------

@pytest.mark.parametrize("nom", ["logistique", "boosting", "foret"])
def test_creer_modele(nom):
    assert hasattr(creer_modele(nom), "predict_proba")


def test_creer_modele_inconnu():
    with pytest.raises(ValueError, match="inconnu"):
        creer_modele("arbre")


def test_entrainer_et_predire(table):
    _, train, test = decouper_train_test(table, "2024-01-01")
    X_train, y_train, X_test, _, _ = preparer_matrices(train, test)
    _, proba, prediction = entrainer_et_predire(creer_modele("logistique"), X_train, y_train, X_test)
    assert len(proba) == len(X_test)
    assert ((proba >= 0) & (proba <= 1)).all()
    assert (prediction == (proba > 0.5)).all()


def test_regle_mois_dernier():
    df = pd.DataFrame({"annulation_mois_dernier": [0.0, 0.1, 0.1], "retard_mois_dernier": [0.25, 0.1, 0.12]})
    # 0,1 + 0,9 × 0,12 = 0,208 > 0,20
    assert regle_mois_dernier(df).tolist() == [1, 0, 1]


def test_mesurer():
    m = mesurer([0, 0, 1, 1], [0, 1, 1, 1], proba=[0.1, 0.6, 0.7, 0.9])
    assert m["Rappel"] == 1.0
    assert m["Précision"] == pytest.approx(2 / 3)
    assert m["AUC"] == 1.0
    assert np.isnan(mesurer([0, 1], [0, 1])["AUC"])


def test_table_calibration():
    resultat = table_calibration(np.array([0.1, 0.15, 0.9, 0.95]), [0, 1, 1, 1])
    assert resultat["nombre de mois"].sum() == 4
    assert resultat.loc["0-20 %", "part réellement perturbée"] == 0.5
    assert resultat.loc["80-100 %", "part réellement perturbée"] == 1.0


def test_importance_variables(table):
    _, train, test = decouper_train_test(table, "2024-01-01")
    X_train, y_train, X_test, _, _ = preparer_matrices(train, test)
    modele, _, _ = entrainer_et_predire(creer_modele("foret"), X_train, y_train, X_test)
    importance = importance_variables(modele)
    assert sorted(importance.index) == sorted(VARIABLES)
    assert importance.is_monotonic_increasing


def test_sensibilite_seuils(df_pred, table):
    _, train, test = decouper_train_test(table, "2024-01-01")
    X_train, _, X_test, _, _ = preparer_matrices(train, test)
    resultat = sensibilite_seuils(df_pred, train, test, X_train, X_test, pd.DatetimeIndex([]), [0.15, 0.25])
    assert resultat.index.tolist() == ["15%", "25%"]
    assert resultat.shape[1] == 8


# --- prévision du mois suivant ------------------------------------------------------

def test_prevoir_mois_suivant(table, tmp_path):
    connues, _, _ = decouper_train_test(table, "2024-01-01")
    modele, medianes = entrainer_modele_final(connues)
    predictions = prevoir_mois_suivant(modele, table, medianes)
    assert len(predictions) == 2  # une ligne par liaison
    assert (predictions["mois_prevu"] == DATES[-1] + pd.DateOffset(months=1)).all()
    assert predictions["proba_perturbation"].between(0, 1).all()
    assert set(predictions["prevision"]) <= {"Normal", "Perturbé"}

    chemin = exporter_predictions(predictions, tmp_path / "resultats")
    assert pd.read_csv(chemin).shape == predictions.shape


def test_entrainer_modele_final_ecarte_les_mois_de_choc(table, caplog):
    connues, _, _ = decouper_train_test(table, "2024-01-01")
    choc = pd.DatetimeIndex(["2023-04-01"])
    with caplog.at_level(logging.INFO, logger="utils.prevision"):
        entrainer_modele_final(connues, choc)
    attendu = (~connues["Date"].isin(choc)).sum()
    assert f"Modèle final entraîné sur {attendu} lignes" in caplog.text


# --- exemples --------------------------------------------------------------------------

def test_resultats_test_et_chercher_resultat(table, caplog):
    _, train, test = decouper_train_test(table, "2024-01-01")
    n = len(test)
    prediction = np.ones(n, dtype=int)
    resultats = resultats_test(test, np.full(n, 0.8), prediction, np.zeros(n, dtype=int))
    attendu = np.where(test["perturbe"] == 1, "juste", "fausse alerte")
    assert (resultats["resultat"] == attendu).all()
    assert (resultats["prediction_regle"] == "Normal").all()

    trouve = chercher_resultat(resultats, "PARIS", "B", "2024-03-01", service="International")
    assert trouve["Gare d'arrivée"] == "B"
    with caplog.at_level(logging.WARNING, logger="utils.prevision"):
        assert chercher_resultat(resultats, "PARIS", "B", "2024-03-01") is None  # mauvais service
    assert "Aucun résultat" in caplog.text


def test_resultats_test_rate(table):
    _, _, test = decouper_train_test(table, "2024-01-01")
    n = len(test)
    resultats = resultats_test(test, np.zeros(n), np.zeros(n, dtype=int), np.zeros(n, dtype=int))
    attendu = np.where(test["perturbe"] == 1, "raté", "juste")
    assert (resultats["resultat"] == attendu).all()
