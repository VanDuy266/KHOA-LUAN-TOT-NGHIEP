"""Profile-aware measured-signal analysis, independent of SDU inference."""
import numpy as np
from scipy.integrate import trapezoid

def analyze(frame, profile, soc=None):
    if not isinstance(profile,dict):raise ValueError("Hồ sơ pin không hợp lệ.")
    chemistry=profile.get('chemistry','unknown');level=profile.get('level','unknown');mode=profile.get('mode','unknown')
    if not all(isinstance(x,str) for x in [chemistry,level,mode]):raise ValueError("Thông tin cấu hình cần là tên hợp lệ.")
    if chemistry not in {'NMC','LFP','LCO','NCA','LTO','other','unknown'} or level not in {'cell','pack','unknown'} or mode not in {'charge','discharge','mixed','unknown'}:
        raise ValueError("Thông tin cấu hình không hợp lệ.")
    nominal=profile.get('nominal_ah')
    if nominal not in (None,''):
        try:nominal=float(nominal)
        except (ValueError,TypeError):raise ValueError("Dung lượng định mức cần là số Ah.")
        if not np.isfinite(nominal) or nominal<=0:raise ValueError("Dung lượng định mức phải hữu hạn và lớn hơn 0.")
    else:nominal=None
    if len(frame)<2:raise ValueError("Cần ít nhất hai điểm đo để phân tích.")
    t=frame.time.to_numpy();v=frame.terminal_voltage.to_numpy();i=frame.terminal_current.to_numpy();temp=frame.temperature.to_numpy()
    if (v<=0).any() or not ((temp>=-80)&(temp<=150)).all():raise ValueError("Kiểm tra lại điện áp hoặc đơn vị nhiệt độ.")
    warnings=[]
    gap=float(np.diff(t).max());continuous=gap<=60
    if not continuous:warnings.append("Khoảng cách đo vượt 60 giây: không tính điện lượng từ đoạn này.")
    if level=='cell' and v.max()>5:warnings.append("Điện áp cao so với một cell: kiểm tra dữ liệu bộ pin hoặc đơn vị.")
    if mode=='discharge' and (i>.1).any():warnings.append("Có dòng sạc trong đoạn khai báo xả.")
    if mode=='charge' and (i<-.1).any():warnings.append("Có dòng xả trong đoạn khai báo sạc.")
    last_soc=None
    if soc is not None:
        a=np.asarray(soc,dtype=float)
        if len(a)!=len(frame) or not np.isfinite(a).all() or (a<0).any() or (a>100).any():raise ValueError("SOC phải cùng số dòng và trong 0–100%.")
        last_soc=float(a[-1])
    return dict(profile=dict(chemistry=chemistry,level=level,mode=mode,nominal_ah=nominal),rows=len(frame),duration_seconds=float(t[-1]-t[0]),
        voltage_min=float(v.min()),voltage_max=float(v.max()),temperature_min=float(temp.min()),temperature_max=float(temp.max()),
        charged_ah=float(trapezoid(np.maximum(i,0),t)/3600) if continuous else None,
        discharged_ah=float(trapezoid(np.maximum(-i,0),t)/3600) if continuous else None,
        soc_pct=last_soc,soh_pct=None,loss_pct=None,warnings=warnings,
        inference_status="Cần mô hình đã kiểm chứng cho cấu hình này; không suy SOH từ điện lượng của đoạn đo.",
        fault_status="Dữ liệu đo chưa kèm mô hình chẩn đoán phù hợp hoặc kết quả kiểm tra xác nhận.")
