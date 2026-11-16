from sklearn.neural_network import MLPRegressor
from sklearn.linear_model import Lasso
from sklearn.ensemble import RandomForestRegressor

class ModelePrevisionRetard:

    def __init__(self, depart, arrivee, colonnes_X, colonne_Y):
        self.depart = depart
        self.arrivee = arrivee
        self.colonnes_X = colonnes_X
        self.colonne_Y = colonne_Y
        # self.model = MLPRegressor(
        #     hidden_layer_sizes=(32,32),
        #     activation='tanh',
        #     solver='adam',
        #     alpha=1,
        #     max_iter=10000,
        #     random_state=42
        # )
        # self.model = Lasso(max_iter=5000, alpha=0.1)
        self.model = RandomForestRegressor(
            n_estimators=200,
            random_state=42,
            n_jobs=-1
        )


    def train(self, df):
        X_train = df[self.colonnes_X]
        y_train = df[self.colonne_Y]
        self.model.fit(X_train, y_train)

    def predict(self, X):
        return self.model.predict(X[self.colonnes_X])
