"""Sinh phần thực nghiệm XJTU và notebook từ kết quả đã chạy."""
import json
from pathlib import Path
import sys
import pandas as pd
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_documents import md_table


def main():
    folder = ROOT / "reports/xjtu"
    info = json.loads((folder / "dataset_summary.json").read_text())
    run = json.loads((folder / "run_metadata.json").read_text())
    scores = pd.read_csv(folder / "metrics_summary.csv")
    within = scores[scores.design == "XJTU held-out"]
    transfer = scores[scores.design == "SDU to XJTU"]
    batch = scores[scores.design.str.startswith("Held-out batch")]
    rf = within[within.model == "Random Forest"].iloc[0]
    multi = within[within.model == "RF multi-source"].iloc[0]
    delta = multi.mae - rf.mae
    change = "giảm" if delta < 0 else "tăng"
    source = (f"Chọn 23 pin thuộc Batch-1/2 trong 55 pin XJTU. Đã tải và kiểm tra CRC/SHA-256 của 23 thành viên MAT nguyên gốc từ ZIP tác giả. "
              f"Tổng {info['raw_points']:,} điểm đo, {info['source_cycles']:,} phần tử chu kỳ; {info['valid_cycles']:,} chu kỳ đạt kiểm tra đầu vào, "
              f"{info['excluded_cycles']} chu kỳ bị loại, {info['duplicate_window_seconds_aggregated']:,} phép đo trùng giây được gộp trung bình trong cửa sổ dẫn xuất.").replace(",", ".")
    discussion = (f"Random Forest riêng XJTU đạt MAE {rf.mae:.3f}, RMSE {rf.rmse:.3f}, R² {rf.r2:.3f}. "
                  f"RF đa nguồn đạt MAE {multi.mae:.3f}, RMSE {multi.rmse:.3f}, R² {multi.r2:.3f}. "
                  f"MAE {change} {abs(delta):.3f} điểm phần trăm SOH khi thêm nguồn SDU trong cấu hình đã cố định. "
                  "Đây là thực nghiệm thăm dò trên cùng phân hoạch, chưa phải bằng chứng ưu thế thống kê hoặc cải thiện trên mọi điều kiện.")
    text = f'''# Thực nghiệm bổ sung trên XJTU

## Nguồn và phạm vi

Wang, F. (2024). XJTU Battery Dataset. Zenodo, DOI 10.5281/zenodo.10963339, CC BY 4.0. Bài báo: Wang, F., Zhai, Z., Zhao, Z. et al. Nature Communications 15, 4332 (2024), DOI 10.1038/s41467-024-48779-z.

Pin Lishen 18650 NCM, danh định 2 Ah. Dữ liệu phòng thí nghiệm, không phải BMS đo trên xe. SDU 2,4 Ah tiếp tục là dữ liệu chính; không cộng số dòng hai nguồn để mô tả một bộ dữ liệu đồng nhất.

{source}

Batch-1/2 được chọn trước khi đánh giá vì quy trình cố định. Chu kỳ đầu là phép đo 0,2C; không dùng 23 chu kỳ đầu này trong đánh giá 1C chính. Bảng đặc trưng vẫn lưu các chu kỳ hợp lệ để đối chiếu. Số mẫu đánh giá chính: **{run['model_cycles']:,}** chu kỳ. Không gọi dung lượng đo ở 1C và 0,2C là hoàn toàn tương đương; tải xả có thể ảnh hưởng dung lượng khả dụng.

## Đặc trưng, nhãn và phân hoạch

Cửa sổ 120 giây đầu đoạn xả; dùng system_time vì relative_time_min có thể đặt lại theo bước. Gom trung bình V/I/T cùng giây ở bản dẫn xuất, giữ nguyên MAT nguồn. SOH = summary.discharge_capacity_Ah / 2 Ah × 100; đối chiếu dung lượng cực đại đoạn xả, sai lệch tối đa cho phép 0,005 Ah. Không cắt SOH trên 100% và không lấy dung lượng đo làm đầu vào.

Mô hình bảng dùng 11 đặc trưng chung: bỏ phase_code, chia current_mean/current_std cho dung lượng danh định mỗi nguồn để đổi sang C-rate. Không dùng dung lượng đo thực tế để chuẩn hóa đặc trưng. GRU dùng 25 vị trí V/I/T trong 120 giây, dòng điện chia 2 Ah, cùng các nhóm pin; chuẩn hóa chỉ học trên train.

GroupKFold 5 vòng theo 23 pin vật lý, shuffle=True, seed=42. Tham số cố định, không tối ưu theo nhãn kiểm thử. Báo cáo trung bình không trọng số theo pin. Mô hình ứng dụng refit sau đánh giá; kết quả refit trên chính pin đã học không được tính như kiểm thử độc lập.

## So sánh mô hình trên pin XJTU giữ riêng

{md_table(within.drop(columns='design'))}

{discussion}

RF đa nguồn dùng toàn bộ SDU và các pin XJTU thuộc tập học của từng vòng; tổng trọng số mỗi nguồn là 0,5. Không đưa nhãn pin XJTU kiểm thử vào học. Cùng bộ kiểm thử XJTU được dùng để so sánh, không tự chọn mô hình triển khai theo điểm thấp nhất.

![Dự đoán Random Forest trên pin XJTU giữ riêng, chọn pin đầu mỗi batch](../reports/xjtu/held_out_predictions.png)

## Chuyển miền SDU sang XJTU

{md_table(transfer.drop(columns='design'))}

RF SDU nguyên bản giữ đúng 12 đặc trưng và artifact cũ; RF chuẩn hóa dòng được học lại chỉ trên SDU với 11 đặc trưng chung. Cả hai không học từ nhãn XJTU. RF chuẩn hóa đồng thời bỏ phase_code, nên không thể quy toàn bộ khác biệt sai số cho riêng chuẩn hóa dòng. Không gộp điểm chuyển miền này vào điểm 5 vòng XJTU. Sai số hoặc R² âm là kết quả cần báo cáo, không xóa các pin chỉ vì mô hình dự đoán kém. Khác biệt dòng xả, dung lượng, giai đoạn lão hóa và điều kiện đo giới hạn chuyển miền.

Ba đặc trưng current_mean theo C-rate, voltage_std và voltage_slope của toàn bộ các chu kỳ XJTU đánh giá nằm ngoài khoảng min–max SDU trong lần kiểm tra này (reports/xjtu/domain_shift.csv). Điều này cho thấy khác biệt đầu vào rõ rệt. MAE XJTU thấp hơn MAE SDU không được xem là cải thiện trên cùng bộ kiểm thử vì hai nguồn và khoảng nhãn khác nhau.

## Giữ riêng chiến lược sạc

{md_table(batch)}

Batch-1 sạc 2C, Batch-2 sạc 3C trong các chu kỳ thông thường, cùng xả 1C. Mỗi thiết kế học trên một batch và kiểm tra toàn bộ pin batch còn lại; đây là kiểm tra khác với giữ riêng pin ngẫu nhiên theo nhóm.

## Sản phẩm và khả năng tái lập

Ứng dụng có mục Thực nghiệm XJTU: bảng so sánh, đồ thị pin giữ riêng, chất lượng và nguồn, dự đoán bằng mô hình RF riêng XJTU hoặc RF đa nguồn. Đầu vào MAT được xử lý riêng, không qua bộ đọc CSV SDU. Đầu ra có cờ đặc trưng ngoài miền và CSV. Dữ liệu refit được phân biệt với dự đoán giữ riêng pin.

Lệnh chạy từ thư mục gốc dự án, sau khi cài requirements.txt và requirements-deep.txt:

```powershell
.\\.venv\\Scripts\\python.exe scripts\\download_xjtu.py
.\\.venv\\Scripts\\python.exe scripts\\prepare_xjtu.py
.\\.venv\\Scripts\\python.exe scripts\\evaluate_xjtu.py
.\\.venv\\Scripts\\python.exe scripts\\build_xjtu_documents.py
```

Các bảng ở reports/xjtu; notebook notebooks/03_thuc_nghiem_xjtu.ipynb. Nguồn MAT không nằm trong ZIP ứng dụng để giảm kích thước; script tải đúng các thành viên từ ZIP tác giả và kiểm tra CRC/SHA. Không cần tải dữ liệu gốc hay huấn luyện lại để xem kết quả đã đóng gói.

## Giới hạn

Chưa kiểm chứng BMS trên xe, chưa triển khai RUL. Chỉ hai batch cố định được sử dụng; không khẳng định đã đánh giá toàn bộ 55 pin. Kiểm tra số học/cấu trúc và đối chiếu dung lượng không đồng nghĩa loại hết nhiễu hoặc xác nhận hiệu chuẩn thiết bị.
'''
    (ROOT / "docs/thuc-nghiem-xjtu.md").write_text(text)
    brief = f"## 4.11. Thực nghiệm bổ sung trên nguồn XJTU\n\n{source}\n\nKhông dùng 23 chu kỳ đầu 0,2C trong đánh giá chính; còn {run['model_cycles']:,} chu kỳ xả 1C. Dùng SOH theo 2 Ah và 11 đặc trưng chung, chuẩn hóa dòng theo dung lượng danh định; không sửa dữ liệu nguồn. Giữ riêng 23 mã pin qua 5 vòng, seed 42, cấu hình cố định.\n\n{md_table(within.drop(columns='design'))}\n\n{discussion}\n\n![Dự đoán RF trên hai pin XJTU giữ riêng](../reports/xjtu/held_out_predictions.png)\n\nChuyển miền chỉ học trên SDU, không dùng nhãn XJTU:\n\n{md_table(transfer.drop(columns='design'))}\n\nCác phép kiểm tra batch và bảng theo từng pin nằm trong reports/xjtu và docs/thuc-nghiem-xjtu.md. Kết quả vẫn thuộc tế bào trong phòng thí nghiệm; chưa là bằng chứng mô hình dùng được trên xe.\n"
    (folder / "report_section.md").write_text(brief)
    notebook = nbformat.v4.new_notebook(metadata={"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"}})
    cells = [nbformat.v4.new_markdown_cell("# Thực nghiệm XJTU\nLishen NCM 2 Ah, Batch-1/2. Kết quả tách riêng SDU; loại chu kỳ tham chiếu đầu khỏi đánh giá chính."),
    nbformat.v4.new_code_cell('''from pathlib import Path
import sys, json
import pandas as pd
import matplotlib.pyplot as plt
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "reports/xjtu/features.csv").exists())
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.xjtu import normalized_features
from sklearn.ensemble import RandomForestRegressor
folder = ROOT / "reports/xjtu"
info = json.loads((folder / "dataset_summary.json").read_text())
print(json.dumps(info, ensure_ascii=False, indent=2))'''),
    nbformat.v4.new_markdown_cell("## 1. Dữ liệu và nhãn\nNhãn theo dung lượng danh định, không đưa dung lượng đo vào đặc trưng."),
    nbformat.v4.new_code_cell('''data = pd.read_csv(folder / "features.csv")
data = data.loc[data.cycle > 1].reset_index(drop=True)
assert (abs(data.soh_pct - data.capacity_ah / 2 * 100) < 1e-8).all()
display(data.groupby("batch").agg(pins=("battery","nunique"), cycles=("cycle","size"), soh_min=("soh_pct","min"), soh_max=("soh_pct","max")))
display(pd.read_csv(folder / "data_audit.csv"))'''),
    nbformat.v4.new_code_cell('''for battery, part in data.groupby("battery"):
    plt.plot(part.cycle, part.soh_pct, alpha=.5, linewidth=.8)
plt.xlabel("Chu kỳ xả"); plt.ylabel("SOH theo 2 Ah (%)"); plt.title("XJTU: chu kỳ xả 1C")
plt.show()'''),
    nbformat.v4.new_markdown_cell("## 2. Kiểm tra giữ riêng pin và chạy lại RF một vòng\nChỉ dùng pin thuộc tập học. Đây là chạy lại cấu hình cố định, không tìm tham số bằng test."),
    nbformat.v4.new_code_cell('''split = pd.read_csv(folder / "split_assignments.csv").set_index("battery").test_fold
folds = data.battery.map(split)
train, test = folds != 1, folds == 1
assert set(data.loc[train,"battery"]).isdisjoint(data.loc[test,"battery"])
X = normalized_features(data, 2.0)
assert "capacity_ah" not in X and "soh_pct" not in X
model = RandomForestRegressor(n_estimators=100, min_samples_leaf=5, max_depth=16, max_samples=.7, random_state=42, n_jobs=2)
model.fit(X.loc[train], data.loc[train,"soh_pct"])
from sklearn.metrics import mean_absolute_error
print("MAE gộp chu kỳ vòng 1 (khác trung bình theo pin):", mean_absolute_error(data.loc[test,"soh_pct"], model.predict(X.loc[test])))'''),
    nbformat.v4.new_markdown_cell("## 3. So sánh mô hình và kiểm tra chuyển miền\nMAE/RMSE theo điểm phần trăm SOH; bảng tổng hợp lấy trung bình theo pin."),
    nbformat.v4.new_code_cell('''scores = pd.read_csv(folder / "metrics_summary.csv")
display(scores)
display(pd.read_csv(folder / "paired_multi_source.csv"))'''),
    nbformat.v4.new_code_cell('''pred = pd.read_csv(folder / "predictions.csv")
part = pred[(pred.design == "XJTU held-out") & (pred.model == "Random Forest")]
battery = sorted(part.battery.unique())[0]
part = part[part.battery == battery].sort_values("cycle")
plt.plot(part.cycle, part.actual_soh, label="Tham chiếu")
plt.plot(part.cycle, part.predicted_soh, label="RF giữ riêng pin")
plt.title(battery); plt.xlabel("Chu kỳ"); plt.ylabel("SOH (%)"); plt.legend(); plt.show()'''),
    nbformat.v4.new_markdown_cell("## Giới hạn\nDữ liệu lab, khác dòng xả SDU; chưa có kiểm chứng trên xe và RUL. Artifact ứng dụng refit không được dùng thay điểm pin giữ riêng.")]
    notebook.cells = cells
    NotebookClient(notebook, timeout=180, kernel_name="python3", resources={"metadata":{"path":str(ROOT)}}).execute()
    nbformat.write(notebook, ROOT / "notebooks/03_thuc_nghiem_xjtu.ipynb")
    print("Đã sinh phần báo cáo và thực thi notebook XJTU.")


if __name__ == "__main__":
    main()
