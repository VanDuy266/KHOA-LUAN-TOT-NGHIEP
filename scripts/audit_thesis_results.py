"""Recompute saved out-of-fold results; do not refit or certify battery safety."""
from pathlib import Path
import sys, json, hashlib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.features import FEATURES as SDU_FEATURES
from battery_soh.bms import FEATURES as BMS_FEATURES


def read(path):
    p = ROOT / path
    if not p.exists() and p.suffix == ".csv":
        p = p.with_suffix(".csv.gz")
    return pd.read_csv(p)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def score(frame):
    return dict(mae=mean_absolute_error(frame.actual, frame.predicted),
                rmse=float(np.sqrt(mean_squared_error(frame.actual, frame.predicted))),
                r2=r2_score(frame.actual, frame.predicted) if len(frame)>1 else None)


def audit(data, predictions, group, keys, target, expected_folds, reported):
    require(not data.duplicated(keys).any(), "Duplicate source sample keys")
    require(set(expected_folds.index) == set(data[group]), "Missing group fold assignments")
    require(np.isfinite(predictions[["actual", "predicted"]].to_numpy()).all(), "Nonfinite predictions")
    require((predictions.fold == predictions[group].map(expected_folds)).all(), "Test fold mismatch")
    rows=[]; group_rows=[]
    for model, part in predictions.groupby("model"):
        require(not part.duplicated(keys).any(), f"Duplicate test predictions: {model}")
        merged=data[keys+[target]].merge(part[keys+["actual"]], on=keys, how="outer", indicator=True, validate="one_to_one")
        require((merged._merge=="both").all(), f"Incomplete or extra test coverage: {model}")
        require(np.allclose(merged[target],merged.actual,rtol=1e-10,atol=1e-8), f"Reference label mismatch: {model}")
        values=[]
        for name, g in part.groupby(group):
            v=score(g); values.append(v)
            group_rows.append(dict(model=model,group=name,fold=int(g.fold.iloc[0]),samples=len(g),**v))
        macro=pd.DataFrame(values).mean()
        old=reported[reported.model==model]
        require(len(old)==1, f"Missing reported model: {model}")
        require(np.allclose(macro[["mae","rmse","r2"]],old.iloc[0][["mae","rmse","r2"]].astype(float),atol=1e-8), f"Published score mismatch: {model}")
        rows.append(dict(model=model,groups=part[group].nunique(),samples=len(part),folds=part.fold.nunique(),
                         macro_mae=macro.mae,macro_rmse=macro.rmse,macro_r2=macro.r2,
                         **{"pooled_"+k:v for k,v in score(part).items()}))
    return pd.DataFrame(rows).sort_values("macro_mae"), pd.DataFrame(group_rows)


