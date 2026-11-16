"""Prévision du mois suivant (Normal ou Perturbé) pour chaque liaison TGV.

Ce module regroupe les calculs du notebook ``notebooks/prevision.ipynb``, où chaque choix
est expliqué : la cible, les huit variables explicatives, les mois de choc, le découpage
dans le temps, les modèles, les mesures de qualité et la prévision du mois suivant.

Une liaison est définie par le triplet (gare de départ, gare d'arrivée, service). Un mois
est **Perturbé** si plus de 20 % des trains prévus sont annulés ou arrivent en retard.

Example:
    >>> from utils.nettoyage import nettoyer  # doctest: +SKIP
    >>> df_pred = ajouter_cible(preparer_donnees(nettoyer(data)[0]))  # doctest: +SKIP
    >>> table = calculer_variables(df_pred)  # doctest: +SKIP
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from utils.nettoyage import verifier_colonnes

logger = logging.getLogger(__name__)

COL_PREVUES = "Nombre de circulations prévues"
COL_ANNULES = "Nombre de trains annulés"
COL_RETARDS = "Nombre de trains en retard à l'arrivée"
CLE_LIAISON = ["Gare de départ", "Gare d'arrivée", "Service"]

#: Seuil de perturbation : part des trains prévus annulés ou en retard au-delà de laquelle le mois est perturbé.
SEUIL_PERTURBATION = 0.20

#: Les huit variables explicatives, toutes connues à la fin du mois précédent.
VARIABLES = [
    "mois",
    "international",
    "retard_mois_dernier",
    "annulation_mois_dernier",
    "retard_12_mois",
    "annulation_12_mois",
    "retard_an_dernier",
    "annulation_an_dernier",
]

#: Noms des modèles que :func:`creer_modele` sait construire.
MODELES = ("logistique", "boosting", "foret")


# ---------------------------------------------------------------------------
# Données et cible
# ---------------------------------------------------------------------------
def preparer_donnees(df):
    """Garde les colonnes utiles à la prévision et ajoute le nombre de trains réellement circulés.

    Args:
        df (pandas.DataFrame): Données nettoyées par :func:`utils.nettoyage.nettoyer`, avec une
            colonne ``Date`` au format date.

    Returns:
        pandas.DataFrame: Une ligne par liaison et par mois, avec la clé de la liaison, la date,
        les trois comptages (prévus, annulés, en retard à l'arrivée) et ``circulations_reelles``.

    Raises:
        KeyError: Si une colonne nécessaire est absente.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"Gare de départ": ["A"], "Gare d'arrivée": ["B"], "Service": ["National"],
        ...                    "Date": pd.to_datetime(["2024-01-01"]), "Nombre de circulations prévues": [100],
        ...                    "Nombre de trains annulés": [4], "Nombre de trains en retard à l'arrivée": [12]})
        >>> int(preparer_donnees(df).loc[0, "circulations_reelles"])
        96
    """
    colonnes = CLE_LIAISON + ["Date", COL_PREVUES, COL_ANNULES, COL_RETARDS]
    verifier_colonnes(df, colonnes)
    df_pred = df[colonnes].copy()
    df_pred["circulations_reelles"] = df_pred[COL_PREVUES] - df_pred[COL_ANNULES]
    logger.info("Données de prévision : %d lignes, %d liaisons", len(df_pred), df_pred.groupby(CLE_LIAISON).ngroups)
    return df_pred


def controler_comptages(df_pred):
    """Compte les lignes dont les comptages rendent un taux impossible à calculer.

    Args:
        df_pred (pandas.DataFrame): Données renvoyées par :func:`preparer_donnees`.

    Returns:
        pandas.Series: Pour chaque contrôle, le nombre de lignes en défaut. Toutes les valeurs
        doivent être nulles après nettoyage.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"Nombre de circulations prévues": [10, 0], "Nombre de trains annulés": [1, 0],
        ...                    "Nombre de trains en retard à l'arrivée": [2, 0], "circulations_reelles": [9, 0]})
        >>> int(controler_comptages(df)["Circulations prévues = 0"])
        1
    """
    comptages = df_pred[[COL_PREVUES, COL_ANNULES, COL_RETARDS]]
    return pd.Series({
        "Circulations prévues = 0": int((df_pred[COL_PREVUES] == 0).sum()),
        "Comptage négatif": int((comptages < 0).any(axis=1).sum()),
        "Comptage manquant": int(comptages.isna().any(axis=1).sum()),
        "Annulés > prévues": int((df_pred[COL_ANNULES] > df_pred[COL_PREVUES]).sum()),
        "Retards > trains réellement circulés": int((df_pred[COL_RETARDS] > df_pred["circulations_reelles"]).sum()),
    }, name="lignes")


def ajouter_cible(df_pred, seuil=SEUIL_PERTURBATION):
    """Ajoute le taux de perturbation du mois et la cible ``perturbe`` (0 ou 1).

    Le taux de perturbation est la part des trains prévus qui sont annulés ou arrivent en
    retard : (annulés + retards à l'arrivée) / circulations prévues.

    Args:
        df_pred (pandas.DataFrame): Données renvoyées par :func:`preparer_donnees`.
        seuil (float): Taux au-delà duquel le mois est perturbé. Par défaut 0,20.

    Returns:
        pandas.DataFrame: Une copie des données avec les colonnes ``taux_perturbation`` et ``perturbe``.

    Raises:
        ValueError: Si le seuil n'est pas strictement compris entre 0 et 1.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"Nombre de circulations prévues": [100, 100], "Nombre de trains annulés": [5, 0],
        ...                    "Nombre de trains en retard à l'arrivée": [20, 10]})
        >>> ajouter_cible(df)["perturbe"].tolist()
        [1, 0]
    """
    if not 0 < seuil < 1:
        raise ValueError(f"Le seuil doit être compris entre 0 et 1, pas {seuil}.")
    df_pred = df_pred.copy()
    df_pred["taux_perturbation"] = (df_pred[COL_ANNULES] + df_pred[COL_RETARDS]) / df_pred[COL_PREVUES]
    df_pred["perturbe"] = (df_pred["taux_perturbation"] > seuil).astype(int)
    logger.info("Cible créée avec un seuil de %.0f %% : %.1f %% de mois perturbés", seuil * 100,
                df_pred["perturbe"].mean() * 100)
    return df_pred


def part_perturbee_selon_seuil(df_pred, seuils):
    """Calcule la part des mois perturbés pour plusieurs seuils.

    Args:
        df_pred (pandas.DataFrame): Données contenant la colonne ``taux_perturbation``.
        seuils (list[float]): Seuils à comparer.

    Returns:
        pandas.Series: La part des mois perturbés, indexée par le seuil écrit en pourcentage.

    Example:
        >>> import pandas as pd
        >>> part_perturbee_selon_seuil(pd.DataFrame({"taux_perturbation": [0.1, 0.3]}), [0.2]).tolist()
        [0.5]
    """
    return pd.Series(
        {f"{s:.0%}": (df_pred["taux_perturbation"] > s).mean() for s in seuils},
        name="part des mois perturbés",
    )


# ---------------------------------------------------------------------------
# Variables explicatives
# ---------------------------------------------------------------------------
def _variables_liaison(groupe):
    """Calcule les variables d'une seule liaison, pour chaque mois (voir :func:`calculer_variables`)."""
    groupe = groupe.set_index("Date").sort_index()
    calendrier = pd.date_range(groupe.index.min(), groupe.index.max() + pd.DateOffset(months=1), freq="MS")
    g = groupe.reindex(calendrier)

    taux_annulation = g[COL_ANNULES] / g[COL_PREVUES]
    taux_retard = g[COL_RETARDS] / g["circulations_reelles"].where(g["circulations_reelles"] > 0)

    v = pd.DataFrame(index=calendrier)
    v["retard_mois_dernier"] = taux_retard.shift(1)
    v["annulation_mois_dernier"] = taux_annulation.shift(1)

    def somme_12(col):
        return g[col].rolling(12, min_periods=6).sum().shift(1)

    v["retard_12_mois"] = somme_12(COL_RETARDS) / somme_12("circulations_reelles")
    v["annulation_12_mois"] = somme_12(COL_ANNULES) / somme_12(COL_PREVUES)

    v["retard_an_dernier"] = taux_retard.shift(12)
    v["annulation_an_dernier"] = taux_annulation.shift(12)

    v["taux_perturbation"] = g["taux_perturbation"]
    v["perturbe"] = g["perturbe"]
    return v


