
from projet_sncf.database.dataloader import get_dataframe
from projet_sncf.business.model.Modele_prevision_retard_manager import get_modele_manager
import pandas as pd
import numpy as np
from sklearn.manifold import TSNE
import logging

logger = logging.getLogger(__name__)

def simulation(parameters:dict, axe:list, cible:str):
    """
        Fait 1000 modifications des entrées utilisateur pour avoir les 1000 vecteurs de paramètre
        Utilisation du previsionneur (avec ces data, et les vecteurs de paramètre) : méthode get_inferance_retard
        on renvoie un vecteur [1000] affichable dans une boxplot
    """
    logger.info(f"L'utilisateur demande une prévision de retard sur  : {'<->'.join(axe)} {cible}");
    perturbe = lambda x: np.random.normal(loc=x, scale=0.05 * abs(x)) # TODO : normalisation des prct de causes a faire
    values = []
    for _ in range(1000):
        values.append([perturbe(parameter) for parameter in parameters.values()])
    X = pd.DataFrame(values, columns=parameters.keys())
    Y = get_modele_manager().get_inferance(X, axe, cible)
    logger.info(f"Prévision de retard effectuée")
    return Y


def clusterise(axes, cible):    
    """
        Va chercher le dataframe de Data  
        créé 1000 scénari possibles en base via shuffle
        Utilisation du previsionneur (avec ces data, et les vecteurs de parametre) : méthode get_inferance_retard
        utiliser l'algo TSNE
        on renvoie la matrice [len(axes), 2] affichable coté streamlit
    """
    logger.info(f"L'utilisateur demande un clustering sur  : {len(axes)} axes avec cible = {cible}");
    perplexity = min(len(axes)//2,5)
    if perplexity<=1:
        raise ValueError("Trop peu d'axes pour effectuer la projection t-SNE.")
    df = get_dataframe()
    X = df.sample(n=1000)
    Y = []
    X = X[get_parameters_disponibles()]
    for axe in axes:
        y = get_modele_manager().get_inferance(X, axe, cible)
        Y += [y]
    Y = np.array(Y)        
    tsne = TSNE(
        n_components=2,
        perplexity=perplexity,
        random_state=42
    )
    Y_2d = tsne.fit_transform(Y)

    logger.info(f"Clustering effectuée")
    return Y_2d


def get_cibles_disponibles():
    """
        cibles autorisées pour la simulation
    """
    return ["Retard moyen de tous les trains à l'arrivée", "Nombre trains en retard > 30min", "Nombre de trains annulés"]


def get_parameters_disponibles():
    """
        parametres autorisées à la saisie utilisateur pour la simulation
    """
    return["Temps", "Nombre de circulations prévues", "Prct retard pour causes externes", "Prct retard pour cause infrastructure", 
           "Prct retard pour cause gestion trafic", "Prct retard pour cause matériel roulant", 
           "Prct retard pour cause gestion en gare et réutilisation de matériel", 
           "Prct retard pour cause prise en compte voyageurs (affluence, gestions PSH, correspondances)"]
