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