def calculer_variables(df_pred):
    """Calcule les huit variables explicatives de chaque liaison, pour chaque mois.

    Pour le mois ``t``, les variables n'utilisent que des mois antérieurs :

    - ``retard_mois_dernier``, ``annulation_mois_dernier`` : taux du mois ``t-1`` ;
    - ``retard_12_mois``, ``annulation_12_mois`` : taux des mois ``t-12`` à ``t-1`` (sommes,
      puis division ; au moins 6 mois connus) ;
    - ``retard_an_dernier``, ``annulation_an_dernier`` : taux du mois ``t-12`` ;
    - ``mois`` : mois de l'année visé ; ``international`` : 1 si le service est international.

    Chaque série est remise sur un calendrier mensuel complet (un mois absent devient une
    ligne vide) et prolongée d'un mois : ce dernier mois est celui à prévoir, dont la cible
    est inconnue.

    Args:
        df_pred (pandas.DataFrame): Données renvoyées par :func:`ajouter_cible`.

    Returns:
        pandas.DataFrame: Une ligne par liaison et par mois (mois à prévoir compris), avec la clé,
        la date, les variables de :data:`VARIABLES`, ``taux_perturbation`` et ``perturbe``.

    Raises:
        KeyError: Si une colonne nécessaire est absente.
    """
    verifier_colonnes(df_pred, CLE_LIAISON + ["Date", "circulations_reelles", "taux_perturbation", "perturbe"])
    table = (
        df_pred.groupby(CLE_LIAISON)
        .apply(_variables_liaison, include_groups=False)
        .rename_axis(CLE_LIAISON + ["Date"])
        .reset_index()
    )
    table["mois"] = table["Date"].dt.month
    table["international"] = (table["Service"] == "International").astype(int)
    logger.info("Variables calculées : %d lignes", len(table))
    return table


