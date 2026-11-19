import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

from projet_sncf.utils.month_variations import filter_route


def plot_heatmap_cancelations(pivot, title, figsize=(12, 6)):
    """Dessine la heatmap annulations à partir d'un pivot DataFrame."""
    pivot_display = pivot.fillna(0)

    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        pivot_display,
        annot=True,
        fmt='.1f',
        cmap='YlOrRd',
        linewidths=0.5,
        cbar_kws={'label': 'Taux d\'annulation (%)'},
        ax=ax,
    )

    ax.set_title(title)
    ax.set_xlabel('Mois')
    ax.set_ylabel('Année')
    ax.set_xticklabels([f'M{m}' for m in pivot_display.columns])

    for i in range(len(pivot_display)):
        for j in range(len(pivot_display.columns)):
            if np.isnan(pivot.iloc[i, j]):
                ax.text(j + 0.5, i + 0.5, '-', ha='center', va='center',
                        fontsize=8, color='gray')

    fig.tight_layout()
    return fig


def plot_heatmap_annulations(df, gare_depart, gare_arrive,
                             col_annules="Nombre de trains annulés",
                             col_prevues="Nombre de circulations prévues"):
    """Heatmap année × mois - taux d'annulation pour un trajet donné."""
    d = filter_route(df, gare_depart, gare_arrive)

    # Taux d'annulation par année/mois
    agg = d.groupby(['annee', 'mois']).agg({
        col_annules: 'sum',
        col_prevues: 'sum',
    }).reset_index()
    agg['taux'] = agg[col_annules] / agg[col_prevues] * 100

    pivot = agg.pivot_table(index='annee', columns='mois', values='taux', aggfunc='mean')
    return plot_heatmap_cancelations(pivot, f'{gare_depart} -> {gare_arrive} - Taux d\'annulation')


def plot_heatmap_annulations_global(df,
                                    col_annules="Nombre de trains annulés",
                                    col_prevues="Nombre de circulations prévues"):
    """Heatmap année × mois - taux d'annulation sur tous les trajets."""
    agg = df.groupby(['annee', 'mois']).agg({
        col_annules: 'sum',
        col_prevues: 'sum',
    }).reset_index()
    agg['taux'] = agg[col_annules] / agg[col_prevues] * 100

    pivot = agg.pivot_table(index='annee', columns='mois', values='taux', aggfunc='mean')
    return plot_heatmap_cancelations(pivot, 'Taux d\'annulation par mois (tous trajets)')

def plot_heatmap(pivot, title, figsize=(12, 6)):
    """Dessine la heatmap à partir d'un pivot DataFrame."""
    pivot_display = pivot.fillna(0)

    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        pivot_display,
        annot=True,
        fmt='.1f',
        cmap='YlOrRd',
        linewidths=0.5,
        cbar_kws={'label': 'Retard moyen (min)'},
        ax=ax,
    )

    ax.set_title(title)
    ax.set_xlabel('Mois')
    ax.set_ylabel('Année')
    ax.set_xticklabels([f'M{m}' for m in pivot_display.columns])

    for i in range(len(pivot_display)):
        for j in range(len(pivot_display.columns)):
            if np.isnan(pivot.iloc[i, j]):
                ax.text(j + 0.5, i + 0.5, '–', ha='center', va='center',
                        fontsize=8, color='gray')

    fig.tight_layout()
    return fig


def plot_heatmap_delay(df, gare_depart, gare_arrive,
                       col_retard="Retard moyen de tous les trains à l'arrivée"):
    """Heatmap année × mois pour un trajet donné."""
    d = filter_route(df, gare_depart, gare_arrive)
    pivot = d.pivot_table(index='annee', columns='mois', values=col_retard, aggfunc='mean')
    return plot_heatmap(pivot, f'{gare_depart} -> {gare_arrive} - Retard moyen par mois')


def plot_heatmap_global(df,
                        col_retard="Retard moyen de tous les trains à l'arrivée"):
    """Heatmap année × mois, valeurs = retard moyen sur tous les trajets."""
    pivot = df.pivot_table(index='annee', columns='mois', values=col_retard, aggfunc='mean')
    return plot_heatmap(pivot, 'Retard moyen par mois (tous trajets)')   