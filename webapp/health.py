"""Experimental OLS trend-to-threshold, not fault or safety prediction."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


def history_frame(frame):
    if not {"position","soh_pct"} <= set(frame):
        raise ValueError("CSV cần cột position (chu kỳ/tháng) và soh_pct; tùy chọn soc_pct.")
    if not 5 <= len(frame) <= 2000:
        raise ValueError("Cần từ 5 đến 2000 mốc lịch sử của cùng một pin và một giai đoạn.")
    cols=["position","soh_pct"]+(["soc_pct"] if "soc_pct" in frame else [])
    data=frame[cols].apply(pd.to_numeric,errors="raise").sort_values("position")
    if not np.isfinite(data.to_numpy()).all() or data.position.duplicated().any() or (data.position<0).any():
        raise ValueError("Mốc phải không âm, không trùng; dữ liệu phải hữu hạn.")
    if not data.soh_pct.between(0,130).all() or ("soc_pct" in data and not data.soc_pct.between(0,100).all()):
        raise ValueError("SOH cần trong 0–130%, SOC trong 0–100%.")
    return data.reset_index(drop=True)


def trend_forecast(frame,threshold=80):
    data=history_frame(frame)
    if not np.isfinite(threshold) or not 0 < threshold < 100:
        raise ValueError("Ngưỡng SOH cần lớn hơn 0 và nhỏ hơn 100%.")
    recent=data.tail(20);x=recent.position.to_numpy();y=recent.soh_pct.to_numpy()
    model=LinearRegression().fit((x-x[-1]).reshape(-1,1),y)
    slope=float(model.coef_[0]);fit=model.predict((x-x[-1]).reshape(-1,1))
    current=float(y[-1]);level=float(model.predict([[0]])[0]);span=float(x[-1]-x[0])
    result=dict(soh_pct=current,loss_pct=100-current if current<=100 else None,
                soc_pct=float(data.soc_pct.iloc[-1]) if "soc_pct" in data else None,
                threshold=threshold,current_position=float(x[-1]),samples=len(data),fit_samples=len(recent),
                slope=slope,fit_r2=float(r2_score(y,fit)),remaining=None,crossing=None,
                fault_status="Chưa xác định lỗi: lịch sử SOH không chứa bằng chứng chẩn đoán.",
                method="Hồi quy tuyến tính OLS trên tối đa 20 mốc gần nhất; ngoại suy tối đa 3 lần khoảng lịch sử fit.",
                points=data[["position","soh_pct"]].to_dict("records"),forecast=[])
    if current<=threshold:
        result.update(status="reached",message="SOH đã bằng hoặc thấp hơn ngưỡng bạn chọn; không đồng nghĩa pin hỏng.",remaining=0.,crossing=float(x[-1]))
    elif slope>=-1e-6 or result["fit_r2"]<.3 or level<=threshold:
        result.update(status="insufficient_trend",message="Xu hướng giảm chưa rõ hoặc đường fit không phù hợp; chưa ước tính thời điểm xuống ngưỡng.")
    else:
        remaining=(threshold-level)/slope
        if remaining>3*span:
            result.update(status="beyond_horizon",message="Ngưỡng nằm quá xa so với lịch sử quan sát; chưa đưa số chu kỳ/tháng còn lại.")
        else:
            result.update(status="estimated",message="Ước tính thời điểm xuống ngưỡng dung lượng nếu xu hướng hiện tại tiếp diễn; không dự báo sự cố hỏng.",remaining=float(remaining),crossing=float(x[-1]+remaining))
            future=np.linspace(x[-1],x[-1]+remaining,30)
            result["forecast"]=[dict(position=float(t),soh_pct=float(level+slope*(t-x[-1]))) for t in future]
    return result
