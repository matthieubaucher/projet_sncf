from projet_sncf.business.service.Prevision_de_retard import (
    clusterise,
    simulation,
)
from projet_sncf.database import dataloader as dl


def simulation_scenario_utilisateur(parameters: dict, axe: str, cible: str):
    if cible not in get_cibles():
        raise ValueError("Cible non disponible pour la simulation")

    if axe not in get_axes():
        raise ValueError("Axe non disponible pour la simulation")

    if parameters.get("Nombre de circulations prévues", 0) <= 0:
        raise ValueError("Nombre de circulations prévues doit être au moins 1")

    # traduction en temps suivant l'origine définie dans la base
    temps = parameters["Temps"]
    parameters["Temps"] = dl.get_temps(temps // 12, temps % 12 + 1)

    return simulation(parameters, axe, cible)


def clusterise_ligne_et_axe(axes: list, cible: str):
    if cible not in get_cibles():
        raise ValueError("Cible non disponible pour la simulation")

    if len(axes) < 4:
        raise ValueError("Choisissez au moins 4 axes")

<<<<<<< HEAD
    if len(axes)>7:
        raise ValueError("Choisissez maximum 7 axes") # limites streamlit : on aurait aimé pouvoir montrer plus
    
=======
>>>>>>> 617ea09 (test(CI): refactor du fichier Retard_prevision_API.py pour PEP8)
    for axe in axes:
        if axe not in get_axes():
            raise ValueError(f"Axe {axe} non disponible pour la simulation")

    return clusterise(axes, cible)


def get_axes():
    """
    axes disponibles pour la simulation
    """
    return dl.get_axes()


def get_cibles():
    """
    cibles autorisées pour la simulation
    """
<<<<<<< HEAD
    return get_cibles_disponibles()
=======
    return [
        "Retard moyen de tous les trains à l'arrivée",
        "Nombre trains en retard > 30min",
        "Nombre de trains annulés",
    ]

>>>>>>> 617ea09 (test(CI): refactor du fichier Retard_prevision_API.py pour PEP8)

def get_parameters():
    """
    parametres autorisées à la saisie utilisateur pour la simulation
    """
<<<<<<< HEAD
    return get_parameters_disponibles()

=======
    return [
        "Temps",
        "Nombre de circulations prévues",
        "Prct retard pour causes externes",
        "Prct retard pour cause infrastructure",
        "Prct retard pour cause gestion trafic",
        "Prct retard pour cause matériel roulant",
        "Prct retard pour cause gestion en gare et réutilisation de matériel",
        (
            "Prct retard pour cause prise en compte voyageurs "
            "(affluence, gestions PSH, correspondances)"
        ),
    ]
>>>>>>> 617ea09 (test(CI): refactor du fichier Retard_prevision_API.py pour PEP8)
