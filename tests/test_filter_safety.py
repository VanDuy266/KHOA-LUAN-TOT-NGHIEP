"""Regression for Step_Index/Voltage(V) incorrectly offered as group filters."""
import io
import json
from unittest.mock import patch

import pandas as pd
import pytest
from webapp.server import app
from webapp.column_mapping import preview_frame
from webapp.upload_table import read_upload
from werkzeug.datastructures import FileStorage

RAW=b'Cycle_Index,Step_Index,Voltage(V),Current(A),Test_Time(s),Aux_Temperature_1(C)\n1,1,4.1,-2,0,25\n1,1,4.0,-2,60,25\n1,1,3.9,-2,120,25\n1,2,3.8,0,121,25\n1,2,3.8,0,180,25\n'
PROFILE=dict(battery_id='PIN-A',measured_at='2026-11-13',origin='other',chemistry='unknown',level='unknown',mode='unknown',nominal_ah=None)
MAPPING=dict(time='Test_Time(s)',terminal_voltage='Voltage(V)',terminal_current='Current(A)',temperature='Aux_Temperature_1(C)')
UNITS=dict(time='s',terminal_voltage='V',terminal_current='A',temperature='C')


def request_data(**updates):
    data=dict(task='signals',profile=json.dumps(PROFILE),file=(io.BytesIO(RAW),'lab.csv'),mapping=json.dumps(MAPPING),units=json.dumps(UNITS))
    data.update(updates)
    return data


def test_preview_distinguishes_cycle_and_step_and_never_offers_voltage_as_phase():
    result=preview_frame(pd.read_csv(io.BytesIO(RAW)))
    assert result['filter_candidates']['cycle']==['Cycle_Index']
    assert result['filter_candidates']['step']==['Step_Index']
    assert result['filter_candidates']['phase']==[]
    assert 'Voltage(V)' not in sum(result['filter_candidates'].values(),[])
    assert result['bms_missing']


@pytest.mark.parametrize('key,column',[('cycle','Step_Index'),('phase','Voltage(V)'),('phase','Step_Index'),('battery','Voltage(V)')])
def test_wrong_group_column_is_rejected_before_filtering_or_model_inference(key,column):
    with patch('webapp.server.artifact',side_effect=AssertionError('invalid filter called model')):
        response=app.test_client().post('/api/assessment',data=request_data(**{'filter_'+key+'_column':column,'filter_'+key+'_value':'1'}))
    assert response.status_code==400,response.json
    assert column in response.json['error']
    assert 'Không có dòng khớp' not in response.json['error']


def test_baic_mode_rejects_lab_structure_before_trying_wrong_filters():
    profile=dict(PROFILE,origin='BAIC EU500',chemistry='NMC',level='pack',mode='charge',nominal_ah=145)
    with patch('webapp.server.artifact',side_effect=AssertionError('wrong schema called model')):
        response=app.test_client().post('/api/assessment',data=request_data(task='bms',profile=json.dumps(profile),confirmed='1',filter_cycle_column='Step_Index',filter_cycle_value='1',filter_phase_column='Voltage(V)',filter_phase_value='1'))
    assert response.status_code==400,response.json
    assert 'không đúng cấu trúc BMS BAIC' in response.json['error']
    assert 'time_s' in response.json['error']


def test_valid_cycle_and_step_filters_use_real_rows():
    response=app.test_client().post('/api/assessment',data=request_data(filter_cycle_column='Cycle_Index',filter_cycle_value='1',filter_step_column='Step_Index',filter_step_value='1'))
    assert response.status_code==200,response.json
    record=response.json['record']
    assert record['rows']==3
    assert record['results'][0]['soh_pct'] is None
    assert record['mapping']['filters']=={'Cycle_Index':'1','Step_Index':'1'}


def test_empty_filter_explains_selection_and_actual_values_csv():
    response=app.test_client().post('/api/assessment',data=request_data(filter_cycle_column='Cycle_Index',filter_cycle_value='1',filter_step_column='Step_Index',filter_step_value='99'))
    assert response.status_code==400,response.json
    message=response.json['error']
    assert 'Step_Index: 99' in message
    assert 'Một số giá trị quan sát' in message
    assert 'Step_Index: 1, 2' in message