# ---------------------------------------------------------------------------
# Mois de choc et découpage
# ---------------------------------------------------------------------------
def detecter_mois_choc(df_pred, nb_ecarts=3):
    """Repère les mois où tout le réseau est anormalement perturbé (règle de Hampel).

    Un mois est un choc si son taux de perturbation national dépasse la médiane de plus de
    ``nb_ecarts`` écarts robustes. L'écart robuste vaut 1,4826 fois l'écart absolu médian.

    Args:
        df_pred (pandas.DataFrame): Données contenant ``Date`` et les trois comptages.
        nb_ecarts (float): Nombre d'écarts robustes au-delà duquel un mois est un choc. Par défaut 3.

    Returns:
        pandas.DatetimeIndex: Les mois de choc.
    """
    mensuel = df_pred.groupby("Date")[[COL_PREVUES, COL_ANNULES, COL_RETARDS]].sum()
    taux_national = (mensuel[COL_ANNULES] + mensuel[COL_RETARDS]) / mensuel[COL_PREVUES]
    mediane = taux_national.median()
    ecart_robuste = 1.4826 * (taux_national - mediane).abs().median()
    mois_choc = taux_national.index[taux_national > mediane + nb_ecarts * ecart_robuste]
    logger.info("Mois de choc : %s", [m.strftime("%Y-%m") for m in mois_choc])
    return mois_choc


