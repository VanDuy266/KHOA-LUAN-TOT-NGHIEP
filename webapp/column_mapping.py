"""Explicit unit and column adapter; does not establish cross-domain validity."""
import io
import json
import numpy as np
import pandas as pd
from prediction import csv_chunks

ALIASES={
    "time":["time","Time","Test_Time(s)","Timestamp"],
    "terminal_voltage":["terminal_voltage","Voltage","Voltage_measured","Voltage(V)"],
    "terminal_current":["terminal_current","Current","Current_measured","Current(A)","I_pack"],
    "temperature":["temperature","Temperature","Temperature_measured","Aux_Temperature_1(C)"]}
SCALES={"time":{"s":1,"ms":.001,"min":60},"terminal_voltage":{"V":1,"mV":.001},"terminal_current":{"A":1,"mA":.001},"temperature":{"C":1,"K":1}}

def read_frame(raw, preview=False):
    reader=csv_chunks(raw)
    try:
        first=next(reader, pd.DataFrame())
        if preview:return first.head(5)
        parts=[first];count=len(first)
        for part in reader:
            count+=len(part)
            if count>100000:raise ValueError("Ánh xạ tối đa 100.000 dòng cho một đoạn xả.")
            parts.append(part)
        if count>100000:raise ValueError("Ánh xạ tối đa 100.000 dòng.")
        frame=pd.concat(parts,ignore_index=True)
        if frame.empty:raise ValueError("File không có dòng dữ liệu.")
        return frame
    finally:
        reader.close()

def preview(raw):
    frame=read_frame(raw,True)
    if frame.empty:raise ValueError("File không có dòng dữ liệu.")
    columns=frame.columns.tolist()
    suggestions={key:next((c for c in columns if str(c).casefold() in [a.casefold() for a in aliases]),"") for key,aliases in ALIASES.items()}
    return dict(columns=columns,preview=frame,suggestions=suggestions)

def normalize(raw, mapping, units, positive_discharge=False):
    if set(mapping)!=set(ALIASES) or set(units)!=set(ALIASES):raise ValueError("Cần chọn đủ bốn cột và đơn vị.")
    if not all(isinstance(v,str) for v in [*mapping.values(),*units.values()]):raise ValueError("Cột và đơn vị phải là tên hợp lệ.")
    if len(set(mapping.values()))!=4:raise ValueError("Mỗi tín hiệu cần một cột riêng.")
    frame=read_frame(raw)
    if not set(mapping.values())<=set(frame):raise ValueError("Cột được chọn không có trong file.")
    out=pd.DataFrame()
    for key,col in mapping.items():
        if units[key] not in SCALES[key]:raise ValueError("Đơn vị không được hỗ trợ.")
        out[key]=pd.to_numeric(frame[col],errors="raise")*SCALES[key][units[key]]
    if units["temperature"]=="K":out["temperature"]-=273.15
    if positive_discharge:out["terminal_current"]*=-1
    if not np.isfinite(out.to_numpy()).all():raise ValueError("Tín hiệu có giá trị thiếu hoặc vô hạn.")
    if (out.time<0).any() or out.time.duplicated().any() or not out.time.is_monotonic_increasing:
        raise ValueError("Một đoạn xả cần thời gian không âm, tăng dần và không trùng.")
    # Relative time retains the beginning of the supplied segment; user must supply start-of-discharge.
    out["time"]-=out.time.iloc[0]
    return out
