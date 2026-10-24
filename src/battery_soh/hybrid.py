"""Hồi quy nền Ridge và Random Forest hiệu chỉnh phần dư."""

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.utils.validation import check_is_fitted


class RidgeResidualForest(RegressorMixin, BaseEstimator):
    def __init__(self, alpha=10.0, n_estimators=100, random_state=42, n_jobs=2):
        self.alpha = alpha
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.n_jobs = n_jobs

    def fit(self, X, y):
        self.baseline_ = make_pipeline(StandardScaler(), Ridge(alpha=self.alpha))
        self.baseline_.fit(X, y)
        residual = np.asarray(y) - self.baseline_.predict(X)
        self.correction_ = RandomForestRegressor(
            n_estimators=self.n_estimators,
            min_samples_leaf=5,
            max_depth=16,
            max_samples=0.7,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
        )
        self.correction_.fit(X, residual)
        self.n_features_in_ = X.shape[1]
        return self

    def predict(self, X):
        check_is_fitted(self, ["baseline_", "correction_"])
        return self.baseline_.predict(X) + self.correction_.predict(X)
