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
    return baseline / count, pd.DataFrame({
        "feature": features.columns,
        "contribution": contributions / count,
    })


def render_explanation(artifact, features):
    import streamlit as st
    from labels import COLUMNS

    baseline, effects = tree_contributions(artifact["model"], features)
    effects["Đặc trưng"] = effects.feature.map(lambda name: COLUMNS.get(name, name))
    effects["Đóng góp (điểm % SOH)"] = effects.contribution
    effects = effects.sort_values("contribution")
    with st.expander("Đóng góp của đặc trưng", expanded=False):
        st.caption(
            f"SOH dự đoán = {baseline:.3f}% + tổng đóng góp."
        )
        st.bar_chart(
            effects.set_index("Đặc trưng")[["Đóng góp (điểm % SOH)"]],
            horizontal=True, color="#087f70", height=390,
        )
        st.caption(
            "Phương pháp: đường đi trong cây. Đóng góp dương: tăng SOH; âm: giảm SOH so với mốc."
        )
