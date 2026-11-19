import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from utils.journal import NOM_GESTIONNAIRE, configurer_journal
from utils.nettoyage import (
    COL_RETARD_30,
    COLONNES_COMMENTAIRES,
    ajouter_variables_temps,
    invalider_retards_30_min,
    invalider_retards_moyens_negatifs,
    nettoyer,
    supprimer_commentaires,
    supprimer_lignes_sans_circulation,
    verifier_colonnes,
)

RETARD_TOUS_DEPART = "Retard moyen de tous les trains au départ"
RETARD_TOUS_ARRIVEE = "Retard moyen de tous les trains à l'arrivée"
RETARD_EN_RETARD = "Retard moyen des trains en retard à l'arrivée"
RETARD_15 = (
    "Retard moyen trains en retard > 15 (si liaison concurrencée par vol)"
)


@pytest.fixture
def donnees() -> pd.DataFrame:
    """Petit jeu de données brutes, une ligne par cas à tester.

    - ligne 0 : ligne valide, rien à corriger ;
    - ligne 1 : aucune circulation prévue -> ligne supprimée ;
    - ligne 2 : « > 30 min » négatif -> NaN ;
    - ligne 3 : « > 60 min » supérieur à « > 30 min » -> NaN ;
    - ligne 4 : retards moyens négatifs (tous les trains et trains en retard)
      -> NaN.
    """
    return pd.DataFrame(
        {
            "Date": ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05"],
            "Service": ["National"] * 5,
            "Gare de départ": ["PARIS LYON"] * 5,
            "Gare d'arrivée": ["MARSEILLE ST CHARLES"] * 5,
            "Nombre de circulations prévues": [300, 0, 250, 280, 260],
            "Nombre de trains annulés": [2, 0, 1, 0, 3],
            "Nombre de trains en retard à l'arrivée": [40, 0, 35, 50, 20],
            "Nombre trains en retard > 30min": [10, 0, -4, 3, 5],
            "Nombre trains en retard > 60min": [4, 0, 1, 6, 2],
            RETARD_EN_RETARD: [25.0, 0.0, 30.0, 40.0, -3.0],
            RETARD_15: [35.0, 0.0, 40.0, 50.0, 30.0],
            RETARD_TOUS_DEPART: [2.5, 0.0, 3.0, 4.0, -0.4],
            RETARD_TOUS_ARRIVEE: [4.0, 0.0, 5.0, 7.0, -472.6],
            "Commentaire annulations": [np.nan] * 5,
            "Commentaire retards au départ": [np.nan] * 5,
            "Commentaire retards à l'arrivée": [
                np.nan,
                np.nan,
                "Heurt d'un animal",
                np.nan,
                np.nan,
            ],
        }
    )


# --- verifier_colonnes -----------------------------------------------------


def test_verifier_colonnes_accepte_un_tableau_complet(
    donnees: pd.DataFrame,
) -> None:
    verifier_colonnes(donnees, ["Date", "Service"])


def test_verifier_colonnes_signale_les_colonnes_manquantes(
    donnees: pd.DataFrame,
) -> None:
    with pytest.raises(KeyError, match="Colonne inexistante"):
        verifier_colonnes(donnees, ["Date", "Colonne inexistante"])


def test_verifier_colonnes_refuse_autre_chose_qu_un_dataframe() -> None:
    with pytest.raises(TypeError):
        verifier_colonnes([1, 2, 3], ["Date"])


# --- règles une par une ----------------------------------------------------


def test_supprimer_commentaires(donnees: pd.DataFrame) -> None:
    df, n = supprimer_commentaires(donnees)
    assert n == 3
    assert not any(c in df.columns for c in COLONNES_COMMENTAIRES)


def test_supprimer_commentaires_sur_donnees_deja_nettoyees(
    donnees: pd.DataFrame,
) -> None:
    df, _ = supprimer_commentaires(donnees)
    df2, n = supprimer_commentaires(df)
    assert n == 0
    assert list(df2.columns) == list(df.columns)


def test_ajouter_variables_temps(donnees: pd.DataFrame) -> None:
    df = ajouter_variables_temps(donnees)
    assert pd.api.types.is_datetime64_any_dtype(df["Date"])
    assert df["Mois"].tolist() == [1, 2, 3, 4, 5]
    assert df["Année"].tolist() == [2024] * 5


def test_ajouter_variables_temps_date_illisible() -> None:
    with pytest.raises(ValueError):
        ajouter_variables_temps(pd.DataFrame({"Date": ["pas une date"]}))


def test_supprimer_lignes_sans_circulation(donnees: pd.DataFrame) -> None:
    df, n = supprimer_lignes_sans_circulation(donnees)
    assert n == 1
    assert (df["Nombre de circulations prévues"] > 0).all()
    assert "2024-02" not in df["Date"].tolist()


