import pandas as pd

from sklearn.linear_model import Lasso, Ridge
from sklearn.naive_bayes import GaussianNB

import pickle

data = pd.read_csv(
    "./resources/Diabetes_Classification( from DATA world).csv")

cs = {"female": 0, "male": 1}
data["Gender"] = data["Gender"].map(cs)

diab = {"No diabetes": 0, "Diabetes": 1}
data["Diabetes"] = data["Diabetes"].map(diab)

x = data[["Age", "Gender", "Height", "Weight", "Systolic BP", "Diastolic BP"]]


def trainGlucoseModal(data, x):
    ''' Glucose prediction modal'''
    y = data["Glucose"]
    ridge = Ridge(alpha=0.001)
    ridge.fit(x, y)
    return ridge


def trainDiabetiesModal(data, x):
    ''' Diabeties prediction modal'''
    y = data["Diabetes"]
    GaussianModel = GaussianNB()
    GaussianModel.fit(x, y)
    return GaussianModel


def trainColestrolModal(data, x):
    ''' Colestrol prediction model'''
    y = data["Cholesterol"]
    lasso = Lasso(alpha=0.1)
    lasso.fit(x, y)
    return lasso


pickle.dump(trainGlucoseModal(data, x), open('glucoseModel.pkl', 'wb'))
pickle.dump(trainDiabetiesModal(data, x), open('DiabetiesModel.pkl', 'wb'))
pickle.dump(trainColestrolModal(data, x), open('colestrolModel.pkl', 'wb'))
