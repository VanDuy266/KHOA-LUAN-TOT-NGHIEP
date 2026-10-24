"""Đối chiếu miền đặc trưng và sai số theo điều kiện; không chọn lại tham số."""
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "src"))
from battery_soh.xjtu import normalized_features


def main():
    folder=ROOT / "reports/xjtu"
    data=pd.read_csv(folder / "features.csv")
    data=data.loc[data.cycle > 1]
    sdu=pd.read_csv(ROOT / "reports/features.csv")
    source=normalized_features(sdu,2.4); target=normalized_features(data,2)
    domain=[]
    for c in source.columns:
        outside=(target[c]<source[c].min()) | (target[c]>source[c].max())
        domain.append({"feature":c,"sdu_min":source[c].min(),"sdu_max":source[c].max(),
                       "xjtu_min":target[c].min(),"xjtu_max":target[c].max(),"outside_sdu_fraction":outside.mean()})
    pd.DataFrame(domain).to_csv(folder / "domain_shift.csv",index=False)
    pred=pd.read_csv(folder / "predictions.csv")
    pred=pred.merge(data[["battery","cycle","current_mean","temperature_mean"]],on=["battery","cycle"],validate="many_to_one")
    errors=[]
    for (design,model,batch),part in pred.groupby(["design","model","batch"]):
        errors.append({"design":design,"model":model,"batch":batch,"cycles":len(part),
                       "mae":mean_absolute_error(part.actual_soh,part.predicted_soh),
                       "rmse":root_mean_squared_error(part.actual_soh,part.predicted_soh)})
    pd.DataFrame(errors).to_csv(folder / "errors_by_batch.csv",index=False)
    paired=pd.read_csv(folder / "paired_multi_source.csv").mae_multi_minus_single_pp.to_numpy()
    rng=np.random.default_rng(42)
    bootstrap=rng.choice(paired,size=(5000,len(paired)),replace=True).mean(axis=1)
    report={"comparison":"RF multi-source minus XJTU-only RF MAE; positive means worse",
            "paired_cells":len(paired),"mean_difference_pp":float(paired.mean()),
            "cell_bootstrap_95pct_interval_pp":np.quantile(bootstrap,[.025,.975]).tolist(),
            "interpretation":"Exploratory paired comparison on the same 23 held-out cells, not independent confirmation or correction for multiple comparisons.",
            "transfer_caution":"RF original SDU uses 12 raw features. RF normalized also removes phase_code; this comparison does not isolate the effect of current normalization.",
            "between_dataset_caution":"Do not interpret lower XJTU MAE than SDU MAE as improvement on an identical test set; sources and target ranges differ."}
    (folder / "analysis.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    held = pred[(pred.design == "XJTU held-out") & (pred.model == "Random Forest")]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, batch in zip(axes, [1, 2]):
        cells = held[held.batch == batch]
        battery = sorted(cells.battery.unique())[0]
        part = cells[cells.battery == battery].sort_values("cycle")
        ax.plot(part.cycle, part.actual_soh, label="Tham chiếu")
        ax.plot(part.cycle, part.predicted_soh, label="RF giữ riêng pin")
        ax.set(title=battery, xlabel="Chu kỳ", ylabel="SOH (%)")
        ax.legend(fontsize=8); ax.grid(alpha=.2)
    fig.tight_layout(); fig.savefig(folder / "held_out_predictions.png", dpi=170); plt.close(fig)
    print(pd.DataFrame(domain).sort_values('outside_sdu_fraction',ascending=False).head().to_string(index=False))


if __name__ == "__main__":main()
