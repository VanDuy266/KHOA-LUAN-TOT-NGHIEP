import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.anomaly import trend_features, COLUMNS


def series():
    return pd.DataFrame(
        dict(
            battery=["test"] * 30,
            phase=["primary"] * 30,
            cycle=np.arange(1, 31),
            soh_pct=100 - 0.1 * np.arange(30),
        )
    )


def test_steady_decline_has_no_rule_flags():
    result = trend_features(series())
    assert not result.rule_flag.any()
    assert result.eligible.sum() == len(result)-6
    assert result.loc[6, "eligible"]


def test_abrupt_drop_is_flagged_without_future_access():
    data = series()
    data.loc[15:, "soh_pct"] -= 3
    result = trend_features(data)
    assert result.loc[15, "rule_flag"]
    data.loc[16:, "soh_pct"] = 55
    changed = trend_features(data)
    pd.testing.assert_frame_equal(result.loc[:15], changed.loc[:15])


def test_history_does_not_cross_phase_or_battery():
    a = series()
    b = series().assign(phase="second_life", soh_pct=60)
    c = series().assign(battery="another", soh_pct=50)
    result = trend_features(pd.concat([a, b, c], ignore_index=True))
    assert not result.groupby(["battery", "phase"]).head(6).eligible.any()
    assert not result.rule_flag.any()


def test_cycle_gap_is_used_in_rate():
    data = series()
    data.cycle = data.cycle * 5
    result = trend_features(data)
    assert np.allclose(result.rate_per100.dropna(), -2)


def test_duplicate_keys_rejected():
    data = series()
    with pytest.raises(ValueError, match="Trùng"):
        trend_features(pd.concat([data, data.iloc[:1]]))


def test_monitoring_predictions_use_declared_battery_folds():
    data = pd.read_csv(ROOT / "reports/anomaly_predictions.csv")
    split = pd.read_csv(ROOT / "reports/split_assignments.csv")
    joined = data.merge(split, on="battery", validate="many_to_one")
    assert joined.fold.eq(joined.test_fold).all()
    assert len(joined) == 20823
    assert (
        joined.loc[joined.eligible, ["iforest_score", "iforest_threshold"]]
        .notna()
        .all()
        .all()
    )
    assert joined.loc[~joined.eligible, "flag"].eq(False).all()
