"""Explicit unit and column adapter; does not establish cross-domain validity."""
import io
import json
import re
import unicodedata
import numpy as np
import pandas as pd
from prediction import csv_chunks

ALIASES={
    "time":["time","Time","Test_Time(s)","Timestamp","Thời gian","Thời gian (s)","Thời gian (giây)","Thời gian (ms)","Thời gian (phút)","time_ms","time_min","Time(ms)","Time(min)"],
    "terminal_voltage":["terminal_voltage","Voltage","Voltage_measured","Voltage(V)","Voltage(mV)","voltage_mv","Điện áp","Điện áp (V)","Điện áp (mV)"],
    "terminal_current":["terminal_current","Current","Current_measured","Current(A)","Current(mA)","current_ma","I_pack","Dòng điện","Dòng điện (A)","Dòng điện (mA)"],
    "temperature":["temperature","Temperature","Temperature_measured","Aux_Temperature_1(C)","Temperature(C)","Temperature(K)","temperature_k","Nhiệt độ","Nhiệt độ (C)","Nhiệt độ (°C)","Nhiệt độ (K)"]}


def column_key(value):
    value=unicodedata.normalize("NFD",str(value).casefold().replace("đ","d"))
    return re.sub(r"[^a-z0-9]+","", "".join(c for c in value if not unicodedata.combining(c)))


def suggested_unit(signal, column):
    name=column_key(column)
    if signal=="time":
        if name.endswith("ms"):return "ms"
        if name.endswith(("min","phut")):return "min"
        return "s"
    if signal=="terminal_voltage":return "mV" if name.endswith("mv") else "V"
    if signal=="terminal_current":return "mA" if name.endswith("ma") else "A"
    return "K" if name.endswith("k") else "C"


CONTEXT_ALIASES={"battery":["battery","battery_id","Mã pin","Ma pin"],
                 "cycle":["cycle","cycle_index","Chu kỳ","Chu ky"],
                 "phase":["phase","phase_code","Giai đoạn","Giai doan"]}

BMS_COLUMNS=['time_s','soc','pack_voltage','charge_current','max_cell_voltage','min_cell_voltage','max_temperature','min_temperature']
STEP_ALIASES=['step','step_index','step_id','Bước đo','Buoc do']
BMS_CONTEXT_ALIASES={'battery':['vehicle','vehicle_id','Mã xe','Ma xe','battery','battery_id'],
                     'cycle':['session','session_id','Phiên sạc','Phien sac'], 'phase':[]}


def filter_candidates(columns, task='signals'):
    aliases=dict(BMS_CONTEXT_ALIASES if task=='bms' else CONTEXT_ALIASES)
    aliases['step']=[] if task=='bms' else STEP_ALIASES
    return {key:[c for c in columns if column_key(c) in {column_key(a) for a in names}] for key,names in aliases.items()}


def validate_filter_column(key, column, columns, task='signals'):
    if not column:return
    if column not in filter_candidates(columns,task).get(key,[]):
        if key=='cycle' and column_key(column) in {column_key(a) for a in STEP_ALIASES}:
            raise ValueError(f'{column} là bước đo, không phải chu kỳ. Dùng bộ lọc Bước đo; chu kỳ dùng Cycle_Index hoặc cycle.')
        label={'battery':'mã pin/xe','cycle':'phiên sạc' if task=='bms' else 'chu kỳ','phase':'giai đoạn sử dụng','step':'bước đo'}.get(key,key)
        candidates=filter_candidates(columns,task).get(key,[])
        expected=('Cột phù hợp: '+', '.join(candidates)+'.') if candidates else ('Tệp không có cột '+label+'; bỏ bộ lọc này.')
        raise ValueError(f'Cột {column} không phải cột {label}. '+expected)


SCALES={"time":{"s":1,"ms":.001,"min":60},"terminal_voltage":{"V":1,"mV":.001},"terminal_current":{"A":1,"mA":.001},"temperature":{"C":1,"K":1}}

