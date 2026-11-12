import json
from unittest.mock import patch

import pytest
from webapp.server import app


@pytest.fixture
def client():
    return app.test_client()


def capacity_record(client, day="2026-11-01", measured=95):
    profile=dict(battery_id="OWN-001",measured_at=day,conditions="25°C, cùng thiết bị",chemistry="LFP",level="pack",mode="discharge",origin="other",nominal_ah=100)
    response=client.post('/api/assessment',data=dict(task="capacity",profile=json.dumps(profile),reference_ah="100",measured_ah=str(measured),comparable="1"))
    assert response.status_code==200,response.json
    return response.json['record']


def test_record_roundtrip_rebuilds_html_and_marks_unverified(client):
    record=capacity_record(client)
    record['report_html']='<script>untrusted()</script>'
    with patch('webapp.server.artifact',side_effect=AssertionError('Restore must not load models')):
        response=client.post('/api/assessment/restore',json=record)
    assert response.status_code==200,response.json
    item=response.json['items'][0]
    assert item['record']['restored'] and item['record']['results']==record['results']
    assert '<script>untrusted()' not in item['report_html']
    assert 'chưa xác minh' in item['record']['warnings'][0]


def test_backup_duplicate_ids_or_unsupported_version_are_rejected(client):
    record=capacity_record(client)
    for payload in [dict(format='vincent-assessments',version=2,records=[record]),
                    dict(format='vincent-assessments',version=1,records=[record,record])]:
        assert client.post('/api/assessment/restore',json=payload).status_code==400


@pytest.mark.parametrize('edit', ['bad_id','bad_loss','bad_explanation','nan','bad_chart','missing_profile'])
def test_malformed_record_cannot_break_history_or_reports(client,edit):
    record=capacity_record(client)
    if edit=='bad_id':record['id']='"><script>alert(1)</script>'
    elif edit=='bad_loss':record['results'][0]['loss_pct']=-90
    elif edit=='bad_explanation':record['explanation']={'evidence':{}}
    elif edit=='nan':record['results'][0]['soh_pct']=float('nan')
    elif edit=='bad_chart':record['signals']=[{'time':'bad'}]
    else:record.pop('profile')
    assert client.post('/api/assessment/restore',json=record).status_code==400


def test_trend_is_computed_from_calendar_measurements(client):
    records=[capacity_record(client,f'2026-11-0{i+1}',99-4*i) for i in range(5)]
    response=client.post('/api/assessment/trend',json={'records':records,'threshold':80})
    assert response.status_code==200,response.json
    data=response.json
    assert data['unit']=='days' and data['result']['status']=='estimated'
    assert data['result']['slope']==pytest.approx(-4)
    assert data['crossing_date'] and data['points'][0]['position']==0
    assert 'chưa xác minh' in data['scope']


@pytest.mark.parametrize('case',['too_few','mixed_battery','mixed_model','mixed_conditions','same_day'])
def test_history_comparability_is_enforced_on_server(client,case):
    records=[capacity_record(client,f'2026-11-0{i+1}',99-4*i) for i in range(5)]
    if case=='too_few':records.pop()
    elif case=='mixed_battery':records[-1]['profile']['battery_id']='OTHER'
    elif case=='mixed_model':records[-1]['task']='signals'
    elif case=='mixed_conditions':records[-1]['profile']['conditions']='Khác điều kiện'
    else:records[-1]['profile']['measured_at']=records[0]['profile']['measured_at']
    assert client.post('/api/assessment/trend',json={'records':records,'threshold':80}).status_code==400


def test_payload_size_is_bounded(client):
    response=client.post('/api/assessment/restore',data=' '* (5*1024*1024+1),content_type='application/json')
    assert response.status_code==400


@pytest.mark.parametrize("task",["sdu","bms","signals"])
def test_all_assessment_types_can_be_restored(client,task):
    record=client.post('/api/assessment',data=dict(task=task,sample="1",profile="{}")).json['record']
    response=client.post('/api/assessment/restore',json=record)
    assert response.status_code==200,response.json
    assert response.json['items'][0]['record']['results']==record['results']
