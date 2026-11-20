from projet_sncf.business.service.Prevision_de_retard import (
    clusterise,
    get_cibles_disponibles,
    get_parameters_disponibles,
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

    if len(axes) > 7:
        raise ValueError("Choisissez maximum 7 axes")

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
    return get_cibles_disponibles()


def get_parameters():
    """
    parametres autorisées à la saisie utilisateur pour la simulation
    """
    return get_parameters_disponibles()
