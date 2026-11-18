from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV

class ModelePrevisionRetard:

    def __init__(self, depart, arrivee, colonnes_X, colonne_Y):
        self.depart = depart
        self.arrivee = arrivee
        self.colonnes_X = colonnes_X
        self.colonne_Y = colonne_Y
        self.model = None
 

    def train(self, df):
        X_train = df[self.colonnes_X]
        y_train = df[self.colonne_Y]

        param_grid = {
            "max_depth": [3, 4],
            "n_estimators": [100, 150],
            "min_samples_leaf": [2, 3],
            "max_features": [2, 3],
        }

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

        self.model = grid_search.best_estimator_


    def predict(self, X):
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