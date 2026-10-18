"""Điểm vào ứng dụng. Mỗi màn hình nằm riêng trong app/screens để dễ sửa."""
import sys
from pathlib import Path
import streamlit as st

APP = Path(__file__).resolve().parent
ROOT = APP.parent
# Cho phép chạy từ thư mục bất kỳ bằng streamlit run app/streamlit_app.py.
sys.path.insert(0, str(APP))
sys.path.insert(0, str(ROOT / "src"))

from screens import overview, explorer, evaluation, forecast, profile

st.set_page_config(page_title="PinLab · Sức khỏe pin", page_icon="🔋", layout="wide", initial_sidebar_state="auto")
st.markdown("<style>" + (APP / "styles.css").read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-mark">ϟ</div><div><div class="brand-name">PinLab</div>'
                '<div class="brand-sub">DỮ LIỆU & SỨC KHỎE PIN</div></div></div><div class="sidebar-heading">KHÔNG GIAN NGHIÊN CỨU</div>', unsafe_allow_html=True)
    page = st.radio("Điều hướng", ["Tổng quan", "Tra cứu pin", "Đánh giá mô hình", "Dự đoán SOH", "Hồ sơ đề tài"], label_visibility="collapsed", key="navigation")
    st.markdown('<div class="sidebar-note">Cell lithium-ion · Dữ liệu NASA<br>Ước lượng SOH từ 120 giây đầu xả</div>'
                '<div class="sidebar-person">Nguyễn Văn Duy<small>MSSV 2311553949<br>Chuyên ngành: Khoa Học Dữ Liệu</small></div>', unsafe_allow_html=True)

required = ["reports/features.csv", "reports/metrics_summary.csv", "reports/metrics_by_battery.csv",
    "reports/data_audit.csv", "reports/predictions.csv", "reports/dataset_summary.json",
    "reports/removed_measurements.csv", "artifacts/random_forest.joblib", "data/clean/measurements.csv"]
missing = [name for name in required if not (ROOT / name).exists()]
if missing:
    st.error("Chưa đủ dữ liệu để mở sản phẩm. Hãy chạy bước chuẩn bị ở thư mục chính.")
    st.code("python scripts/download_data.py\npython scripts/prepare_data.py\npython scripts/run_experiment.py", language="bash")
    with st.expander("Các file còn thiếu"): st.write(missing)
    st.stop()

screens = {"Tổng quan": overview.render, "Tra cứu pin": explorer.render,
           "Đánh giá mô hình": evaluation.render, "Dự đoán SOH": forecast.render, "Hồ sơ đề tài": profile.render}
screens[page]()
st.markdown('<div class="app-footer"><span>PinLab / Khóa luận tốt nghiệp · Nguyễn Văn Duy</span>'
            '<span>Khoa Học Dữ Liệu · Nghiên cứu trên cell thử nghiệm</span></div>', unsafe_allow_html=True)
