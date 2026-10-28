"""Fixed chronological holdout audit for experimental trend-to-threshold baseline."""
from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from webapp.health import trend_forecast
from webapp.data import table


def main():
    out=ROOT/"reports/health";out.mkdir(parents=True,exist_ok=True)
    rows=[]
    datasets={"SDU":[],"BMS":[]}
    for (pin,phase),g in table("reports/features.csv").groupby(["battery","phase"]):
        datasets["SDU"].append((pin+"/"+phase,g[["cycle","soh_pct"]].rename(columns={"cycle":"position"}).sort_values("position")))
    b=table("reports/bms/monthly_reference.csv")
    for vehicle,g in b.groupby("vehicle"):
        g=g.sort_values("month").copy();periods=pd.PeriodIndex(g.month,freq="M")
        g["position"]=periods.astype("int64")-periods.astype("int64").min();g["soh_pct"]=g.reference_capacity_ah/145*100
        datasets["BMS"].append((vehicle,g[["position","soh_pct"]]))
    for dataset,groups in datasets.items():
        for name,g in groups:
            g=g.reset_index(drop=True)
            for fraction in [.6,.7,.8]:
                n=int(len(g)*fraction)
                if n<5 or len(g)-n<3:continue
                train=g.iloc[:n];future=g.iloc[n:];r=trend_forecast(train,80)
                # First observed <=80 point, only if no earlier observed crossing.
                early=bool((train.soh_pct<=80).any());cross=future[future.soh_pct<=80]
                observed=None if early or cross.empty else float(cross.position.iloc[0])
                prediction=r["crossing"] if r["status"]=="estimated" else None
                error=None if observed is None or prediction is None else abs(prediction-observed)
                rows.append(dict(dataset=dataset,group=name,prefix=fraction,train_samples=n,test_samples=len(future),
                    cutoff=float(train.position.iloc[-1]),status=r["status"],predicted_crossing=prediction,
                    observed_crossing=observed,absolute_crossing_error=error,
                    already_crossed=early,right_censored=not early and cross.empty))
    data=pd.DataFrame(rows);data.to_csv(out/"chronological_results.csv",index=False)
    summaries=[]
    for dataset,g in data.groupby("dataset"):
        events=g[g.observed_crossing.notna()];scored=g[g.absolute_crossing_error.notna()]
        summaries.append(dict(dataset=dataset,origins=len(g),forecasted=int((g.status=="estimated").sum()),
            future_crossings=len(events),scored_crossings=len(scored),right_censored=int(g.right_censored.sum()),
            crossing_mae=None if scored.empty else float(scored.absolute_crossing_error.mean()),
            unit="cycles" if dataset=="SDU" else "months"))
    (out/"summary.json").write_text(json.dumps(summaries,indent=2),"utf-8")
    lines=["# Kiểm chứng dự báo xuống ngưỡng SOH — thử nghiệm", "",
      "Mốc cơ sở: hồi quy tuyến tính OLS trên tối đa 20 mốc gần nhất. Không phải mô hình dự báo sự cố pin. Mốc 80% là tiêu chí nghiên cứu minh họa, không phải giới hạn an toàn của hãng.",
      "Mỗi lịch sử được cắt tại 60%, 70%, 80% số mốc; chỉ phần trước mốc cắt dùng fit. Phần sau chỉ dùng đối chiếu. Không dùng giá trị tương lai khi tính đường dự báo. Không chọn mô hình/siêu tham số theo kết quả này.",
      "Chỉ ngoại suy khi độ dốc âm, R² fit ít nhất 0,3, đường fit hiện tại trên ngưỡng và điểm giao không quá 3 lần khoảng lịch sử fit. Các quy tắc này cố định trước khi chạy, là giới hạn mô hình chứ không phải tiêu chí an toàn.","",
      "| Bộ dữ liệu | Mốc đánh giá | Có ngoại suy | Chạm ngưỡng tương lai quan sát được | Chạm ngưỡng có dự báo để chấm | Chưa quan sát chạm ngưỡng | MAE thời điểm (đơn vị) |",
      "|---|---:|---:|---:|---:|---:|---|"]
    for r in summaries:
        value="Chưa đủ trường hợp để tính" if r["crossing_mae"] is None else f"{r['crossing_mae']:.2f} {r['unit']}"
        lines.append(f"| {r['dataset']} | {r['origins']} | {r['forecasted']} | {r['future_crossings']} | {r['scored_crossings']} | {r['right_censored']} | {value} |")
    lines += ["", "Điểm chạm tham chiếu là mốc quan sát đầu tiên <=80%, không nội suy; lịch sử không chạm ngưỡng được coi là bị kiểm duyệt phải, không gán ngày hỏng. Lịch sử đã từng chạm trước mốc cắt bị loại khỏi đánh giá sự kiện tương lai. Sai số chỉ trên trường hợp vừa quan sát được chạm vừa có dự báo; không đại diện toàn bộ nhóm. Nhiều mốc cắt cùng pin/xe có phụ thuộc, không phải mẫu độc lập.",
      "SDU tính theo chu kỳ; BMS tính theo tháng, không so trực tiếp hai MAE. BMS dùng nhãn xe–tháng suy ra từ dòng điện/SOC và có thể tổng hợp các phiên muộn hơn trong cùng tháng, nên chỉ là kiểm chứng hồi cứu, không khẳng định triển khai thời gian thực. Chưa có khoảng dự đoán được hiệu chuẩn; kết quả là ngoại suy thử nghiệm cần kiểm chứng ngoài tập này.",
      "Không dùng kết quả để kết luận pin tốt/xấu, an toàn, hỏng/không hỏng hoặc ngày xảy ra sự cố. Chẩn đoán lỗi cần dữ liệu lỗi đã xác minh mà bộ dữ liệu hiện tại chưa có.",
      "Phương pháp OLS: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html . Phân biệt dự báo tuổi thọ tới mốc dung lượng với chẩn đoán lỗi: https://data.nasa.gov/dataset/li-ion-battery-aging-datasets .",
      "Tái lập: .venv/Scripts/python.exe scripts/evaluate_health.py; chi tiết từng mốc cắt: chronological_results.csv."]
    (out/"validation.md").write_text("\n\n".join(lines),"utf-8")
    print(json.dumps(summaries,indent=2))

if __name__=="__main__":main()
