"""Biểu đồ tương tác bằng Altair, có tên trục và chú giải tiếng Việt."""
import altair as alt
from labels import MODEL_NAMES

PALETTE = ["#087f70", "#eb8c5e", "#6576a8", "#c7a44a"]


def finish(chart, height=300):
    return chart.properties(height=height, padding={"left": 15, "right": 15, "top": 10, "bottom": 10},
        autosize=alt.AutoSizeParams(type="fit", contains="padding")).configure_view(stroke=None).configure_axis(
        labelColor="#6a7b75", titleColor="#4c6159", gridColor="#e9eeea", domain=False,
        labelFont="Arial", titleFont="Arial",
        labelFontSize=11, titleFontSize=12, titlePadding=12).configure_legend(
        title=None, labelColor="#52665d", orient="bottom", symbolType="circle")


def soh_trend(data):
    chart = alt.Chart(data).mark_line(strokeWidth=2.6).encode(
        x=alt.X("cycle:Q", title="Chu kỳ xả"),
        y=alt.Y("soh_pct:Q", title="Sức khỏe pin · SOH (%)", scale=alt.Scale(zero=False)),
        color=alt.Color("battery:N", scale=alt.Scale(range=PALETTE)),
        tooltip=[alt.Tooltip("battery:N", title="Pin"), alt.Tooltip("cycle:Q", title="Chu kỳ"),
                 alt.Tooltip("soh_pct:Q", title="SOH (%)", format=".2f")])
    return finish(chart)


def signal(data, column, title, color="#087f70"):
    chart = alt.Chart(data).mark_line(color=color, strokeWidth=2.3).encode(
        x=alt.X("time:Q", title="Thời gian (giây)"),
        y=alt.Y(f"{column}:Q", title=title, scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("time:Q", title="Giây", format=".2f"),
                 alt.Tooltip(f"{column}:Q", title=title, format=".3f")])
    return finish(chart, 240)


def model_comparison(data, metric):
    data = data.copy()
    data["model_name"] = data.model.map(MODEL_NAMES)
    unit = "R²" if metric == "r2" else f"{metric.upper()} · điểm phần trăm SOH"
    chart = alt.Chart(data).mark_bar(cornerRadiusEnd=5, size=25).encode(
        x=alt.X(f"{metric}:Q", title=unit),
        y=alt.Y("model_name:N", sort=alt.EncodingSortField(field=metric, order="descending" if metric == "r2" else "ascending"), title=None),
        color=alt.condition(alt.datum.model == "Random Forest", alt.value("#eb8c5e"), alt.value("#087f70")),
        tooltip=[alt.Tooltip("model_name:N", title="Mô hình"), alt.Tooltip(f"{metric}:Q", title=unit, format=".3f")])
    return finish(chart, 260)


def held_out(data):
    melted = data.melt(id_vars=["cycle"], value_vars=["actual_soh", "predicted_soh"], var_name="series", value_name="soh")
    melted["series"] = melted.series.replace({"actual_soh": "SOH thực tế", "predicted_soh": "SOH dự đoán"})
    chart = alt.Chart(melted).mark_line(strokeWidth=2.6).encode(
        x=alt.X("cycle:Q", title="Chu kỳ xả"),
        y=alt.Y("soh:Q", title="SOH (%)", scale=alt.Scale(zero=False)),
        color=alt.Color("series:N", scale=alt.Scale(domain=["SOH thực tế", "SOH dự đoán"], range=["#087f70", "#eb8c5e"])),
        strokeDash=alt.StrokeDash("series:N", legend=None),
        tooltip=[alt.Tooltip("cycle:Q", title="Chu kỳ"), alt.Tooltip("series:N", title="Đường"),
                 alt.Tooltip("soh:Q", title="SOH (%)", format=".2f")])
    return finish(chart, 330)


def residuals(data):
    data = data.copy()
    data["error"] = data.predicted_soh - data.actual_soh
    dots = alt.Chart(data).mark_circle(size=34, opacity=.7).encode(
        x=alt.X("cycle:Q", title="Chu kỳ xả"), y=alt.Y("error:Q", title="Dự đoán − thực tế (điểm % SOH)"),
        color=alt.Color("battery:N", scale=alt.Scale(range=PALETTE)),
        tooltip=[alt.Tooltip("battery:N", title="Pin"), alt.Tooltip("cycle:Q", title="Chu kỳ"), alt.Tooltip("error:Q", title="Sai số", format=".3f")])
    return finish(dots, 260)


def compare_signal(data, column, title):
    chart = alt.Chart(data).mark_line(strokeWidth=2.4).encode(
        x=alt.X("time:Q", title="Thời gian (giây)"),
        y=alt.Y(f"{column}:Q", title=title, scale=alt.Scale(zero=False)),
        color=alt.Color("comparison:N", title=None, scale=alt.Scale(range=["#087f70", "#eb8c5e"])),
        tooltip=[alt.Tooltip("comparison:N", title="Chu kỳ"), alt.Tooltip("time:Q", title="Giây", format=".2f"),
                 alt.Tooltip(f"{column}:Q", title=title, format=".3f")])
    return finish(chart, 260)
