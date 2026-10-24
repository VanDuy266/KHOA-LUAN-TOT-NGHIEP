"""Dự đoán một chu kỳ hoặc theo lô, lưu kết quả trong phiên."""

import hashlib
import pandas as pd
import streamlit as st
from app_data import table, model
from components import heading, section, csv_download
from labels import COLUMNS, vietnamese_table
from charts import signal
from prediction import predict, predict_batch, read_csv
from result_report import add_history, current_time, html_report


def render():
    heading("", "Dự đoán tình trạng sức khỏe pin", "")
    selected_model = st.selectbox(
        "Mô hình SOH", ["Random Forest", "Ridge–RF phần dư"], key="soh_model"
    )
    mode = st.radio(
        "Chế độ dự đoán",
        ["Một chu kỳ", "Theo lô"],
        horizontal=True,
        key="forecast_mode",
    )
    measurements = table("data/clean/sample_measurements.csv")
    sample = measurements[
        (measurements.battery == "SDU_01") & (measurements.time <= 120)
    ]
    sample = sample[sample.phase_code == 0]
    sample = sample[
        sample.cycle.isin(
            sorted(sample.cycle.unique())[: (1 if mode == "Một chu kỳ" else 3)]
        )
    ]
    sample = sample[
        [
            "battery",
            "cycle",
            "time",
            "terminal_voltage",
            "terminal_current",
            "temperature",
            "phase_code",
        ]
    ]
    with st.container(border=True):
        left, right = st.columns([1.4, 1], gap="large")
        with left:
            uploaded = st.file_uploader(
                "File CSV hoặc CSV.GZ · tối đa 512 MiB", type=["csv", "gz"]
            )
            phase_code = st.selectbox(
                "Giai đoạn của dữ liệu",
                [0, 1],
                format_func=lambda x: "Sử dụng ban đầu" if x == 0 else "Tái sử dụng",
                key="upload_phase",
            )
            use_example = st.checkbox("Dùng dữ liệu mẫu SDU_01")
        with right:
            cycle = st.number_input(
                "Chu kỳ xả",
                min_value=1,
                max_value=100000,
                value=1,
                step=1,
                disabled=mode == "Theo lô",
            )
            csv_download(
                "Tải CSV mẫu",
                sample,
                "mau_mot_chu_ky.csv" if mode == "Một chu kỳ" else "mau_theo_lo.csv",
            )
        run = st.button(
            "Dự đoán SOH", type="primary", icon=":material/bolt:", width="stretch"
        )
    with st.expander("Thông số đầu vào"):
        st.dataframe(
            pd.DataFrame(
                {
                    "Cột": [
                        "time",
                        "terminal_voltage",
                        "terminal_current",
                        "temperature",
                        "phase_code",
                        "cycle",
                        "battery",
                    ],
                    "Đơn vị": [
                        "Giây",
                        "V",
                        "A",
                        "°C",
                        "0: ban đầu; 1: tái sử dụng",
                        "Số nguyên dương",
                        "Mã pin",
                    ],
                    "Yêu cầu": [
                        "Từ đầu xả",
                        "Điện áp cell NMC 2,4 Ah",
                        "Dòng âm khi xả",
                        "Nhiệt độ bề mặt",
                        "Giai đoạn của pin",
                        "Bắt buộc khi xử lý theo lô",
                        "Khuyến nghị với dữ liệu theo lô",
                    ],
                }
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Cửa sổ 0–120 giây: ít nhất 5 mẫu, bắt đầu ≤20 giây, kết thúc ≥90 giây; ít nhất 3 mẫu xả trải dài ≥30 giây. Tối đa 2.000 chu kỳ/lô. CSV gốc SDU được đọc theo khối, chỉ giữ cửa sổ đầu xả."
        )
    content = uploaded.getvalue() if uploaded is not None else None
    input_key = (
        selected_model,
        phase_code,
        content,
        use_example,
        cycle,
        mode,
        uploaded.name if uploaded is not None else "",
    )
    if run:
        st.session_state.pop("forecast_result", None)
        try:
            if content is None and not use_example:
                raise ValueError("Hãy tải CSV hoặc chọn dữ liệu mẫu.")
            if content is None and mode == "Một chu kỳ" and cycle != 1:
                raise ValueError("CSV mẫu thuộc chu kỳ 1.")
            with st.spinner("Đang đọc dữ liệu..."):
                frame = (
                    read_csv(content, phase_code=phase_code)
                    if content is not None
                    else sample.copy()
                )
            if mode == "Một chu kỳ" and frame.attrs.get("source_format") == "sdu_raw":
                frame = frame[frame.cycle == cycle].copy()
                if frame.empty:
                    raise ValueError(
                        "File không có chu kỳ xả đã chọn. Kiểm tra số chu kỳ hoặc chọn Theo lô."
                    )
            artifact = model(selected_model)
            features, outside = None, []
            if mode == "Một chu kỳ":
                estimate, features, outside = predict(frame, cycle, artifact)
                battery = (
                    str(frame.battery.iloc[0])
                    if "battery" in frame
                    else "Không cung cấp"
                )
                rows = pd.DataFrame(
                    [
                        {
                            "battery": battery,
                            "cycle": int(cycle),
                            "phase_code": int(frame.phase_code.iloc[0]),
                            "measurement_count": len(frame),
                            "predicted_soh_pct": estimate,
                            "status": "Thành công",
                            "outside_count": len(outside),
                            "error": "",
                        }
                    ]
                )
            else:
                rows = predict_batch(frame, artifact)
            rows["model"] = selected_model
            created = current_time()
            source = (
                uploaded.name
                if content is not None
                else "Mẫu SDU_01 · đã dùng huấn luyện"
            )
            request_id = hashlib.sha256(
                (
                    content
                    if content is not None
                    else sample.to_csv(index=False).encode()
                )
                + str((cycle, phase_code, mode, source, selected_model)).encode()
            ).hexdigest()
            st.session_state["prediction_history"] = add_history(
                st.session_state.get("prediction_history", []),
                rows,
                request_id,
                source,
                created,
            )
            st.session_state["forecast_result"] = (
                input_key,
                rows,
                features,
                outside,
                frame,
                created,
                source,
            )
        except (
            ValueError,
            TypeError,
            KeyError,
            UnicodeDecodeError,
            pd.errors.ParserError,
            OSError,
            EOFError,
        ) as error:
            st.error(str(error))
    result = st.session_state.get("forecast_result")
    if not result or result[0] != input_key:
        return
    _, rows, features, outside, frame, created, source = result
    section("01", "Kết quả", created + " · UTC+7")
    if mode == "Một chu kỳ":
        single_result(rows, features, outside, frame, source)
    else:
        valid = rows.status.eq("Thành công")
        for column, label, value in zip(
            st.columns(3),
            ["Chu kỳ xử lý", "Thành công", "Dữ liệu không hợp lệ"],
            [len(rows), int(valid.sum()), int((~valid).sum())],
        ):
            with column:
                st.metric(label, value)
        st.dataframe(vietnamese_table(rows).round(3), hide_index=True, width="stretch")
        if valid.any():
            chart = rows[valid].rename(columns={"predicted_soh_pct": "soh_pct"})
            chart["battery"] = (
                chart.battery
                + " · "
                + chart.phase_code.map({0: "Ban đầu", 1: "Tái sử dụng"})
            )
            from charts import soh_trend

            st.altair_chart(soh_trend(chart), width="stretch", theme=None)
        st.caption(source + " · SOH theo dung lượng danh định 2,4 Ah")
    export = rows.assign(window_seconds=120)
    a, b = st.columns(2)
    with a:
        csv_download(
            "Tải kết quả CSV", vietnamese_table(export), "vincent_d_ket_qua.csv"
        )
    with b:
        st.download_button(
            "Tải phiếu HTML",
            html_report(export, created, source).encode("utf-8"),
            "vincent_d_phieu_soh.html",
            "text/html",
            icon=":material/description:",
            width="stretch",
        )


def single_result(rows, features, outside, frame, source):
    left, right = st.columns([1, 1.5], gap="large")
    with left:
        with st.container(border=True):
            st.metric("SOH dự đoán", f"{rows.predicted_soh_pct.iloc[0]:.2f}%")
            st.caption("SDU · NMC/graphite · dung lượng danh định 2,4 Ah")
    with right:
        st.text(source)
        st.write(f"Chu kỳ {int(rows.cycle.iloc[0])} · {len(frame)} điểm đo")
        if outside:
            st.warning(
                "Ngoài miền huấn luyện: " + ", ".join(COLUMNS[name] for name in outside)
            )
        else:
            st.caption("Các đặc trưng nằm trong khoảng giá trị của tập huấn luyện.")
    preview = frame[pd.to_numeric(frame.time) <= 120]
    for column, name, label, color in zip(
        st.columns(3),
        ["terminal_voltage", "terminal_current", "temperature"],
        ["Điện áp (V)", "Dòng điện (A)", "Nhiệt độ (°C)"],
        ["#087f70", "#6576a8", "#eb8c5e"],
    ):
        with column:
            with st.container(border=True):
                st.altair_chart(
                    signal(preview, name, label, color), width="stretch", theme=None
                )
    with st.expander("Đặc trưng đầu vào"):
        st.dataframe(
            vietnamese_table(features).T.rename(columns={0: "Giá trị"}), width="stretch"
        )
