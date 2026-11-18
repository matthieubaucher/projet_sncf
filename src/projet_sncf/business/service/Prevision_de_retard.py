
from projet_sncf.database.dataloader import get_dataframe
from projet_sncf.business.model.Modele_prevision_retard_manager import get_inferance
import pandas as pd
import numpy as np
from sklearn.manifold import TSNE


def simulation(parameters, axe, cible):
    """
        Fait 1000 modifications des entrées utilisateur pour avoir les 1000 vecteurs de paramètre
        Utilisation du previsionneur (avec ces data, et les vecteurs de paramètre) : méthode get_inferance_retard
        on renvoie un vecteur [1000] affichable dans une boxplot
    """
    perturbe = lambda x: np.random.normal(loc=x, scale=0.05 * abs(x)) # TODO : normalisation des prct de causes a faire
    values = []
    for _ in range(1000):
        values.append([perturbe(parameter) for parameter in parameters])
    X = pd.DataFrame(values, columns=parameters.index)
    Y = get_inferance(X, axe, cible)
    return Y


def clusterise(axes, cible):    
    """
        Va chercher le dataframe de Data  
        créé 1000 scénari possibles en base via shuffle
        Utilisation du previsionneur (avec ces data, et les vecteurs de parametre) : méthode get_inferance_retard
        utiliser l'algo TSNE
        on renvoie la matrice [len(axes), 2] affichable coté streamlit
    """
    perplexity = min(len(axes)//2,5)
    if perplexity<=1:
        raise ValueError("Trop peu d'axes pour effectuer la projection t-SNE.")
    df = get_dataframe()
    X = df.sample(n=1000)
    Y = []
    for axe in axes:
        y = get_inferance(X, axe, cible)
        Y += [y]
    Y = np.array(Y)        
    tsne = TSNE(
        n_components=2,
        perplexity=perplexity,
        random_state=42
    )
    Y_2d = tsne.fit_transform(Y)
    return Y_2d