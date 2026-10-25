"""Phân rã dự đoán Random Forest theo đường đi trong cây, không phải SHAP."""

import numpy as np
import pandas as pd


def tree_contributions(estimator, features):
    if len(features) != 1:
        raise ValueError("Giải thích cần đúng một mẫu.")
    values = features.to_numpy(dtype=np.float32)[0]
    contributions = np.zeros(len(values))
    baseline = 0.0
    for tree in estimator.estimators_:
        structure = tree.tree_
        node = 0
        baseline += float(structure.value[node].ravel()[0])
        while structure.children_left[node] != structure.children_right[node]:
            feature = structure.feature[node]
            child = (
                structure.children_left[node]
                if values[feature] <= structure.threshold[node]
                else structure.children_right[node]
            )
            contributions[feature] += float(
                structure.value[child].ravel()[0] - structure.value[node].ravel()[0]
            )
            node = child
    count = len(estimator.estimators_)
    return baseline / count, pd.DataFrame(
        {
            "feature": features.columns,
            "contribution": contributions / count,
        }
    )


def prediction_contributions(estimator, features):
    library = type(estimator).__module__.split(".")[0]
    if library == "catboost":
        from catboost import Pool
        values = np.asarray(estimator.get_feature_importance(Pool(features), type="ShapValues", thread_count=2))[0]
        return float(values[-1]), pd.DataFrame({"feature":features.columns,"contribution":values[:-1]}), "Đóng góp SHAP gốc từ CatBoost."
    if library == "xgboost":
        from xgboost import DMatrix
        values = np.asarray(estimator.get_booster().predict(DMatrix(features), pred_contribs=True))[0]
        return float(values[-1]), pd.DataFrame({"feature":features.columns,"contribution":values[:-1]}), "Đóng góp TreeSHAP gốc từ XGBoost."
    if hasattr(estimator, "baseline_") and hasattr(estimator, "correction_"):
        baseline, effects = tree_contributions(estimator.correction_, features)
        scaler = estimator.baseline_.steps[0][1]
        ridge = estimator.baseline_.steps[-1][1]
        baseline += float(ridge.intercept_)
        effects["contribution"] += ridge.coef_ * scaler.transform(features)[0]
        method = "Hệ số Ridge trên đặc trưng chuẩn hóa và đường đi cây phần dư."
    else:
        baseline, effects = tree_contributions(estimator, features)
        method = "Đường đi trong cây Random Forest."

    return baseline, effects, method


def render_explanation(artifact, features):
    import streamlit as st
    from labels import COLUMNS

    baseline, effects, method = prediction_contributions(artifact["model"], features)
    effects["Đặc trưng"] = effects.feature.map(lambda name: COLUMNS.get(name, name))
    effects["Đóng góp (điểm % SOH)"] = effects.contribution
    effects = effects.sort_values("contribution")
    with st.expander("Đóng góp của đặc trưng", expanded=False):
        st.caption(f"SOH dự đoán = {baseline:.3f}% + tổng đóng góp.")
        st.bar_chart(
            effects.set_index("Đặc trưng")[["Đóng góp (điểm % SOH)"]],
            horizontal=True,
            color="#087f70",
            height=390,
        )
        st.caption(
            method
            + " Đóng góp dương: tăng SOH; âm: giảm SOH so với mốc. "
            + ("Không phải quan hệ nhân quả." if "SHAP" in method else "Không phải SHAP hoặc quan hệ nhân quả.")
        )
