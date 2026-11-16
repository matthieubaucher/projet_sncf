import numpy as np

def simulation_scenario_utilisateur(parameters, axe, cible):
    dummy_array = np.array([np.random.rand() for _ in range(0,50)])
    return dummy_array


def get_cibles():
    """
        cibles autorisées pour la simulation
    """
    return ["Retard moyen de tous les trains à l'arrivée", "Nombre trains en retard > 30min", "Nombre de trains annulés"]

def get_parameters():
    """
        parametres autorisées à la saisie utilisateur pour la simulation
    """
    return["Temps", "Nombre de circulations prévues", "Prct retard pour causes externes", "Prct retard pour cause infrastructure", 
           "Prct retard pour cause gestion trafic", "Prct retard pour cause matériel roulant", 
           "Prct retard pour cause gestion en gare et réutilisation de matériel", 
           "Prct retard pour cause prise en compte voyageurs (affluence, gestions PSH, correspondances)"]