def decouper_train_test(table, date_coupure="2025-01-01", mois_choc=None):
    """Sépare les mois connus en apprentissage (avant la coupure) et test (à partir de la coupure).

    Les lignes sans cible ou sans historique suffisant sont écartées. Les mois de choc sont
    retirés de l'apprentissage seulement, pour juger honnêtement le modèle sur le test.

    Args:
        table (pandas.DataFrame): Table renvoyée par :func:`calculer_variables`.
        date_coupure (str | pandas.Timestamp): Premier mois du test. Par défaut ``"2025-01-01"``.
        mois_choc (pandas.DatetimeIndex | None): Mois à retirer de l'apprentissage.

    Returns:
        tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]: Les mois connus (tous), le jeu
        d'apprentissage et le jeu de test.
    """
    connues = table.dropna(subset=["perturbe", "retard_mois_dernier", "retard_12_mois"]).copy()
    connues["perturbe"] = connues["perturbe"].astype(int)
    train = connues[connues["Date"] < date_coupure]
    test = connues[connues["Date"] >= date_coupure]
    if mois_choc is not None:
        train = train[~train["Date"].isin(mois_choc)]
    logger.info("Apprentissage : %d lignes | Test : %d lignes", len(train), len(test))
    return connues, train, test


def preparer_matrices(train, test, variables=None):
    """Construit les matrices des modèles, en remplaçant les valeurs manquantes par la médiane de l'apprentissage.

    Args:
        train (pandas.DataFrame): Jeu d'apprentissage.
        test (pandas.DataFrame): Jeu de test.
        variables (list[str] | None): Variables à utiliser. Par défaut :data:`VARIABLES`.

    Returns:
        tuple: ``(X_train, y_train, X_test, y_test, medianes)``. Les médianes sont calculées sur
        l'apprentissage seul, pour ne rien apprendre du test.
    """
    variables = VARIABLES if variables is None else variables
    medianes = train[variables].median()
    return (
        train[variables].fillna(medianes), train["perturbe"],
        test[variables].fillna(medianes), test["perturbe"],
        medianes,
    )


# ---------------------------------------------------------------------------
# Modèles et mesures
# ---------------------------------------------------------------------------
def creer_modele(nom):
    """Crée un modèle non entraîné.

    Tous les modèles utilisent ``class_weight="balanced"``, pour ne pas négliger les mois
    perturbés, minoritaires.

    Args:
        nom (str): ``"logistique"`` (régression logistique, variables mises à la même échelle),
            ``"boosting"`` (gradient boosting) ou ``"foret"`` (forêt aléatoire de 300 arbres).

    Returns:
        sklearn.base.BaseEstimator: Le modèle.

    Raises:
        ValueError: Si le nom n'est pas dans :data:`MODELES`.

    Example:
        >>> type(creer_modele("foret")).__name__
        'RandomForestClassifier'
    """
    if nom == "logistique":
        return make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000))
    if nom == "boosting":
        return HistGradientBoostingClassifier(class_weight="balanced", random_state=42)
    if nom == "foret":
        return RandomForestClassifier(
            n_estimators=300, min_samples_leaf=5, class_weight="balanced", random_state=42, n_jobs=-1
        )
    raise ValueError(f"Modèle inconnu : {nom!r}. Choix possibles : {MODELES}")


def entrainer_et_predire(modele, X_train, y_train, X_test, seuil_proba=0.5):
    """Entraîne un modèle et prédit le jeu de test.

    Args:
        modele (sklearn.base.BaseEstimator): Modèle créé par :func:`creer_modele`.
        X_train (pandas.DataFrame): Variables d'apprentissage.
        y_train (pandas.Series): Cible d'apprentissage.
        X_test (pandas.DataFrame): Variables de test.
        seuil_proba (float): Probabilité au-delà de laquelle on annonce « Perturbé ». Par défaut 0,5.

    Returns:
        tuple: ``(modele, proba, prediction)`` : le modèle entraîné, la probabilité de perturbation
        de chaque mois du test et la prédiction (0 ou 1).
    """
    modele.fit(X_train, y_train)
    proba = modele.predict_proba(X_test)[:, 1]
    prediction = (proba > seuil_proba).astype(int)
    logger.info("%s entraîné sur %d lignes", type(modele).__name__, len(X_train))
    return modele, proba, prediction


