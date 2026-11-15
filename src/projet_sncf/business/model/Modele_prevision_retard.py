import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score

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

        best_score = -999

        for max_depth in [3,4]: 
          for n_estimators in [100,150]: 
            for min_samples_leaf in [2,3]:
              for max_features in [2,3]:    
                model = RandomForestRegressor(
                    min_samples_leaf=min_samples_leaf,
                    n_estimators = n_estimators,
                    max_depth = max_depth,
                    max_features=max_features,
                    random_state=42,
                    n_jobs=-1
                )
                scores = cross_val_score(model, X_train, y_train, cv=5, scoring="r2", n_jobs=-1)
                score = np.mean(scores)
                if score > best_score:
                    best_score = score
                    self.model = model        

        self.model.fit(X_train, y_train)


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