"""Tạo và thực thi notebook phân tích SDU bằng kernel của môi trường hiện tại."""

import os
import sys
import json
import tempfile
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager

ROOT = Path(__file__).resolve().parents[1]


def main():
    for name, folder in [
        ("JUPYTER_DATA_DIR", "jupyter"),
        ("IPYTHONDIR", "ipython"),
        ("JUPYTER_RUNTIME_DIR", "jupyter-runtime"),
    ]:
        os.environ.setdefault(name, str(ROOT / ".cache" / folder))
    os.environ.setdefault(
        "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "battery-soh-matplotlib")
    )
    spec = ROOT / ".cache/kernel-spec"
    spec.mkdir(parents=True, exist_ok=True)
    (spec / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [
                    sys.executable,
                    "-m",
                    "ipykernel_launcher",
                    "-f",
                    "{connection_file}",
                ],
                "display_name": "SDU Python",
                "language": "python",
            }
        )
    )
    KernelSpecManager().install_kernel_spec(
        str(spec), kernel_name="battery-soh", user=True
    )
    md, code = nbformat.v4.new_markdown_cell, nbformat.v4.new_code_cell
    cells = [
        md(
            "# Phân tích và dự đoán SOH — SDU 2025\nNguyễn Văn Duy · 2311553949\n\nNguồn: https://doi.org/10.5281/zenodo.14859405 · CC BY 4.0. Bộ chọn 10.505.065 điểm đo, 86 pin, 20.823 chu kỳ. Mỗi mẫu huấn luyện là một chu kỳ, không phải một điểm cảm biến."
        ),
        code(
            "from pathlib import Path\nimport json\nimport sys\nimport numpy as np\nimport pandas as pd\nimport matplotlib.pyplot as plt\nROOT = Path.cwd()\nif ROOT.name == 'notebooks': ROOT = ROOT.parent\nsys.path.insert(0, str(ROOT/'src'))\nfrom battery_soh.features import FEATURES\ndata = pd.read_csv(ROOT/'reports/features.csv')\njson.loads((ROOT/'reports/dataset_summary.json').read_text())"
        ),
        md(
            "## 1. Kiểm tra bảng chu kỳ\nKhóa gồm mã pin vật lý, giai đoạn và chu kỳ. Dung lượng tham chiếu là 2,4 Ah. SOH trên 100% được giữ nguyên."
        ),
        code(
            "assert len(data) == 20823 and data.battery.nunique() == 86\nassert not data.duplicated(['battery','phase','cycle']).any()\nassert np.isfinite(data[FEATURES].to_numpy()).all()\nassert np.allclose(data.soh_pct, data.capacity_ah/2.4*100)\ndata.groupby('phase').agg(pins=('battery','nunique'), cycles=('cycle','size'), min_soh=('soh_pct','min'), max_soh=('soh_pct','max'))"
        ),
        code(
            "fig, axes = plt.subplots(1, 2, figsize=(12,4), sharey=True)\nfor ax, (phase, group) in zip(axes, data.groupby('phase')):\n    for battery, part in group.groupby('battery'):\n        part = part.sort_values('cycle')\n        ax.plot(part.cycle, part.soh_pct, alpha=.3, linewidth=.8)\n    ax.set(title=phase, xlabel='Chu kỳ', ylabel='SOH (%)')\nfig.tight_layout()\nplt.show()"
        ),
        md(
            "## 2. Đặc trưng đầu xả\nChỉ lấy 120 giây đầu. Nhãn, dung lượng cuối chu kỳ, tổng số điểm và thời gian toàn chu kỳ không thuộc đầu vào. Tương quan mô tả không chứng minh quan hệ nhân quả; không chọn đặc trưng theo tập kiểm thử."
        ),
        code(
            "corr = data[FEATURES + ['soh_pct']].corr()\nfig, ax = plt.subplots(figsize=(9,8))\nimage = ax.imshow(corr, vmin=-1, vmax=1, cmap='coolwarm')\nax.set_xticks(range(len(corr)), corr.columns, rotation=90)\nax.set_yticks(range(len(corr)), corr.columns)\nfig.colorbar(image, ax=ax)\nfig.tight_layout()\nplt.show()"
        ),
        md(
            "## 3. Phân hoạch pin\nCùng 5 vòng GroupKFold cho các mô hình. Cả hai giai đoạn của một pin nằm trong cùng phía; bộ chuẩn hóa chỉ học trên train."
        ),
        code(
            "split = pd.read_csv(ROOT/'reports/split_assignments.csv')\nassert split.battery.nunique() == len(split) == 86\nfor fold in range(1,6):\n    test_pins = set(split.loc[split.test_fold == fold, 'battery'])\n    train_pins = set(split.loc[split.test_fold != fold, 'battery'])\n    assert train_pins.isdisjoint(test_pins)\nsplit.groupby('test_fold').size().rename('Số pin kiểm thử')"
        ),
        md(
            "## 4. So sánh mô hình\nRidge, Random Forest, LightGBM và GRU; mốc trung bình SOH làm đối chứng. GRU dùng chuỗi V/I/T 25 vị trí trong cửa sổ đầu xả cùng số chu kỳ và giai đoạn, khác biểu diễn của mô hình bảng. MAE/RMSE tính bằng điểm phần trăm SOH, chỉ số chính lấy trung bình theo pin."
        ),
        code(
            "metrics = pd.read_csv(ROOT/'reports/metrics_summary.csv')\ndisplay(metrics)\nfig, ax = plt.subplots(figsize=(9,4))\nax.bar(metrics.model, metrics.mae)\nax.set(ylabel='MAE (điểm % SOH)', title='Kiểm thử pin giữ riêng')\nplt.show()"
        ),
        code("pd.read_csv(ROOT/'reports/metrics_by_phase.csv')"),
        md(
            "## 5. Phân tích sai số\nSai số dương nghĩa là dự đoán cao hơn SOH thực tế. Kiểm tra riêng hai giai đoạn và pin để tránh kết luận từ một điểm trung bình."
        ),
        code(
            "pred = pd.read_csv(ROOT/'reports/predictions.csv')\nrf = pred[pred.model == 'Random Forest'].copy()\nrf['error'] = rf.predicted_soh - rf.actual_soh\nfig, ax = plt.subplots(figsize=(9,4))\nfor phase, part in rf.groupby('phase'):\n    ax.scatter(part.actual_soh, part.error, s=3, alpha=.2, label=phase)\nax.axhline(0, color='black', linewidth=.7)\nax.set(xlabel='SOH thực tế (%)', ylabel='Sai số (điểm % SOH)')\nax.legend()\nplt.show()\nrf.groupby('phase').error.agg(['mean','std','min','max'])"
        ),
        md(
            "## 6. Kiểm tra bổ sung\nBỏ nhóm đặc trưng dùng cùng phân hoạch và tham số RF. Kiểm thử 70/30 theo thời gian trong từng pin và giai đoạn trả lời bài toán khác với pin mới; không trộn điểm."
        ),
        code(
            "display(pd.read_csv(ROOT/'reports/ablation_summary.csv'))\ntemporal = pd.read_csv(ROOT/'reports/temporal_metrics.csv')\nassert (temporal.last_train_cycle < temporal.first_test_cycle).all()\ntemporal.groupby('model')[['mae','rmse']].mean()"
        ),
        md(
            "## 7. Chất lượng và giới hạn\n26 điểm nghi vấn được giữ để xem xét, không nằm trong cửa sổ 120 giây đầu. Bộ chọn giữ đủ các chu kỳ xả tham chiếu, không gồm mọi trạng thái trong nguồn. Dữ liệu phòng thí nghiệm chưa đại diện cho bộ pin xe thực tế tại Việt Nam."
        ),
        code("json.loads((ROOT/'reports/dataset_check.json').read_text())"),
    ]
    notebook = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "SDU Python",
                "language": "python",
                "name": "battery-soh",
            }
        },
    )
    NotebookClient(
        notebook,
        timeout=120,
        kernel_name="battery-soh",
        resources={"metadata": {"path": str(ROOT)}},
    ).execute()
    (ROOT / "notebooks").mkdir(exist_ok=True)
    nbformat.write(notebook, ROOT / "notebooks/01_eda.ipynb")
    print(
        f"Đã thực thi notebook SDU: {sum(cell.cell_type == 'code' for cell in notebook.cells)} ô mã, không lỗi."
    )


if __name__ == "__main__":
    main()