def regle_mois_dernier(df, seuil=SEUIL_PERTURBATION):
    """Prévision de référence : le mois prochain sera comme le mois dernier.

    Le taux de perturbation du mois précédent est reconstitué à partir des deux taux :
    taux d'annulation + (1 − taux d'annulation) × taux de retard.

    Args:
        df (pandas.DataFrame): Données contenant ``annulation_mois_dernier`` et ``retard_mois_dernier``.
        seuil (float): Seuil de perturbation. Par défaut 0,20.

    Returns:
        pandas.Series: 1 si le mois précédent était perturbé, 0 sinon.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"annulation_mois_dernier": [0.1, 0.0], "retard_mois_dernier": [0.2, 0.1]})
        >>> regle_mois_dernier(df).tolist()
        [1, 0]
    """
    annulation, retard = df["annulation_mois_dernier"], df["retard_mois_dernier"]
    return ((annulation + (1 - annulation) * retard) > seuil).astype(int)


def mesurer(y_vrai, y_predit, proba=None):
    """Calcule les mesures de qualité d'une prévision.

    Args:
        y_vrai (array-like): Réalité (0 ou 1).
        y_predit (array-like): Prévision (0 ou 1).
        proba (array-like | None): Probabilité de perturbation, pour l'AUC. Sans probabilité,
            l'AUC vaut NaN.

    Returns:
        dict[str, float]: ``F1 macro``, ``Rappel``, ``Précision`` et ``AUC``.

    Example:
        >>> m = mesurer([0, 1, 1, 0], [0, 1, 0, 0])
        >>> m["Rappel"], m["Précision"]
        (0.5, 1.0)
    """
    return {
        "F1 macro": f1_score(y_vrai, y_predit, average="macro"),
        "Rappel": recall_score(y_vrai, y_predit),
        "Précision": precision_score(y_vrai, y_predit),
        "AUC": roc_auc_score(y_vrai, proba) if proba is not None else np.nan,
    }


def table_calibration(proba, y_vrai, bornes=(0, 0.2, 0.4, 0.6, 0.8, 1.0)):
    """Compare la probabilité annoncée à la part réelle de mois perturbés, par tranche de probabilité.

    Args:
        proba (array-like): Probabilités annoncées par le modèle.
        y_vrai (array-like): Réalité (0 ou 1).
        bornes (tuple[float]): Bornes des tranches de probabilité.

    Returns:
        pandas.DataFrame: Pour chaque tranche, la part réellement perturbée et le nombre de mois.
    """
    etiquettes = [f"{bornes[i] * 100:.0f}-{bornes[i + 1] * 100:.0f} %" for i in range(len(bornes) - 1)]
    groupes = pd.cut(proba, bins=list(bornes), include_lowest=True, labels=etiquettes)
    resultat = pd.DataFrame({"groupe": groupes, "perturbe": np.asarray(y_vrai)}).groupby(
        "groupe", observed=False)["perturbe"].agg(["mean", "size"])
    resultat.columns = ["part réellement perturbée", "nombre de mois"]
    return resultat


def importance_variables(modele, variables=None):
    """Renvoie l'importance des variables d'un modèle à base d'arbres, de la plus faible à la plus forte.

    Args:
        modele (sklearn.base.BaseEstimator): Modèle entraîné ayant un attribut ``feature_importances_``.
        variables (list[str] | None): Noms des variables. Par défaut :data:`VARIABLES`.

    Returns:
        pandas.Series: L'importance de chaque variable, triée par ordre croissant.
    """
    variables = VARIABLES if variables is None else variables
    return pd.Series(modele.feature_importances_, index=variables).sort_values()


