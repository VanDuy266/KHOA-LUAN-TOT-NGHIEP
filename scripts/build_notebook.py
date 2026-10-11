"""Create and execute an EDA notebook in this environment's Python kernel."""
import os
import sys
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/battery-soh-matplotlib")
    os.environ.setdefault("JUPYTER_DATA_DIR", str(ROOT / ".cache/jupyter"))
    os.environ.setdefault("IPYTHONDIR", str(ROOT / ".cache/ipython"))
    os.environ.setdefault("JUPYTER_RUNTIME_DIR", str(ROOT / ".cache/jupyter-runtime"))
    spec = ROOT / ".cache/kernel-spec"
    spec.mkdir(parents=True, exist_ok=True)
    import json
    (spec / "kernel.json").write_text(json.dumps({"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "Battery SOH Python", "language": "python"}))
    KernelSpecManager().install_kernel_spec(str(spec), kernel_name="battery-soh", user=True, replace=True)
    notebook = nbformat.v4.new_notebook(metadata={"kernelspec": {"display_name": "Battery SOH Python", "language": "python", "name": "battery-soh"}})
    markdown, code = nbformat.v4.new_markdown_cell, nbformat.v4.new_code_cell
    notebook.cells = [
        markdown("# Phân tích khám phá SOH\nDữ liệu chuyển đổi công khai dẫn nguồn NASA; chưa đối chiếu MAT gốc. Notebook chỉ mô tả dữ liệu và kết quả, không fit mô hình trên test."),
        code("from pathlib import Path\nimport pandas as pd\nimport matplotlib.pyplot as plt\nROOT = Path.cwd()\nassert (ROOT / 'reports/features.csv').exists()\ndata = pd.read_csv(ROOT / 'reports/features.csv')\naudit = pd.read_csv(ROOT / 'reports/data_audit.csv')\naudit"),
        markdown("## Thống kê từng pin\nNhãn SOH tính theo 2 Ah; 468 chu kỳ chính, không loại chu kỳ. Các pin bổ sung cần xác minh trước khi phân tích chung."),
        code("data.groupby('battery').agg(cycles=('cycle', 'count'), min_soh=('soh_pct', 'min'), max_soh=('soh_pct', 'max'))"),
        code("fig, ax = plt.subplots(figsize=(9, 4))\nfor battery, group in data.groupby('battery'):\n    ax.plot(group.cycle, group.soh_pct, label=battery)\nax.set(xlabel='Discharge cycle', ylabel='SOH (%)', title='Measured SOH from converted data')\nax.legend()\nplt.show()"),
        markdown("## Tương quan mô tả\nTương quan trên dữ liệu gộp không chứng minh quan hệ nhân quả hoặc giá trị dự đoán trên pin mới. Không dùng biểu đồ này để chọn đặc trưng dựa trên test."),
        code("corr = data.drop(columns='battery').corr()\nfig, ax = plt.subplots(figsize=(9, 7))\nimage = ax.imshow(corr, vmin=-1, vmax=1, cmap='coolwarm')\nax.set_xticks(range(len(corr)), corr.columns, rotation=90)\nax.set_yticks(range(len(corr)), corr.columns)\nfig.colorbar(image, ax=ax)\nfig.tight_layout()\nplt.show()"),
        markdown("## Kết quả leave-one-battery-out\nMAE/RMSE đo bằng điểm phần trăm SOH; trung bình không trọng số giữa pin. Chỉ ba pin, chưa đủ kết luận về xe điện thực tế."),
        code("pd.read_csv(ROOT / 'reports/metrics_summary.csv')"),
        code("pd.read_csv(ROOT / 'reports/metrics_by_battery.csv')"),
        markdown("## Điểm cần xác minh\nB05/B07 trong bản chuyển đổi có cùng trục thời gian. Checksum xác nhận phiên bản file, không xác nhận đúng với NASA gốc. Cần tái trích xuất dữ liệu gốc trước khi chốt kết luận khoa học."),
    ]
    NotebookClient(notebook, timeout=120, kernel_name="battery-soh", resources={"metadata": {"path": str(ROOT)}}).execute()
    target = ROOT / "notebooks"
    target.mkdir(exist_ok=True)
    nbformat.write(notebook, target / "01_eda.ipynb")
    print("Executed EDA notebook with current venv kernel")


if __name__ == "__main__":
    main()
