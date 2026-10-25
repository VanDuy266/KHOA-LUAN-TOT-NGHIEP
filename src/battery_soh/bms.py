"""Field BMS charging features. Pack signals stay separate from the SDU model."""
import numpy as np

FEATURES = ['soc_start', 'pack_voltage_mean', 'pack_voltage_std', 'pack_voltage_slope',
            'cell_voltage_max_mean', 'cell_voltage_min_mean', 'cell_voltage_spread_mean',
            'charge_current_mean', 'charge_current_std', 'temperature_max_mean',
            'temperature_min_mean', 'temperature_max_slope']
NOMINAL_AH = 145.0

def charging_features(frame):
    """Use observed signals in the first 120 seconds only; no capacity fields."""
    frame = frame[frame.time_s.between(0, 120)].copy()
    if len(frame) < 12 or frame.time_s.iloc[-1] < 112:
        raise ValueError("Incomplete first 120 seconds")
    t = frame.time_s.to_numpy(dtype=float)
    def slope(values):
        centered = t-t.mean()
        return float(np.dot(centered, values-values.mean()) / np.dot(centered,centered))
    return dict(zip(FEATURES, [
        float(frame.soc.iloc[0]), frame.pack_voltage.mean(), frame.pack_voltage.std(ddof=0), slope(frame.pack_voltage),
        frame.max_cell_voltage.mean(), frame.min_cell_voltage.mean(),
        (frame.max_cell_voltage-frame.min_cell_voltage).mean(), -frame.charge_current.mean(),
        frame.charge_current.std(ddof=0), frame.max_temperature.mean(), frame.min_temperature.mean(),
        slope(frame.max_temperature)]))

def tail_capacity(frame):
    """Field-derived reference from AFTER the feature window, not a laboratory RPT."""
    tail=frame[frame.time_s > 120]
    if len(tail)<100:
        raise ValueError('Too few measurements after the feature window')
    gain=float(tail.soc.iloc[-1]-tail.soc.iloc[0])
    if gain<20:
        raise ValueError('SOC increase below 20 percentage points after 120 seconds')
    return float(np.trapezoid(-tail.charge_current,tail.time_s)/3600/(gain/100))