def sensibilite_seuils(df_pred, train, test, X_train, X_test, mois_choc, seuils):
    """Refait l'apprentissage et le test de la forêt aléatoire pour plusieurs seuils de perturbation.

    Les variables et la période de test restent les mêmes : seule la cible change.

    Args:
        df_pred (pandas.DataFrame): Toutes les données, avec ``taux_perturbation`` et ``Date``.
        train (pandas.DataFrame): Jeu d'apprentissage.
        test (pandas.DataFrame): Jeu de test.
        X_train (pandas.DataFrame): Variables d'apprentissage.
        X_test (pandas.DataFrame): Variables de test.
        mois_choc (pandas.DatetimeIndex): Mois de choc national.
        seuils (list[float]): Seuils à comparer.

    Returns:
        pandas.DataFrame: Pour chaque seuil, la part de mois perturbés, la part venant d'un mois de
        choc, puis le rappel, la précision et le F1 de la forêt aléatoire et de la règle
        « comme le mois dernier ».
    """
    resultats = {}
    for seuil in seuils:
        y_train_s = (train["taux_perturbation"] > seuil).astype(int)
        y_test_s = (test["taux_perturbation"] > seuil).astype(int)
        foret = creer_modele("foret").fit(X_train, y_train_s)
        pred_foret = foret.predict(X_test)
        pred_regle = regle_mois_dernier(test, seuil)
        perturbes = df_pred["taux_perturbation"] > seuil
        resultats[f"{seuil:.0%}"] = {
            "mois perturbés (test)": y_test_s.mean(),
            "dont mois de choc (tout l'historique)": df_pred.loc[perturbes, "Date"].isin(mois_choc).mean(),
            "rappel forêt": recall_score(y_test_s, pred_foret),
            "rappel règle": recall_score(y_test_s, pred_regle),
            "précision forêt": precision_score(y_test_s, pred_foret),
            "précision règle": precision_score(y_test_s, pred_regle),
            "F1 forêt": f1_score(y_test_s, pred_foret, average="macro"),
            "F1 règle": f1_score(y_test_s, pred_regle, average="macro"),
        }
        logger.info("Seuil %.0f %% testé", seuil * 100)
    return pd.DataFrame(resultats).T


# ---------------------------------------------------------------------------
# Prévision du mois suivant
# ---------------------------------------------------------------------------
def entrainer_modele_final(connues, mois_choc=None, variables=None):
    """Entraîne la forêt aléatoire sur tous les mois connus (hors mois de choc).

    Args:
        connues (pandas.DataFrame): Tous les mois connus, renvoyés par :func:`decouper_train_test`.
        mois_choc (pandas.DatetimeIndex | None): Mois à écarter.
        variables (list[str] | None): Variables à utiliser. Par défaut :data:`VARIABLES`.

    Returns:
        tuple: ``(modele, medianes)`` : le modèle entraîné et les médianes utilisées pour remplacer
        les valeurs manquantes.
    """
    variables = VARIABLES if variables is None else variables
    toutes = connues if mois_choc is None else connues[~connues["Date"].isin(mois_choc)]
    medianes = toutes[variables].median()
    modele = creer_modele("foret").fit(toutes[variables].fillna(medianes), toutes["perturbe"])
    logger.info("Modèle final entraîné sur %d lignes", len(toutes))
    return modele, medianes


def prevoir_mois_suivant(modele, table, medianes, variables=None, seuil_proba=0.5):
    """Prévoit le mois qui suit la dernière donnée, pour chaque liaison qui a assez d'historique.

    Args:
        modele (sklearn.base.BaseEstimator): Modèle entraîné par :func:`entrainer_modele_final`.
        table (pandas.DataFrame): Table renvoyée par :func:`calculer_variables`.
        medianes (pandas.Series): Médianes renvoyées par :func:`entrainer_modele_final`.
        variables (list[str] | None): Variables à utiliser. Par défaut :data:`VARIABLES`.
        seuil_proba (float): Probabilité au-delà de laquelle on annonce « Perturbé ». Par défaut 0,5.

    Returns:
        pandas.DataFrame: Une ligne par liaison, avec la clé, ``mois_prevu``,
        ``proba_perturbation`` (arrondie à 3 décimales) et ``prevision`` (``"Normal"`` ou ``"Perturbé"``).
    """
    variables = VARIABLES if variables is None else variables
    mois_a_prevoir = table["Date"].max()
    a_prevoir = table[table["Date"] == mois_a_prevoir].dropna(subset=["retard_mois_dernier", "retard_12_mois"])
    predictions = a_prevoir[CLE_LIAISON + ["Date"]].rename(columns={"Date": "mois_prevu"})
    predictions["proba_perturbation"] = modele.predict_proba(a_prevoir[variables].fillna(medianes))[:, 1].round(3)
    predictions["prevision"] = np.where(predictions["proba_perturbation"] > seuil_proba, "Perturbé", "Normal")
    logger.info("Prévision de %s : %d liaisons, %d annoncées perturbées", f"{mois_a_prevoir:%Y-%m}",
                len(predictions), int((predictions["prevision"] == "Perturbé").sum()))
    return predictions