def main():
    out=ROOT/"reports/thesis_audit";out.mkdir(parents=True,exist_ok=True)
    sdu=read("reports/features.csv"); bms=read("reports/bms/features.csv")
    folds=read("reports/split_assignments.csv").set_index("battery").test_fold
    require(folds.index.is_unique,"Duplicate physical battery assignments")
    generated=pd.Series(index=bms.vehicle.unique(),dtype=int)
    for fold,(train,test) in enumerate(GroupKFold(5).split(bms,groups=bms.vehicle),1):
        require(set(bms.vehicle.iloc[train]).isdisjoint(bms.vehicle.iloc[test]),"BMS train/test overlap")
        generated.loc[bms.vehicle.iloc[test].unique()]=fold
    preds=pd.concat([read(p) for p in ["reports/predictions.csv","reports/hybrid_predictions.csv","reports/boosting/predictions.csv"]],ignore_index=True)
    preds=preds.rename(columns={"actual_soh":"actual","predicted_soh":"predicted"})
    reported=pd.concat([read("reports/hybrid_comparison.csv"),read("reports/boosting/metrics_summary.csv")])
    sdu_scores,sdu_groups=audit(sdu,preds,"battery",["battery","phase","cycle"],"soh_pct",folds,reported)
    bp=read("reports/bms/predictions.csv").rename(columns={"reference_soh_pct":"actual","prediction":"predicted"})
    bms_scores,bms_groups=audit(bms,bp,"vehicle",["vehicle","session"],"reference_soh_pct",generated,read("reports/bms/metrics_summary.csv"))
    # Confirm nested boosting validation remains inside each outer training partition.
    split_path=ROOT/"reports/boosting/splits.json"
    for split in json.loads(split_path.read_text("utf-8")):
        fit,valid,test=[set(split[k]) for k in ["fit_batteries","validation_batteries","test_batteries"]]
        require(fit.isdisjoint(valid) and (fit|valid).isdisjoint(test),"Boosting nested group overlap")
        require(test==set(folds[folds==split["fold"]].index),"Boosting outer test mismatch")
        require(fit|valid==set(folds[folds!=split["fold"]].index),"Boosting outer training coverage mismatch")
    require(not set(SDU_FEATURES)&{"soh_pct","capacity_ah","battery"},"SDU label/ID in inputs")
    require(not set(BMS_FEATURES)&{"reference_soh_pct","reference_capacity_ah","tail_capacity_ah","vehicle","month","available_capacity","available_energy"},"BMS label/ID in inputs")
    for name,frame in [("sdu_summary",sdu_scores),("bms_summary",bms_scores),("sdu_by_battery",sdu_groups),("bms_by_vehicle",bms_groups)]:
        frame.to_csv(out/(name+".csv"),index=False)
    paired=[]
    for dataset,groups in [("SDU",sdu_groups),("BMS",bms_groups)]:
        pivot=groups.pivot(index="group",columns="model",values="mae")
        for name in pivot.columns:
            if name=="Random Forest":continue
            delta=(pivot[name]-pivot["Random Forest"]).dropna().to_numpy()
            rng=np.random.default_rng(42)
            boots=rng.choice(delta,size=(10000,len(delta)),replace=True).mean(axis=1)
            low,high=np.quantile(boots,[.025,.975])
            paired.append(dict(dataset=dataset,model=name,reference="Random Forest",groups=len(delta),
                               relative_mae_reduction_pct=float(-delta.mean()/pivot["Random Forest"].mean()*100),mean_mae_difference=float(delta.mean()),improved_groups=int((delta<0).sum()),
                               bootstrap_low=float(low),bootstrap_high=float(high)))
    paired=pd.DataFrame(paired);paired.to_csv(out/"paired_comparisons.csv",index=False)
    files=["reports/features.csv","reports/predictions.csv","reports/hybrid_predictions.csv","reports/boosting/predictions.csv","reports/split_assignments.csv","reports/bms/features.csv","reports/bms/predictions.csv","reports/boosting/splits.json","scripts/run_experiment.py","scripts/train_gru.py","scripts/evaluate_hybrid.py","scripts/evaluate_boosting.py","scripts/build_bms.py"]
    hashes={}
    for f in files:
        p=ROOT/f
        if not p.exists():p=p.with_suffix(".csv.gz")
        hashes[str(p.relative_to(ROOT)).replace(chr(92),"/")]=hashlib.sha256(p.read_bytes()).hexdigest()
    evidence=dict(status="passed",scope="Audit of saved out-of-fold predictions and training source; not a fresh model-training reproduction",checks=["Exact source sample coverage once per model","Source labels match saved predictions","Physical group test folds agree","Published macro metrics recomputed within 1e-8","Boosting fit/validation/test groups disjoint","Target and group ID excluded from declared inputs"],sha256=hashes,
                  limitations=["Saved prediction audit alone cannot prove how historical fitted weights were produced.","No independent BMS capacity measurement or fault labels.","Group CV does not establish future chronological performance.","Bootstrap intervals resample physical groups, are descriptive and do not correct for shared CV training or multiple model selection."])
    (out/"verification.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2),"utf-8")
    def table(frame):
        lines=["| Mô hình | MAE (điểm %) | RMSE (điểm %) | R² |","|---|---:|---:|---:|"]
        for r in frame.itertuples():lines.append(f"| {r.model} | {r.macro_mae:.4f} | {r.macro_rmse:.4f} | {r.macro_r2:.4f} |")
        return "\n".join(lines)
    best=sdu_scores.iloc[0];bestb=bms_scores.iloc[0]
    hybrid=paired[(paired.dataset=="SDU")&(paired.model=="Ridge-RF residual")].iloc[0]
    text=f"""# Kết quả kiểm chứng phục vụ khóa luận

## Phạm vi và cách tính

Đây là kiểm tra lại dự đoán ngoài tập huấn luyện đã lưu, không phải một lượt huấn luyện lại. Mỗi pin/xe chỉ thuộc một vòng kiểm thử; toàn bộ mẫu của cùng pin/xe được giữ cùng nhóm. SDU có {len(sdu):,} chu kỳ từ {sdu.battery.nunique()} pin; BMS có {len(bms):,} phiên từ {bms.vehicle.nunique()} xe. Cả hai dùng 5 vòng kiểm thử theo nhóm.

MAE và RMSE có đơn vị điểm phần trăm SOH: dự đoán 90 khi tham chiếu 92 là sai lệch 2 điểm %. R² không phải độ chính xác phân loại và không được đổi thành phần trăm pin tốt/hỏng. Bảng chính là trung bình chỉ số tính riêng trên mỗi pin/xe (macro); CSV cũng cung cấp chỉ số gộp tất cả mẫu (pooled), không trộn hai cách tính.

## SDU: dự đoán SOH trên pin giữ riêng

{table(sdu_scores)}

Mô hình có MAE macro thấp nhất trong các cấu hình đã thử là {best.model}: MAE {best.macro_mae:.4f}, RMSE {best.macro_rmse:.4f} điểm % và R² {best.macro_r2:.4f}. Kết quả này không phải xác suất dự đoán đúng của một pin cụ thể.

Ridge–RF so với Random Forest có chênh MAE trung bình {hybrid.mean_mae_difference:.6f} điểm %, cải thiện trên {hybrid.improved_groups}/{hybrid.groups} pin. Khoảng bootstrap mô tả 95% cho chênh trung bình là [{hybrid.bootstrap_low:.6f}; {hybrid.bootstrap_high:.6f}]. Không tuyên bố ưu thế chắc chắn khi khoảng chứa 0; cũng không khẳng định thuật toán mới hay tốt nhất phổ quát. Khoảng này không điều chỉnh phụ thuộc do tập huấn luyện CV dùng chung hoặc việc thử nhiều mô hình.

CatBoost/XGBoost có chọn siêu tham số bằng nhóm validation bên trong tập học; các baseline dùng cấu hình cố định, nên ngân sách tinh chỉnh chưa ngang nhau. GRU dùng biểu diễn chuỗi khác mô hình bảng; khác biệt không chỉ nằm ở thuật toán. Mô hình bàn giao học lại toàn bộ dữ liệu không dùng để tính bảng kiểm thử này.

## BMS: dự đoán trên xe giữ riêng

{table(bms_scores)}

{bestb.model} có MAE macro thấp nhất: {bestb.macro_mae:.4f} điểm %. SOH tham chiếu BMS được suy ra từ tích phân dòng điện và độ tăng SOC ở phần sau cửa sổ đầu sạc, tổng hợp theo xe–tháng. Đây là đánh giá độ khớp với nhãn suy ra, chưa phải xác nhận độ chai bằng phép đo dung lượng độc lập. Nhiều phiên cùng xe–tháng dùng chung nhãn, không được xem là các phép đo dung lượng độc lập. Không so trực tiếp MAE SDU với BMS để kết luận mô hình nào tốt hơn.

## Kiểm tra chống rò rỉ và giới hạn bằng chứng

Đã kiểm tra đủ mẫu, không lặp mẫu trong mỗi mô hình, nhãn tham chiếu khớp nguồn, đúng fold vật lý và bộ fit/validation/test boosting không giao nhau. Đặc trưng khai báo không chứa nhãn dung lượng, SOH hay mã pin/xe. Mã huấn luyện cho thấy scaler được fit trong tập học. Đây là kiểm tra tệp dự đoán và mã nguồn; chưa phải tái huấn luyện độc lập để chứng minh toàn bộ lịch sử thực thi. Hash của đầu vào và mã nằm trong verification.json.

Kiểm thử giữ riêng pin/xe đánh giá chuyển sang đối tượng khác, không chứng minh dự đoán tương lai theo thời gian. Tập kiểm thử đã được xem khi so sánh mô hình; nếu cần ước lượng không thiên lệch cho lựa chọn cuối cùng, cần một tập ngoài chưa dùng lựa chọn hoặc nested CV cho toàn bộ quy trình chọn mô hình.

## Đóng góp và cách trình bày khi bảo vệ

Đóng góp của đề tài là xây dựng quy trình trích xuất tín hiệu đầu sạc, so sánh mô hình trên cùng nhóm pin giữ riêng, triển khai giao diện dự đoán và bổ sung kiểm chứng trên dữ liệu vận hành xe riêng biệt. Không gọi phối hợp Ridge–RF là thuật toán mới phát minh. Không quy đổi kết quả thành phần trăm hoàn thành hay điểm khóa luận.

Có thể trình bày: “Trong các cấu hình đã khảo sát, {best.model} có MAE macro thấp nhất trên 86 pin SDU theo kiểm thử nhóm 5 vòng. BMS được đánh giá riêng trên 20 xe, với nhãn SOH suy ra từ vận hành; chưa mở rộng kết luận sang chẩn đoán pin hỏng hoặc xác nhận an toàn.”

## Phần cần hoàn thiện tiếp

Đối chiếu tiêu chí và biểu mẫu báo cáo của trường với giảng viên; bổ sung phép đo dung lượng độc lập nếu muốn xác nhận SOH BMS vật lý; dùng dữ liệu lỗi đã xác minh nếu mở rộng sang chẩn đoán hỏng. Chưa cần bổ sung nhãn tốt/hỏng cho mục tiêu hồi quy SOH hiện tại.

Chạy lại: `.venv/Scripts/python.exe scripts/audit_thesis_results.py`. Đầu ra nằm tại reports/thesis_audit; CSV giữ đầy đủ số lẻ, bảng Markdown làm tròn 4 chữ số.
"""
    (out/"ket_qua_va_gioi_han.md").write_text(text,"utf-8")
    print(sdu_scores.to_string(index=False));print(bms_scores.to_string(index=False));print("THESIS AUDIT PASSED")

if __name__=="__main__":main()
