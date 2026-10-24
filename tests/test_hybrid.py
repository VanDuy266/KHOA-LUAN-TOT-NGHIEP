import sys
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
import pytest
from sklearn.exceptions import NotFittedError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.hybrid import RidgeResidualForest
from battery_soh.features import FEATURES


def test_prediction_is_sum_of_fitted_components():
    x = pd.DataFrame({"x": np.linspace(0, 1, 60)})
    y = 10 + 2 * x.x + np.sin(x.x * 8)
    model = RidgeResidualForest(n_estimators=5).fit(x, y)
    assert np.allclose(
        model.predict(x), model.baseline_.predict(x) + model.correction_.predict(x)
    )
    with pytest.raises(NotFittedError):
        RidgeResidualForest().predict(x)


def test_hybrid_uses_same_test_pins_and_covers_all_samples():
    pred = pd.read_csv(ROOT / "reports/hybrid_predictions.csv")
    split = pd.read_csv(ROOT / "reports/split_assignments.csv")
    joined = pred.merge(split, on="battery", validate="many_to_one")
    assert (
        len(pred) == 20823 and not pred.duplicated(["battery", "phase", "cycle"]).any()
    )
    assert joined.fold.eq(joined.test_fold).all()
    from sklearn.metrics import mean_absolute_error

    scores = pd.read_csv(ROOT / "reports/hybrid_by_battery.csv")
    for row in scores.itertuples():
        p = pred[pred.battery == row.held_out_battery]
        assert row.mae == pytest.approx(
            mean_absolute_error(p.actual_soh, p.predicted_soh)
        )


def test_saved_hybrid_is_usable():
    artifact = joblib.load(ROOT / "artifacts/ridge_residual_forest.joblib")
    data = pd.read_csv(ROOT / "reports/features.csv").head()
    assert artifact["dataset"] == "SDU" and artifact["features"] == FEATURES
    assert np.isfinite(artifact["model"].predict(data[FEATURES])).all()
