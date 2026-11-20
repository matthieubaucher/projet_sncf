import logging
import time

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV

logger = logging.getLogger(__name__)


class ModelePrevisionRetard:
    def __init__(
        self,
        depart: str,
        arrivee: str,
        feature_columns: list[str],
        target_column: str,
    ):
        self.depart = depart
        self.arrivee = arrivee
        self.feature_columns = feature_columns
        self.target_column = target_column
        self.model = None
        logger.info(
            "Modèle créé : %s %s %s paramètres : %s",
            depart,
            arrivee,
            target_column,
            " + ".join(feature_columns),
        )

    def train(self, df):
        logger.info(
            "Entraînement du modèle %s <-> %s sur la cible %s : début",
            self.depart,
            self.arrivee,
            self.target_column,
        )
        if len(df) < 20:
            logger.warning(f"Peu de données d'entrainement : {len(df)} lignes")
        # Le nettoyage conserve les valeurs impossibles comme NaN ; on écarte
        # les lignes où les variables ou la cible de ce modèle sont vides.
        df = df.dropna(subset=self.feature_columns + [self.target_column])
        X_train = df[self.feature_columns]
        y_train = df[self.target_column]

        param_grid = {
            "max_depth": [3, 4],
            "n_estimators": [100, 150],
            "min_samples_leaf": [2, 3],
            "max_features": [2, 3],
        }

        debut_elapse = time.perf_counter()

        grid_search = GridSearchCV(
            estimator=RandomForestRegressor(random_state=42, n_jobs=-1),
            param_grid=param_grid,
            cv=5,
            scoring="r2",
            n_jobs=-1,
        )

        grid_search.fit(X_train, y_train)

        elapsed = time.perf_counter() - debut_elapse

        self.model = grid_search.best_estimator_

        logger.info(
            "Entraînement du modèle %s <-> %s sur la cible %s : "
            "fin avec R2=%.2f en %.2f secondes",
            self.depart,
            self.arrivee,
            self.target_column,
            grid_search.best_score_,
            elapsed,
        )
        if grid_search.best_score_ < 0:
            logger.warning("ce modèle fait pire que la moyenne")
        elif grid_search.best_score_ < 0.2:
            logger.warning("ce modèle est pas terrible")

    def predict(self, X):
        logger.info(
            "Prédiction avec le modèle %s <-> %s sur la cible %s",
            self.depart,
            self.arrivee,
            self.target_column,
        )
        return self.model.predict(X[self.feature_columns])


# Ces modèles ont été testés sans succès, faute de données d'entraînement :
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