def exporter_predictions(predictions, dossier, nom_fichier="predictions_liaisons.csv"):
    """Écrit les prévisions dans un fichier CSV.

    Args:
        predictions (pandas.DataFrame): Prévisions renvoyées par :func:`prevoir_mois_suivant`.
        dossier (str | pathlib.Path): Dossier de destination, créé s'il n'existe pas.
        nom_fichier (str): Nom du fichier. Par défaut ``"predictions_liaisons.csv"``.

    Returns:
        pathlib.Path: Chemin du fichier écrit.
    """
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / nom_fichier
    predictions.to_csv(chemin, index=False)
    logger.info("Prévisions exportées dans %s", chemin)
    return chemin


# ---------------------------------------------------------------------------
# Exemples
# ---------------------------------------------------------------------------
def resultats_test(test, proba, prediction, regle):
    """Rassemble, pour chaque mois du test, ce que le modèle savait, ce qu'il a prédit et la réalité.

    Args:
        test (pandas.DataFrame): Jeu de test.
        proba (array-like): Probabilités de la forêt aléatoire.
        prediction (array-like): Prédictions de la forêt aléatoire (0 ou 1).
        regle (array-like): Prédictions de la règle « comme le mois dernier » (0 ou 1).

    Returns:
        pandas.DataFrame: Le jeu de test enrichi de ``proba_perturbation``, ``prediction_foret``,
        ``prediction_regle``, ``realite`` et ``resultat`` (``"juste"``, ``"fausse alerte"`` ou ``"raté"``).
    """
    resultats = test[CLE_LIAISON + ["Date", "retard_mois_dernier", "annulation_mois_dernier",
                                    "retard_12_mois", "taux_perturbation", "perturbe"]].copy()
    resultats["proba_perturbation"] = proba
    resultats["prediction_foret"] = np.where(np.asarray(prediction) == 1, "Perturbé", "Normal")
    resultats["prediction_regle"] = np.where(np.asarray(regle) == 1, "Perturbé", "Normal")
    resultats["realite"] = np.where(resultats["perturbe"] == 1, "Perturbé", "Normal")
    resultats["resultat"] = np.select(
        [resultats["prediction_foret"] == resultats["realite"], resultats["prediction_foret"] == "Perturbé"],
        ["juste", "fausse alerte"],
        default="raté",
    )
    return resultats


def chercher_resultat(resultats, depart, arrivee, mois, service="National"):
    """Renvoie le résultat d'une liaison pour un mois du test.

    Args:
        resultats (pandas.DataFrame): Table renvoyée par :func:`resultats_test`.
        depart (str): Gare de départ.
        arrivee (str): Gare d'arrivée.
        mois (str | pandas.Timestamp): Mois cherché, par exemple ``"2025-06-01"``.
        service (str): ``"National"`` ou ``"International"``. Par défaut ``"National"``.

    Returns:
        pandas.Series | None: La ligne trouvée, ou ``None`` si la liaison ou le mois n'est pas dans le test.
    """
    ligne = resultats[
        (resultats["Gare de départ"] == depart)
        & (resultats["Gare d'arrivée"] == arrivee)
        & (resultats["Service"] == service)
        & (resultats["Date"] == pd.Timestamp(mois))
    ]
    if ligne.empty:
        logger.warning("Aucun résultat pour %s → %s (%s) en %s", depart, arrivee, service, mois)
        return None
    return ligne.iloc[0]
