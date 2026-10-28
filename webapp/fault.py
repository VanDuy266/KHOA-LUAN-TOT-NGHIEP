"""Feature extraction for released 50x14 millivolt snapshots, not BAIC telemetry."""
import numpy as np
import pandas as pd
FEATURES=['residual_mean','residual_std','residual_min','residual_max','residual_range','residual_slope','residual_change','voltage_mean','voltage_range']

def snapshot_features(frame):
    values=frame.apply(pd.to_numeric,errors="raise").to_numpy(dtype=float)
    if values.shape!=(50,14) or not np.isfinite(values).all() or not ((values>=0)&(values<=6000)).all():
        raise ValueError("Cần đúng 50 hàng × 14 cột điện áp cell, đơn vị mV, hữu hạn trong 0–6000; không có cột nhãn.")
    if values.max()<=6:raise ValueError("Dữ liệu có vẻ dùng V; cần mV đúng định dạng nguồn.")
    residual=values-np.median(values,axis=1,keepdims=True)
    t=np.arange(50,dtype=float);t-=t.mean()
    x=np.stack([residual.mean(axis=0),residual.std(axis=0),residual.min(axis=0),residual.max(axis=0),np.ptp(residual,axis=0),t@residual/(t@t),np.abs(np.diff(residual,axis=0)).mean(axis=0),values.mean(axis=0),np.ptp(values,axis=0)],axis=1)
    return pd.DataFrame(x,columns=FEATURES)
