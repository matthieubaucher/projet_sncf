
from projet_sncf.business.model.Modele_prevision_retard import ModelePrevisionRetard
from projet_sncf.database.dataloader import get_dataframe
import logging

logger = logging.getLogger(__name__)

class ModelManager:

    def __init__(self):
        self.dataframe = get_dataframe()
        self.modeles = {} # stockage des modèles entrainés
        logger.info("ModelManager créé");

    def get_id_axe(self, colonnes_X, axe, cible:str):
        id_axe = "<->".join(sorted(axe))
        id_col = "/".join(sorted(colonnes_X))
        return id_axe + "__" + cible + "__" + id_col

    def get_trained_modele(self, X, axe, cible:str):
        id_modele = self.get_id_axe(X.columns.tolist(), axe, cible)
        modele = self.modeles.get(id_modele)
        if modele is None:
            modele = ModelePrevisionRetard(axe[0], axe[1], X.columns.tolist(), cible)
            self.modeles[id_modele] = modele
            modele.train(self.dataframe)
        return modele

    def get_inferance(self, X, axe, cible):
        """
            Applique les scenarios en utilisant prédict sur le modèle
            Mémofonction pour retrouver le modèle suivant l'axe (ligne dans les deux sens); l'entraine sinon
            La cible est le y à reproduire
        """
        modele = self.get_trained_modele(X, axe, cible)
        return  modele.predict(X)



modele_manager = ModelManager() # singleton
def get_modele_manager():
    return modele_manager