def read_frame(raw, preview=False):
    if raw.removeprefix(b'\xef\xbb\xbf').lstrip().startswith((b'[',b'{')):
        try:records=json.loads(raw.decode('utf-8-sig'))
        except (ValueError,UnicodeError):raise ValueError("JSON không hợp lệ.")
        if not isinstance(records,list) or not records or not all(isinstance(r,dict) for r in records):raise ValueError("JSON cần mảng các bản ghi phẳng có tên cột.")
        if len(records)>100000:raise ValueError("Tối đa 100.000 bản ghi.")
        if any(isinstance(v,(dict,list)) for r in records for v in r.values()):raise ValueError("JSON lồng nhau chưa được hỗ trợ.")
        frame=pd.DataFrame(records)
        return frame.head(5) if preview else frame
    reader=csv_chunks(raw)
    try:
        first=next(reader, pd.DataFrame())
        if preview:return first.head(5)
        parts=[first];count=len(first)
        for part in reader:
            count+=len(part)
            if count>100000:raise ValueError("Ánh xạ tối đa 100.000 dòng cho một đoạn đo.")
            parts.append(part)
        if count>100000:raise ValueError("Ánh xạ tối đa 100.000 dòng.")
        frame=pd.concat(parts,ignore_index=True)
        if frame.empty:raise ValueError("File không có dòng dữ liệu.")
        return frame
    finally:
        reader.close()

def preview(raw):
    return preview_frame(read_frame(raw,True))


def preview_frame(frame):
    if frame.empty:raise ValueError("File không có dòng dữ liệu.")
    columns=frame.columns.tolist()
    candidates={key:[c for c in columns if column_key(c) in [column_key(a) for a in aliases]] for key,aliases in ALIASES.items()}
    suggestions={key:matches[0] if len(matches)==1 else "" for key,matches in candidates.items()}
    context_columns={key:next((c for c in columns if column_key(c) in [column_key(a) for a in aliases]),"") for key,aliases in CONTEXT_ALIASES.items()}
    context_values={key:str(frame[col].iloc[0]) for key,col in context_columns.items() if col and frame[col].nunique(dropna=False)==1 and frame[col].notna().all()}
    groups=filter_candidates(columns)
    bms_groups=filter_candidates(columns,'bms')
    filter_columns={column for group in [*groups.values(),*bms_groups.values()] for column in group}
    return dict(columns=columns,preview=frame,suggestions=suggestions,context_columns=context_columns,context_values=context_values,
                suggested_units={key:suggested_unit(key,col) for key,col in suggestions.items()},
                filter_candidates=groups,bms_filter_candidates=bms_groups,
                filter_values={c:[str(v) for v in frame[c].dropna().unique()[:20]] for c in columns if c in filter_columns},
                bms_missing=[name for name in BMS_COLUMNS if name not in columns])

def normalize(raw, mapping, units, positive_discharge=False):
    return normalize_frame(read_frame(raw),mapping,units,positive_discharge)


def normalize_frame(frame, mapping, units, positive_discharge=False):
    if set(mapping)!=set(ALIASES) or set(units)!=set(ALIASES):raise ValueError("Cần chọn đủ bốn cột và đơn vị.")
    if not all(isinstance(v,str) for v in [*mapping.values(),*units.values()]):raise ValueError("Cột và đơn vị phải là tên hợp lệ.")
    if len(set(mapping.values()))!=4:raise ValueError("Mỗi tín hiệu cần một cột riêng.")
    if not set(mapping.values())<=set(frame):raise ValueError("Cột được chọn không có trong file.")
    out=pd.DataFrame()
    for key,col in mapping.items():
        if units[key] not in SCALES[key]:raise ValueError("Đơn vị không được hỗ trợ.")
        try:out[key]=pd.to_numeric(frame[col],errors="raise")*SCALES[key][units[key]]
        except (ValueError,TypeError):raise ValueError(f"Cột {col} cần giá trị số; chuyển timestamp thành thời gian số trước khi tải.")
    if units["temperature"]=="K":out["temperature"]-=273.15
    if positive_discharge:out["terminal_current"]*=-1
    if not np.isfinite(out.to_numpy()).all():raise ValueError("Tín hiệu có giá trị thiếu hoặc vô hạn.")
    if (out.time<0).any() or out.time.duplicated().any() or not out.time.is_monotonic_increasing:
        raise ValueError("Một đoạn đo cần thời gian không âm, tăng dần và không trùng.")
    # Relative time retains the beginning of the supplied segment; user must supply start-of-discharge.
    out["time"]-=out.time.iloc[0]
    return out
