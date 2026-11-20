import numpy as np
from projet_sncf.database import dataloader as dl
from projet_sncf.business.service.Prevision_de_retard import simulation

def simulation_scenario_utilisateur(parameters:dict, axe:str, cible:str):
    if cible not in get_cibles():
        raise ValueError("Cible non disponible pour la simulation")

    print(axe, "  ", get_axes())
    if axe not in get_axes():
        raise ValueError("Axe non disponible pour la simulation")

    # traduction en temps suivant l'origine définie dans la base    
    temps = parameters["Temps"]
    parameters["Temps"] = dl.get_temps(temps//12, temps%12+1)
    
    return simulation(parameters, axe, cible)

def clusterise_ligne_et_axe(axes, cible):
    dummy_array= np.array([
        [ 0.12,  1.45], [-0.87,  0.32],
        [ 1.91, -0.54], [ 0.75,  2.18],
        [-1.43, -0.92], [ 2.34,  0.17],
        [-0.21,  1.03], [ 1.12, -1.76],
        [-2.01,  0.84], [ 0.48, -0.37],
    ])
    return dummy_array

def get_axes():
    """
        axes disponibles pour la simulation
    """
    return dl.get_axes()

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