def test_invalider_retards_30_min(donnees: pd.DataFrame) -> None:
    df, n = invalider_retards_30_min(donnees)
    assert n == 2
    assert df[COL_RETARD_30].isna().tolist() == [
        False,
        False,
        True,
        True,
        False,
    ]
    assert df.loc[0, COL_RETARD_30] == 10


def test_invalider_retards_moyens_negatifs(donnees: pd.DataFrame) -> None:
    df, remplacees = invalider_retards_moyens_negatifs(donnees)
    assert remplacees == {
        RETARD_EN_RETARD: 1,
        RETARD_15: 0,
        RETARD_TOUS_DEPART: 1,
        RETARD_TOUS_ARRIVEE: 1,
    }
    assert (
        df.loc[4, [RETARD_EN_RETARD, RETARD_TOUS_DEPART, RETARD_TOUS_ARRIVEE]]
        .isna()
        .all()
    )
    # une valeur nulle n'est pas négative : elle est gardée
    assert df.loc[1, RETARD_TOUS_DEPART] == 0


# --- nettoyer : l'enchaînement complet -------------------------------------


def test_nettoyer_rapport(donnees: pd.DataFrame) -> None:
    _, rapport = nettoyer(donnees)
    assert rapport["lignes_initiales"] == 5
    assert rapport["lignes_finales"] == 4
    assert rapport["colonnes_supprimees"] == 3
    assert rapport["lignes_sans_circulation_supprimees"] == 1
    # la ligne 1 (0 circulation) est supprimée avant les corrections : il reste
    # 2 cases « > 30 min » et 3 retards moyens
    assert rapport[f"NaN : {COL_RETARD_30}"] == 2
    assert rapport["cases_mises_a_nan"] == 5


def test_nettoyer_ne_modifie_pas_les_donnees_d_origine(
    donnees: pd.DataFrame,
) -> None:
    copie = donnees.copy()
    nettoyer(donnees)
    pd.testing.assert_frame_equal(donnees, copie)


def test_nettoyer_garde_les_comptages_complets(donnees: pd.DataFrame) -> None:
    df, _ = nettoyer(donnees)
    comptages = [
        "Nombre de circulations prévues",
        "Nombre de trains annulés",
        "Nombre de trains en retard à l'arrivée",
    ]
    assert df[comptages].notna().all().all()


def test_nettoyer_ne_laisse_aucune_valeur_negative(
    donnees: pd.DataFrame,
) -> None:
    df, _ = nettoyer(donnees)
    assert not df.select_dtypes("number").lt(0).any().any()


def test_nettoyer_index_remis_a_zero(donnees: pd.DataFrame) -> None:
    df, _ = nettoyer(donnees)
    assert df.index.tolist() == list(range(len(df)))


def test_nettoyer_peut_etre_relance_sur_ses_propres_resultats(
    donnees: pd.DataFrame,
) -> None:
    df, _ = nettoyer(donnees)
    df2, rapport = nettoyer(df)
    assert rapport["lignes_sans_circulation_supprimees"] == 0
    assert rapport["cases_mises_a_nan"] == 0
    assert len(df2) == len(df)


def test_nettoyer_colonne_manquante(donnees: pd.DataFrame) -> None:
    with pytest.raises(KeyError, match="Nombre de circulations prévues"):
        nettoyer(donnees.drop(columns="Nombre de circulations prévues"))


def test_nettoyer_ecrit_dans_les_logs(
    donnees: pd.DataFrame, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="utils.nettoyage"):
        nettoyer(donnees)
    assert "Début du nettoyage" in caplog.text
    assert "Lignes sans circulation prévue supprimées : 1" in caplog.text


# --- journal
# ------------------------------------------------------------------


def test_configurer_journal_ecrit_un_fichier(
    tmp_path: Path, donnees: pd.DataFrame
) -> None:
    chemin = configurer_journal(dossier=tmp_path / "logs")
    nettoyer(donnees)
    contenu = chemin.read_text(encoding="utf-8")
    assert "Fin du nettoyage : 4 lignes gardées" in contenu


def test_configurer_journal_n_ecrit_pas_en_double(tmp_path: Path) -> None:
    configurer_journal(dossier=tmp_path)
    chemin = configurer_journal(dossier=tmp_path)
    logging.getLogger("test").info("message unique")
    assert chemin.read_text(encoding="utf-8").count("message unique") == 1


def test_configurer_journal_affiche_aussi_a_l_ecran(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    chemin = configurer_journal(dossier=tmp_path, afficher=True)
    logging.getLogger("test").info("message visible")
    assert "message visible" in capsys.readouterr().err
    assert "message visible" in chemin.read_text(encoding="utf-8")
    # nettoyage : retirer les gestionnaires ajoutés, pour ne pas gêner les
    # autres tests
    racine = logging.getLogger()
    for gestionnaire in list(racine.handlers):
        if gestionnaire.get_name() == NOM_GESTIONNAIRE:
            racine.removeHandler(gestionnaire)
            gestionnaire.close()
