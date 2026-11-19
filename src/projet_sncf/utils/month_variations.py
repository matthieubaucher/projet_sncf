import logging
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def plot_month_lateness(ax, d, mois, gare_depart, gare_arrive,
                col_retard_dep='nb_retard_depart',
                col_retard_arr='nb_retard_arrive'):
    """Filtre par mois et dessine sur l'axe fourni."""
    sub = d[d['mois'] == mois].groupby('annee').agg({
        col_retard_dep: 'sum',
        col_retard_arr: 'sum'
    }).reset_index()

    if sub.empty:
        logger.warning("Aucune donnée pour le mois %d (%s -> %s)",
                       mois, gare_depart, gare_arrive)
        ax.text(0.5, 0.5, 'Pas de données', ha='center', va='center',
                transform=ax.transAxes, fontsize=10, color='gray')
        ax.set_title(f'Mois {mois}')
        ax.set_axis_off()
        return

    ax.plot(sub['annee'], sub[col_retard_dep], marker='o', label='Départ')
    ax.plot(sub['annee'], sub[col_retard_arr], marker='o', label='Arrivée')
    ax.set_title(f'Mois {mois}')
    ax.set_xlabel('Année')
    ax.set_ylabel('Nb retards')
    ax.legend()


def filter_route(df, gare_depart, gare_arrive):
    """Filtre le dataframe par trajet et valide."""
    d = df[(df['gare_depart'] == gare_depart) & (df['gare_arrive'] == gare_arrive)].copy()
    if d.empty:
        logger.error("Aucune donnée pour le trajet %s -> %s", gare_depart, gare_arrive)
        raise ValueError(f"Aucune donnée pour {gare_depart} -> {gare_arrive}")
    return d


def plotMonthlyLateness(df, gare_depart, gare_arrive, mois,
                        col_retard_dep='nb_retard_depart',
                        col_retard_arr='nb_retard_arrive'):
    """Évolution du retard par année pour un trajet et un mois donnés."""
    d = filter_route(df, gare_depart, gare_arrive)
    sub = d[d['mois'] == mois]

    if sub.empty:
        logger.warning("Aucune donnée pour le mois %d (%s -> %s)",
                       mois, gare_depart, gare_arrive)
        raise ValueError(f"Aucune donnée pour le mois {mois} sur ce trajet")

    logger.info("Plot : %s -> %s, mois %d", gare_depart, gare_arrive, mois)

    fig, ax = plt.subplots(figsize=(8, 6))
    plot_month_lateness(ax, d, mois, gare_depart, gare_arrive,
                col_retard_dep, col_retard_arr)
    ax.set_title(f'{gare_depart} -> {gare_arrive} - Mois {mois}')
    plt.tight_layout()
    plt.show()


def plotMonthlyLatenessAll(df, gare_depart, gare_arrive,
                           col_retard_dep='nb_retard_depart',
                           col_retard_arr='nb_retard_arrive'):
    """Évolution du retard par mois pour un trajet donné."""
    """Evolution of the lateness by month for a given route."""
    d = filter_route(df, gare_depart, gare_arrive)

    logger.info("Plot 12 mois : %s -> %s", gare_depart, gare_arrive)

    fig, axes = plt.subplots(4, 3, figsize=(14, 16))
    fig.suptitle(f'{gare_depart} -> {gare_arrive}', fontsize=14)

    for mois in range(1, 13):
        ax = axes[(mois - 1) // 3, (mois - 1) % 3]
        plot_month_lateness(ax, d, mois, gare_depart, gare_arrive,
                    col_retard_dep, col_retard_arr)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()

def plot_month_annulations(ax, d, mois, gare_depart, gare_arrive,
                           col_annules="Nombre de trains annulés",
                           col_prevues="Nombre de circulations prévues"):
    """Filtre par mois et dessine les annulations sur l'axe fourni."""
    """Filter by month and plot the cancellations on the provided axis."""
    sub = d[d['mois'] == mois].groupby('annee').agg({
        col_annules: 'sum',
        col_prevues: 'sum',
    }).reset_index()

    if sub.empty:
        logger.warning("Aucune donnée pour le mois %d (%s -> %s)",
                       mois, gare_depart, gare_arrive)
        ax.text(0.5, 0.5, 'Pas de données', ha='center', va='center',
                transform=ax.transAxes, fontsize=10, color='gray')
        ax.set_title(f'Mois {mois}')
        ax.set_axis_off()
        return

    sub['taux_annulation'] = (sub[col_annules] / sub[col_prevues] * 100).round(2)

    ax.plot(sub['annee'], sub[col_annules], marker='o', label='Nb annulés')
    ax.plot(sub['annee'], sub['taux_annulation'], marker='s', label='Taux (%)', linestyle='--')
    ax.set_title(f'Mois {mois}')
    ax.set_xlabel('Année')
    ax.set_ylabel('Annulations')
    ax.legend()


def plotMonthAnnulations(df, gare_depart, gare_arrive, mois,
                         col_annules="Nombre de trains annulés",
                         col_prevues="Nombre de circulations prévues"):
    """Évolution des annulations par année pour un trajet et un mois donnés."""
    """Evolution of the cancellations by year for a given route and month."""
    d = filter_route(df, gare_depart, gare_arrive)
    sub = d[d['mois'] == mois]

    if sub.empty:
        logger.warning("Aucune donnée pour le mois %d (%s -> %s)",
                       mois, gare_depart, gare_arrive)
        raise ValueError(f"Aucune donnée pour le mois {mois} sur ce trajet")

    logger.info("Plot annulations : %s -> %s, mois %d", gare_depart, gare_arrive, mois)

    fig, ax = plt.subplots(figsize=(8, 6))
    plot_month_annulations(ax, d, mois, gare_depart, gare_arrive,
                           col_annules, col_prevues)
    ax.set_title(f'{gare_depart} -> {gare_arrive} - Mois {mois} - Annulations')
    plt.tight_layout()
    plt.show()


def plotMonthAnnulationsAll(df, gare_depart, gare_arrive,
                            col_annules="Nombre de trains annulés",
                            col_prevues="Nombre de circulations prévues"):
    """Évolution des annulations par mois (12 sous-graphiques) pour un trajet donné."""
    """Evolution of the cancellations by month (12 subplots) for a given route."""
    d = filter_route(df, gare_depart, gare_arrive)

    logger.info("Plot 12 mois annulations : %s -> %s", gare_depart, gare_arrive)

    fig, axes = plt.subplots(4, 3, figsize=(14, 16))
    fig.suptitle(f'{gare_depart} -> {gare_arrive}  Annulations', fontsize=14)

    for mois in range(1, 13):
        ax = axes[(mois - 1) // 3, (mois - 1) % 3]
        plot_month_annulations(ax, d, mois, gare_depart, gare_arrive,
                               col_annules, col_prevues)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()