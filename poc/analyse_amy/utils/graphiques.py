"""Graphiques utilisés dans les notebooks.

Chaque fonction trace un graphique et renvoie la figure matplotlib, sans l'afficher. Dans un
notebook, on l'affiche avec ``plt.show()`` :

Example:
    >>> import matplotlib.pyplot as plt
    >>> import pandas as pd
    >>> fig = tracer_barres(pd.Series([1, 2], index=["a", "b"]), "Exemple")
    >>> fig.axes[0].get_title()
    'Exemple'
    >>> plt.close(fig)
"""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.metrics import ConfusionMatrixDisplay


def tracer_barres(serie, titre, xlabel="", ylabel="", horizontal=False, couleur=None,
                  ligne_reference=None, ylim=None, taille=(10, 4)):
    """Trace un diagramme en barres à partir d'une série.

    Args:
        serie (pandas.Series): Valeurs à tracer ; l'index donne les étiquettes des barres.
        titre (str): Titre du graphique.
        xlabel (str): Titre de l'axe horizontal.
        ylabel (str): Titre de l'axe vertical.
        horizontal (bool): Si ``True``, barres horizontales. Par défaut ``False``.
        couleur (str | None): Couleur des barres. Par défaut, la couleur de matplotlib.
        ligne_reference (float | None): Valeur où tracer une ligne grise de référence
            (verticale si les barres sont horizontales, horizontale sinon).
        ylim (tuple[float, float] | None): Bornes de l'axe des valeurs (barres verticales seulement).
        taille (tuple[float, float]): Taille de la figure, en pouces.

    Returns:
        matplotlib.figure.Figure: La figure.
    """
    fig, ax = plt.subplots(figsize=taille)
    serie.plot(kind="barh" if horizontal else "bar", ax=ax, color=couleur, rot=0)
    if ligne_reference is not None:
        if horizontal:
            ax.axvline(ligne_reference, color="grey", linewidth=1)
        else:
            ax.axhline(ligne_reference, color="grey", linewidth=1)
    if ylim is not None and not horizontal:
        ax.set_ylim(*ylim)
    ax.set_title(titre)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    return fig


def tracer_evolution(par_annee, par_mois, variables, titre_annee="Moyenne par année",
                     titre_mois="Moyenne par mois de l'année", unite="%"):
    """Trace côte à côte l'évolution d'indicateurs par année et par mois de l'année.

    Args:
        par_annee (pandas.DataFrame): Moyennes par année, avec une colonne ``Année``.
        par_mois (pandas.DataFrame): Moyennes par mois, avec une colonne ``Mois``.
        variables (list[str]): Indicateurs à tracer (une courbe chacun).
        titre_annee (str): Titre du graphique de gauche.
        titre_mois (str): Titre du graphique de droite.
        unite (str): Titre de l'axe vertical. Par défaut ``"%"``.

    Returns:
        matplotlib.figure.Figure: La figure.
    """
    fig, axes = plt.subplots(1, 2, figsize=(16, 5))
    for col in variables:
        axes[0].plot(par_annee["Année"], par_annee[col], marker="o", label=col)
        axes[1].plot(par_mois["Mois"], par_mois[col], marker="o", label=col)
    axes[0].set_title(titre_annee)
    axes[0].set_xlabel("Année")
    axes[1].set_title(titre_mois)
    axes[1].set_xlabel("Mois")
    axes[1].set_xticks(range(1, 13))
    for ax in axes:
        ax.set_ylabel(unite)
        ax.legend()
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def tracer_matrices_confusion(y_vrai, y_predit, titre, etiquettes=("Normal", "Perturbé")):
    """Trace la matrice de confusion en nombre de mois et en part de chaque réalité.

    Args:
        y_vrai (array-like): Réalité (0 ou 1).
        y_predit (array-like): Prévision (0 ou 1).
        titre (str): Titre général.
        etiquettes (tuple[str, str]): Noms des classes 0 et 1.

    Returns:
        matplotlib.figure.Figure: La figure, avec deux matrices côte à côte.
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    ConfusionMatrixDisplay.from_predictions(
        y_vrai, y_predit, display_labels=list(etiquettes), cmap="Blues", colorbar=False, ax=axes[0])
    axes[0].set_title("Nombre de mois")
    ConfusionMatrixDisplay.from_predictions(
        y_vrai, y_predit, display_labels=list(etiquettes), normalize="true",
        values_format=".0%", cmap="Blues", colorbar=False, ax=axes[1])
    axes[1].set_title("Part de chaque réalité")
    for ax in axes:
        ax.set_xlabel("Prévision")
        ax.set_ylabel("Réalité")
    fig.suptitle(titre)
    fig.tight_layout()
    return fig


def tracer_avant_apres(avant, apres, colonnes, titre, unite="Retard moyen (minutes)"):
    """Compare, par des boîtes à moustaches, des colonnes avant et après nettoyage.

    Args:
        avant (pandas.DataFrame): Données avant nettoyage.
        apres (pandas.DataFrame): Données après nettoyage.
        colonnes (list[str]): Colonnes à comparer (un graphique chacune).
        titre (str): Titre général.
        unite (str): Titre de l'axe vertical.

    Returns:
        matplotlib.figure.Figure: La figure.
    """
    fig, axes = plt.subplots(1, len(colonnes), figsize=(7 * len(colonnes), 5), squeeze=False)
    for ax, col in zip(axes[0], colonnes):
        comparaison = pd.concat([
            pd.DataFrame({"État": "Avant nettoyage", unite: avant[col].to_numpy()}),
            pd.DataFrame({"État": "Après nettoyage", unite: apres[col].to_numpy()}),
        ]).dropna()
        sns.boxplot(data=comparaison, x="État", y=unite, ax=ax)
        ax.set_title(col)
        ax.set_xlabel("")
        ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.suptitle(titre)
    fig.tight_layout()
    return fig
