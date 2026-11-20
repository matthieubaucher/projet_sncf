from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV
import logging
import time

logger = logging.getLogger(__name__)

class ModelePrevisionRetard:

    def __init__(self, depart:str, arrivee:str, colonnes_X:list, colonne_Y:str):
        self.depart = depart
        self.arrivee = arrivee
        self.colonnes_X = colonnes_X
        self.colonne_Y = colonne_Y
        self.model = None
        logger.info(f"Modèle créé : {depart} {arrivee} {colonne_Y} parametres : {' + '.join(colonnes_X)}");
 

    def train(self, df):
        logger.info(f"Entrainement du modèle {self.depart} <-> {self.arrivee} sur cible {self.colonne_Y} : début")
        if len(df) < 20:
            logger.warning(f"Peu de données d'entrainement : {len(df)} lignes")
        # Le nettoyage garde les valeurs impossibles en NaN : on écarte les lignes
        # où les variables ou la cible de ce modèle sont vides.
        df = df.dropna(subset=self.colonnes_X + [self.colonne_Y])
        X_train = df[self.colonnes_X]
        y_train = df[self.colonne_Y]

        param_grid = {
            "max_depth": [3, 4],
            "n_estimators": [100, 150],
            "min_samples_leaf": [2, 3],
            "max_features": [2, 3],
        }
        
        debut_elapse = time.perf_counter()

        grid_search = GridSearchCV(
            estimator=RandomForestRegressor(
                random_state=42,
                n_jobs=-1
            ),
            param_grid=param_grid,
            cv=5,
            scoring="r2",
            n_jobs=-1
        )

        grid_search.fit(X_train, y_train)

        elapsed = time.perf_counter() - debut_elapse

        self.model = grid_search.best_estimator_

        logger.info(f"Entrainement du modèle {self.depart} <-> {self.arrivee} sur cible {self.colonne_Y} : fin avec R2={grid_search.best_score_:.2f} en {elapsed:.2f} secondes")
        if grid_search.best_score_<0:
            logger.warning("ce modèle fait pire que la moyenne")
        elif grid_search.best_score_<0.2:
            logger.warning("ce modèle est pas terrible")


    def predict(self, X):
        logger.info(f"Une prédiction effectuée sur le modèle {self.depart} <-> {self.arrivee} sur cible {self.colonne_Y}")
        return self.model.predict(X[self.colonnes_X])



# Note : ces modèles ont été testé et ont des résultats décevant car on a très peu de données pour l'entrainement :
#
# self.model = MLPRegressor(
#     hidden_layer_sizes=(32,32),
#     activation='tanh',
#     solver='adam',
#     alpha=1,
#     max_iter=10000,
#     random_state=42
# )
#
# self.model = Lasso(max_iter=5000, alpha=0.1)