def test_empty_filter_explains_selection_and_actual_values_json():
    upload=FileStorage(stream=io.BytesIO(b'[{"cycle":1,"time":0},{"cycle":2,"time":1}]'),filename='data.json')
    with pytest.raises(ValueError,match='cycle: 99'):
        read_upload(upload,filters={'cycle':'99'})


def test_legacy_mapping_cannot_treat_voltage_as_phase():
    data=request_data(filter_phase_column='Voltage(V)',filter_phase_value='1')
    response=app.test_client().post('/api/column-mapping/normalize',data=data)
    assert response.status_code==400,response.json
    assert 'không phải cột giai đoạn' in response.json['error']


def test_bms_filters_vehicle_and_charge_session_with_matching_schema():
    from webapp.data import table
    first=table('data/bms/processed/01_example.csv.gz').copy()
    first['vehicle']='CAR-A';first['session']=1
    second=first.copy();second['session']=2
    raw=pd.concat([first,second],ignore_index=True).to_csv(index=False).encode()
    profile=dict(PROFILE,origin='BAIC EU500',chemistry='NMC',level='pack',mode='charge',nominal_ah=145)
    response=app.test_client().post('/api/assessment',data=dict(task='bms',profile=json.dumps(profile),confirmed='1',
        file=(io.BytesIO(raw),'bms.csv'),filter_battery_column='vehicle',filter_battery_value='CAR-A',filter_cycle_column='session',filter_cycle_value='2'))
    assert response.status_code==200,response.json
    record=response.json['record']
    assert record['rows']==len(first)
    assert record['filters']=={'vehicle':'CAR-A','session':'2'}
    assert record['results'][0]['soh_pct'] is not None


def test_raw_sdu_uses_first_discharge_instead_of_charging_prefix():
    import numpy as np
    from prediction import read_csv
    from battery_soh.features import extract_window,FEATURES
    from webapp.data import artifact
    records=[]
    for time in range(0,101,20):
        records.append({'Battery_ID':1,'Cycle_Index':1,'Step_Index':1,'Test_Time(s)':time,'Voltage(V)':4.2,'Current(A)':2.,'Aux_Temperature_1(C)':25.})
    for time in range(200,321,10):
        records.append({'Battery_ID':1,'Cycle_Index':1,'Step_Index':2,'Test_Time(s)':time,'Voltage(V)':4.1-(time-200)*.001,'Current(A)':-2.,'Aux_Temperature_1(C)':25.})
    raw=pd.DataFrame(records).to_csv(index=False).encode()
    profile=dict(PROFILE,origin='SDU',chemistry='NMC',level='cell',mode='discharge',nominal_ah=2.4)
    response=app.test_client().post('/api/assessment',data=request_data(task='sdu',profile=json.dumps(profile),confirmed='1',file=(io.BytesIO(raw),'sdu.csv'),filter_cycle_column='Cycle_Index',filter_cycle_value='1'))
    assert response.status_code==200,response.json
    record=response.json['record']
    assert record['window']['method']=='first_discharge'
    assert record['signals'][0]['time']==0 and record['signals'][-1]['time']==120
    assert all(r['terminal_current']<0 for r in record['signals'])
    expected_frame=read_csv(raw,phase_code=0)
    expected=float(artifact('random_forest.joblib')['model'].predict(pd.DataFrame([extract_window(expected_frame,1)])[FEATURES])[0])
    assert np.isclose(record['results'][0]['soh_pct'],expected)


def test_known_raw_sdu_cannot_reverse_charging_into_discharge():
    profile=dict(PROFILE,origin='SDU',chemistry='NMC',level='cell',mode='discharge',nominal_ah=2.4)
    response=app.test_client().post('/api/assessment',data=request_data(task='sdu',profile=json.dumps(profile),confirmed='1',positive_discharge='1'))
    assert response.status_code==400,response.json
    assert 'quy ước dòng xả âm' in response.json['error']
