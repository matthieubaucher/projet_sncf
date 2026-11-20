import logging

import numpy as np
import pandas as pd
from sklearn.manifold import TSNE

from projet_sncf.business.model.Modele_prevision_retard_manager import (
    get_modele_manager,
)
from projet_sncf.database.dataloader import get_dataframe

logger = logging.getLogger(__name__)


def simulation(parameters: dict, axe: list, cible: str):
    """Simule mille variations des paramètres saisis par l'utilisateur.

    Les valeurs simulées sont transmises au modèle, puis renvoyées sous la
    forme d'un vecteur de 1000 prédictions pour affichage dans une boîte à
    moustaches.
    """
    logger.info(
        "Prévision de retard demandée sur %s pour la cible %s",
        "<->".join(axe),
        cible,
    )

    def perturbe(value: float) -> float:
        return np.random.normal(loc=value, scale=0.05 * abs(value))

    values = []
    for _ in range(1000):
        values.append(
            [perturbe(parameter) for parameter in parameters.values()]
        )
    X = pd.DataFrame(values, columns=parameters.keys())
    predictions = get_modele_manager().get_inferance(X, axe, cible)
    logger.info("Prévision de retard effectuée")
    return predictions


def clusterise(axes, cible):
    """Projette les profils de perturbation des liaisons en deux dimensions.

    Un échantillon de données est passé au modèle pour chaque axe. Les
    prédictions obtenues sont ensuite projetées avec t-SNE pour affichage.
    """
    logger.info(
        "Projection demandée pour %d axes avec la cible %s",
        len(axes),
        cible,
    )
    perplexity = min(len(axes) // 2, 5)
    if perplexity <= 1:
        raise ValueError("Trop peu d'axes pour effectuer la projection t-SNE.")
    df = get_dataframe()
    X = df.sample(n=1000)
    predictions = []
    for axe in axes:
        y = get_modele_manager().get_inferance(X, axe, cible)
        predictions.append(y)
    predictions = np.array(predictions)
    tsne = TSNE(n_components=2, perplexity=perplexity, random_state=42)
    embeddings = tsne.fit_transform(predictions)
    logger.info("Clustering effectuée")
    return embeddings
