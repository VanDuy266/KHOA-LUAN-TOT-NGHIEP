import io
import json

import numpy as np
import pandas as pd
import pytest

from webapp.server import app
from battery_soh.features import FEATURES
from webapp.training import run
from webapp.custom_model import predict_portable, extract_features, domain_profile
from webapp.data import table

DOMAIN=dict(chemistry='NMC',level='cell',mode='discharge',nominal_ah=2.4,protocol='V/A/°C, thống kê 120 giây đầu theo cùng quy trình đo')


@pytest.fixture(scope='module')
def trained():
    data=table('reports/features.csv')
    pins=sorted(data.battery.unique())[:8]
    data=data[data.battery.isin(pins)].groupby(['battery','phase'],group_keys=False).head(8)[['battery',*FEATURES,'soh_pct']]
    raw=data.to_csv(index=False).encode()
    result=run(raw,label_source='Independent capacity test / nominal',domain=DOMAIN)
    return data,result


def test_portable_model_matches_trained_ridge_and_heldout_rows(trained):
    data,result=trained
    model=result['portable_ridge']
    held=data[data.battery.isin(result['test_batteries'])]
    prediction=predict_portable(model,held.drop(columns='soh_pct').to_csv(index=False).encode(),DOMAIN)
    expected=pd.DataFrame([p for p in result['predictions'] if p['model']=='Ridge']).sort_values(['battery','phase_code','cycle'])
    actual=pd.DataFrame(prediction['results']).sort_values(['battery','phase_code','cycle'])
    np.testing.assert_allclose(actual.predicted_soh_pct,expected.predicted_soh,rtol=1e-12)
    assert not actual.seen_in_training.any()
    assert set(model['train_batteries']).isdisjoint(model['test_batteries'])
    assert len(prediction['input_sha256'])==64


def test_new_inputs_change_predictions_without_any_saved_output_lookup(trained):
    data,result=trained
    frame=data.head(1).drop(columns='soh_pct').copy()
    first=predict_portable(result['portable_ridge'],frame.to_csv(index=False).encode(),DOMAIN)
    frame['voltage_mean']+=.02
    second=predict_portable(result['portable_ridge'],frame.to_csv(index=False).encode(),DOMAIN)
    assert first['input_sha256']!=second['input_sha256']
    assert first['results'][0]['predicted_soh_pct']!=second['results'][0]['predicted_soh_pct']


@pytest.mark.parametrize('case',['wrong_domain','bad_scale','bad_shape','nan_coef','wrong_features'])
def test_invalid_portable_models_or_domains_are_rejected(trained,case):
    data,result=trained
    model=json.loads(json.dumps(result['portable_ridge']))
    domain=dict(DOMAIN)
    if case=='wrong_domain':domain['chemistry']='LFP'
    elif case=='bad_scale':model['scale'][0]=0
    elif case=='bad_shape':model['mean'].pop()
    elif case=='nan_coef':model['coefficients'][0]=float('nan')
    else:model['features']=['soh_pct']
    with pytest.raises(ValueError):predict_portable(model,data.head(1).to_csv(index=False).encode(),domain)


def test_routes_do_not_deserialize_executable_models(trained):
    data,result=trained
    client=app.test_client()
    response=client.post('/api/custom/predict',data={'model_file':(io.BytesIO(json.dumps(result['portable_ridge']).encode()),'ridge.json'),
        'file':(io.BytesIO(data.head(3).drop(columns='soh_pct').to_csv(index=False).encode()),'new.csv'),'domain_profile':json.dumps(DOMAIN)})
    assert response.status_code==200,response.json
    assert len(response.json['results'])==3
    response=client.post('/api/custom/predict',data={'model_file':(io.BytesIO(b'not a safe model'),'model.joblib')})
    assert response.status_code==400


def test_feature_extraction_uses_uploaded_signals_and_keeps_labels_separate():
    rows=[]
    for battery in ['A','B']:
        for cycle in [1,2]:
            for time in range(0,121,10):
                rows.append(dict(battery=battery,cycle=cycle,phase_code=0,time=time,terminal_voltage=4.1-.001*time,
                                 terminal_current=-2,temperature=25+.01*time,soh_pct=90-cycle))
    data=pd.DataFrame(rows)
    result=extract_features(data.to_csv(index=False).encode())
    assert len(result['rows'])==4 and result['has_labels']
    assert result['rows'][0]['voltage_slope']==pytest.approx(-.001)
    assert result['rows'][0]['soh_pct']==89
    data['soh_pct']=70
    changed=extract_features(data.to_csv(index=False).encode())
    assert all(changed['rows'][0][feature]==result['rows'][0][feature] for feature in FEATURES)
    data.loc[1,'time']=0
    with pytest.raises(ValueError):extract_features(data.to_csv(index=False).encode())


def test_training_route_exports_profile_bound_model(trained):
    data,_=trained
    response=app.test_client().post('/api/training',data={'file':(io.BytesIO(data.to_csv(index=False).encode()),'own.csv'),
            'label_source':'Capacity measured independently','domain_profile':json.dumps(DOMAIN)})
    assert response.status_code==200,response.json
    assert response.json['portable_ridge']['domain']==domain_profile(DOMAIN)
