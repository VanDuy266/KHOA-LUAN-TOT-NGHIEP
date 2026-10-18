"""Trang dự đoán: hướng dẫn, dữ liệu đầu vào, kết quả và xuất CSV."""
import pandas as pd
import streamlit as st
from app_data import table, model
from components import heading, section, stat, note, csv_download
from labels import COLUMNS, vietnamese_table
from charts import signal
from prediction import predict, read_csv


def render():
    heading("DỰ ĐOÁN / 03", "Ước lượng SOH từ một chu kỳ xả.",
            "Tải tín hiệu điện áp, dòng điện và nhiệt độ. Mô hình chỉ sử dụng dữ liệu trong 120 giây đầu.")
    for column, title, body in zip(st.columns(3), ["01 / Chuẩn bị", "02 / Kiểm tra", "03 / Đọc kết quả"],
        ["Một CSV của một pin và một chu kỳ xả. Thời gian tính bằng giây.",
         "Cần tín hiệu đầu chu kỳ, dòng âm khi xả và đủ mẫu trong cửa sổ quan sát.",
         "Nhận SOH ước lượng, xem đặc trưng và tải kết quả. Đây không phải chỉ số mức sạc SOC."]):
        with column: note(title, body)
    section("01", "Dữ liệu đầu vào", "Bạn có thể thử mẫu B0005 trước khi tải dữ liệu riêng.")
    measurements = table("data/clean/measurements.csv")
    example = measurements[(measurements.battery == "B0005") & (measurements.cycle == 1) & (measurements.time <= 120)]
    example = example[["time", "terminal_voltage", "terminal_current", "temperature"]]
    with st.container(border=True):
        left, right = st.columns([1.3, 1], gap="large")
        with left:
            uploaded = st.file_uploader("Tải CSV một chu kỳ xả · tối đa 5 MB", type=["csv"], help="Chấp nhận cột gốc hoặc tên tiếng Việt xuất từ trang Tra cứu pin.")
            use_example = st.checkbox("Dùng CSV mẫu để minh họa")
        with right:
            cycle = st.number_input("Chỉ số chu kỳ xả", min_value=1, max_value=100000, value=1, step=1)
            csv_download("Tải CSV mẫu B0005", example, "chu_ky_mau_B0005.csv")
            st.caption("Cột gốc: time, terminal_voltage, terminal_current, temperature. Không cần nhãn SOH hoặc capacity.")
        run = st.button("Ước lượng SOH", type="primary", icon=":material/bolt:", use_container_width=True)
    with st.expander("Định dạng và điều kiện kiểm tra"):
        st.dataframe(pd.DataFrame({"Cột": ["time", "terminal_voltage", "terminal_current", "temperature"],
            "Đơn vị": ["Giây", "V", "A", "°C"], "Ý nghĩa": ["Từ đầu chu kỳ", "Điện áp cell", "Dòng âm khi xả", "Nhiệt độ cell"]}), hide_index=True, use_container_width=True)
        st.write("Ít nhất 5 mẫu trong 0–120 giây, bắt đầu không muộn hơn 20 giây và kết thúc không sớm hơn 90 giây. Cần 3 mẫu dòng < −0,1 A trải dài ít nhất 30 giây. Không nhận thời gian trùng hoặc tín hiệu thiếu.")
    # Lưu kết quả qua lần bấm tải để kết quả không biến mất khi Streamlit chạy lại.
    # Chỉ hiển thị nếu đầu vào vẫn khớp, tránh nhầm kết quả cũ với CSV mới.
    content = uploaded.getvalue() if uploaded is not None else None
    input_key = (content, use_example, cycle)
    if run:
        st.session_state.pop("forecast_result", None)
        try:
            if content is None and not use_example:
                raise ValueError("Hãy tải CSV hoặc chọn dùng mẫu để bắt đầu.")
            if content is None and cycle != 1:
                raise ValueError("CSV mẫu thuộc chu kỳ 1. Hãy nhập chu kỳ 1 hoặc tải CSV của bạn.")
            frame = read_csv(content) if content is not None else example.copy()
            artifact = model()
            estimate, features, outside = predict(frame, cycle, artifact)
            st.session_state["forecast_result"] = (input_key, estimate, features, outside, frame, content is None)
        except (ValueError, TypeError, KeyError, UnicodeDecodeError, pd.errors.ParserError) as error:
            st.error(str(error))
    stored = st.session_state.get("forecast_result")
    if not stored or stored[0] != input_key:
        if not run: note("Chưa có kết quả", "Chọn mẫu hoặc tải CSV, sau đó bấm Ước lượng SOH. Kết quả sẽ xuất hiện tại đây.", "soft")
        return
    _, estimate, features, outside, frame, is_example = stored
    section("02", "Kết quả ước lượng", "Random Forest · cùng quy trình đặc trưng với thực nghiệm · cửa sổ đầu 120 giây")
    left, right = st.columns([1, 1.6], gap="large")
    with left:
        # Giữ metric ngữ nghĩa để hỗ trợ đọc màn hình và kiểm tra chức năng.
        with st.container(border=True):
            st.metric("SOH ước lượng", f"{estimate:.2f}%")
            st.caption("Tỷ lệ dung lượng so với mức danh định 2 Ah. Không phải lượng pin còn lại.")
    with right:
        if outside:
            st.warning("Đặc trưng ngoài miền huấn luyện: " + ", ".join(COLUMNS[name] for name in outside) + ". Cần thận trọng khi diễn giải.")
        else:
            note("Phạm vi đầu vào", "Các đặc trưng nằm trong khoảng từng cột đã gặp khi huấn luyện. Điều này không bảo đảm dữ liệu cùng phân phối hoặc dự đoán chính xác.")
        st.caption("CSV mẫu đã có trong huấn luyện demo; đây là minh họa thao tác, không phải điểm kiểm thử độc lập." if is_example else "Mô hình nghiên cứu trên bốn cell thử nghiệm. Dữ liệu tải lên chưa được xác minh nguồn hoặc điều kiện đo.")
    st.caption("Dữ liệu upload chỉ được xử lý trong phiên ứng dụng; không được ghi thêm vào dataset hay dùng huấn luyện lại.")
    preview = frame[pd.to_numeric(frame.time) <= 120]
    charts = st.columns(3)
    for column, name, label, color in zip(charts, ["terminal_voltage", "terminal_current", "temperature"],
        ["Điện áp (V)", "Dòng điện (A)", "Nhiệt độ (°C)"], ["#087f70", "#6576a8", "#eb8c5e"]):
        with column:
            with st.container(border=True): st.altair_chart(signal(preview, name, label, color), use_container_width=True, theme=None)
    with st.expander("11 đặc trưng đã dùng cho dự đoán"):
        st.dataframe(vietnamese_table(features).T.rename(columns={0: "Giá trị"}), use_container_width=True)
    output = features.assign(predicted_soh_pct=estimate, model="Random Forest", window_seconds=120)
    csv_download("Tải kết quả dự đoán", vietnamese_table(output), "ket_qua_soh.csv")
