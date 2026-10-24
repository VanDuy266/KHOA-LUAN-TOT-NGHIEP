"""Tạo notebook có sẵn kết quả để xem trực tiếp trong VS Code."""

import base64
import contextlib
import io
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]


def main():
    cells = []
    namespace = {}
    counter = 0

    def markdown(text):
        cells.append(dict(cell_type="markdown", metadata={}, source=text))

    def code(source):
        nonlocal counter
        counter += 1
        outputs = []

        def display(value):
            data = {"text/plain": repr(value)}
            if hasattr(value, "to_html"):
                data["text/html"] = value.to_html(index=False)
            outputs.append(dict(output_type="display_data", metadata={}, data=data))

        def show():
            for number in plt.get_fignums():
                figure = plt.figure(number)
                buffer = io.BytesIO()
                figure.savefig(buffer, format="png", dpi=130, bbox_inches="tight")
                outputs.append(dict(output_type="display_data", metadata={}, data={"image/png": base64.b64encode(buffer.getvalue()).decode()}))
                plt.close(figure)

        namespace["display"] = display
        plt.show = show
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            exec(compile(source, f"cell_{counter}", "exec"), namespace)
        if stream.getvalue():
            outputs.append(dict(output_type="stream", name="stdout", text=stream.getvalue()))
        cells.append(dict(cell_type="code", metadata={}, source=source, execution_count=counter, outputs=outputs))

    markdown("# Tiền xử lý, biểu đồ và dự đoán\nKết quả hiển thị trực tiếp trong VS Code. Các ô mã có thể chạy lại bằng kernel Python của dự án.\n\nBiểu đồ kiểm thử đọc kết quả đã lưu; ô dự đoán mẫu gọi mô hình Random Forest đã huấn luyện.")
    code('''from pathlib import Path
import sys
import pandas as pd
import matplotlib.pyplot as plt
import joblib

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "reports/features.csv").exists())
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "src"))
from prediction import read_csv, predict
from input_audit import audit_frame
from battery_soh.features import FEATURES
''')
    markdown("## 1. Tiền xử lý\nĐọc mẫu CSV, kiểm tra cấu trúc và từng chu kỳ. Có thể thay `file_path` bằng đường dẫn file của bạn.")
    code('''file_path = ROOT / "examples/chu_ky_mau_SDU.csv"
frame = read_csv(file_path.read_bytes(), phase_code=0)
print("File:", file_path.name, "| Số dòng:", len(frame))
display(frame.head(10))
schema, checks, issue = audit_frame(frame)
display(schema)
display(checks)
if issue:
    print(issue)
''')
    markdown("## 2. Đặc trưng và dự đoán mẫu\nMẫu thuộc bộ dữ liệu huấn luyện. Kết quả kiểm thử pin giữ riêng ở phần tiếp theo.")
    code('''artifact = joblib.load(ROOT / "artifacts/random_forest.joblib")
cycle = int(frame.cycle.iloc[0])
estimate, features, outside = predict(frame, cycle, artifact)
display(features.T.rename(columns={0: "Giá trị"}).rename_axis("Đặc trưng").reset_index())
print(f"SOH dự đoán: {estimate:.3f}%")
print("Đặc trưng ngoài miền:", outside)
''')
    markdown("## 3. Tín hiệu đầu vào")
    code('''window = frame[frame.time <= 120].sort_values("time")
fig, axes = plt.subplots(1, 3, figsize=(14, 3.5))
for ax, column, title in zip(axes, ["terminal_voltage", "terminal_current", "temperature"], ["Điện áp (V)", "Dòng điện (A)", "Nhiệt độ (°C)"]):
    ax.plot(window.time, window[column], color="#087f70")
    ax.set(xlabel="Thời gian (giây)", ylabel=title)
    ax.grid(alpha=.2)
fig.tight_layout()
plt.show()
''')
    markdown("## 4. Thực tế và dự đoán trên pin kiểm thử\nThay `model_name`, `battery` và `phase` để xem phần khác.")
    code('''predictions = pd.read_csv(ROOT / "reports/predictions.csv")
model_name = "Random Forest"
battery = "SDU_01"
phase = "primary"
selected = predictions[(predictions.model == model_name) & (predictions.battery == battery) & (predictions.phase == phase)].sort_values("cycle")
if selected.empty:
    raise ValueError("Không có dữ liệu cho mô hình, pin và giai đoạn đã chọn.")
fig, ax = plt.subplots(figsize=(11, 4))
ax.plot(selected.cycle, selected.actual_soh, label="SOH thực tế", color="#087f70")
ax.plot(selected.cycle, selected.predicted_soh, label="SOH dự đoán", color="#eb8c5e", linestyle="--")
ax.set(xlabel="Chu kỳ xả", ylabel="SOH (%)", title=f"{model_name} · {battery} · {phase}")
ax.legend()
ax.grid(alpha=.2)
plt.show()
display(selected.head(15))
''')
    markdown("## 5. So sánh mô hình\nChỉ số tổng hợp kiểm thử theo nhóm pin.")
    code('''metrics = pd.read_csv(ROOT / "reports/metrics_summary.csv")
display(metrics.round(4))
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
for ax, metric in zip(axes, ["mae", "rmse", "r2"]):
    ax.barh(metrics.model, metrics[metric], color="#087f70")
    ax.set_title(metric.upper())
    ax.grid(axis="x", alpha=.2)
fig.tight_layout()
plt.show()
''')
    output = ROOT / "notebooks/02_ket_qua_tung_phan.ipynb"
    output.write_text(json.dumps(dict(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.12"}}, nbformat=4, nbformat_minor=5), ensure_ascii=False, indent=1), encoding="utf-8")
    print("Saved:", output.name)


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
