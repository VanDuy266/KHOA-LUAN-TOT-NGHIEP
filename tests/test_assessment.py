"""Exercise the complete record workflow and reject unsafe scope shortcuts."""
import io
import json
from unittest.mock import patch

import pandas as pd
import pytest

from webapp.server import app
from webapp.data import table


@pytest.fixture
def client():
    return app.test_client()


def profile(**updates):
    result = dict(battery_id="PIN-001", measured_at="2026-11-12", conditions="25°C · 2 A",
                  chemistry="NMC", level="cell", mode="discharge", origin="SDU", nominal_ah=2.4)
    result.update(updates)
    return json.dumps(result)


def upload_data(frame=None, **updates):
    if frame is None:
        frame = table("data/clean/sample_measurements.csv")
        frame = frame[(frame.battery == "SDU_01") & (frame.phase_code == 0) & (frame.cycle == 1) & (frame.time <= 120)].copy()
    data = dict(task="sdu", profile=profile(), confirmed="1", model="Random Forest",
                mapping=json.dumps({x:x for x in ["time","terminal_voltage","terminal_current","temperature"]}),
                units=json.dumps(dict(time="s",terminal_voltage="V",terminal_current="A",temperature="C")),
                file=(io.BytesIO(frame.to_csv(index=False).encode()), "measurements.csv"))
    data.update(updates)
    return data


@pytest.mark.parametrize("task", ["sdu", "bms", "signals"])
def test_sample_check_and_report(client, task):
    data = dict(task=task, sample="1", profile="{}")
    with patch("webapp.server.artifact", side_effect=AssertionError("check loaded a model")):
        response = client.post("/api/assessment/check", data=data)
    assert response.status_code == 200, response.json
    assert response.json["ready"]
    response = client.post("/api/assessment", data=data)
    assert response.status_code == 200, response.json
    record = response.json["record"]
    assert record["sample"] and len(record["source_sha256"]) == 64
    assert record["checks"] and record["app_version"]
    assert "In / Lưu PDF" in response.json["report_html"]
    assert record["signals"]
    if task == "signals":
        assert record["results"][0]["soh_pct"] is None
    else:
        assert 0 <= record["results"][0]["soh_pct"] <= 130
        assert len(record["model_sha256"]) == 64


@pytest.mark.parametrize("updates", [dict(origin="other"),dict(nominal_ah=145),dict(level="pack"),dict(chemistry="LFP"),dict(mode="charge")])
def test_wrong_scope_cannot_call_model(client, updates):
    with patch("webapp.server.artifact", side_effect=AssertionError("wrong scope reached model")):
        response = client.post("/api/assessment", data=dict(task="sdu",profile=profile(**updates),confirmed="1"))
    assert response.status_code == 400
    assert not response.json["preflight"]["scope"]["allowed"]


def test_valid_normalized_upload_and_model_provenance(client):
    response = client.post("/api/assessment", data=upload_data())
    assert response.status_code == 200, response.json
    record = response.json["record"]
    assert not record["sample"]
    assert record["results"][0]["cycle"] == 1
    assert record["mapping"]["units"]["time"] == "s"
    assert record["explanation"]["evidence"]["reconstruction_ok"]
    assert record["validation"]


def test_bad_window_is_blocked_before_inference(client):
    frame = pd.DataFrame(dict(time=[0,1,2],terminal_voltage=[4,4,4],terminal_current=[-2,-2,-2],temperature=[25,25,25]))
    with patch("webapp.server.artifact", side_effect=AssertionError("invalid window reached model")):
        response = client.post("/api/assessment", data=upload_data(frame))
    assert response.status_code == 400
    assert response.json["preflight"]["checks"][0]["status"] == "Không đạt"


def test_duplicate_time_and_multigroup_are_not_silently_combined(client):
    for frame in [pd.DataFrame(dict(time=[0,0],terminal_voltage=[4,4],terminal_current=[-2,-2],temperature=[25,25])),
                  pd.DataFrame(dict(time=[0,60,120,0,60,120],terminal_voltage=[4]*6,terminal_current=[-2]*6,temperature=[25]*6,battery=["A"]*3+["B"]*3))]:
        response=client.post("/api/assessment/check",data=upload_data(frame))
        assert response.status_code == 400


def test_scope_confirmation_is_required_for_user_file(client):
    response=client.post("/api/assessment/check",data=upload_data(confirmed="0"))
    assert response.status_code==200 and not response.json["ready"]


def test_capacity_measurement_and_escaped_report(client):
    data=dict(task="capacity",profile=profile(battery_id='<script>alert(1)</script>'),reference_ah="100",measured_ah="83",comparable="1")
    response=client.post("/api/assessment",data=data)
    assert response.status_code==200,response.json
    assert response.json["record"]["results"][0]["soh_pct"]==83
    assert "<script>alert(1)</script>" not in response.json["report_html"]
    assert "&lt;script&gt;" in response.json["report_html"]
    response=client.post("/api/assessment",data={**data,"comparable":"0"})
    assert response.status_code==400


@pytest.mark.parametrize("value", ["nan","inf","-1","0"])
def test_invalid_capacities_rejected(client,value):
    response=client.post("/api/assessment",data=dict(task="capacity",profile=profile(),reference_ah=value,measured_ah="83",comparable="1"))
    assert response.status_code==400


def test_above_reference_does_not_become_negative_loss(client):
    response=client.post("/api/assessment",data=dict(task="capacity",profile=profile(),reference_ah="100",measured_ah="105",comparable="1"))
    assert response.status_code==200
    assert response.json["record"]["results"][0]["loss_pct"] is None
    assert response.json["record"]["warnings"]


def test_bms_json_uses_prepared_frame_not_raw_csv_route(client):
    frame=table("data/bms/processed/01_example.csv.gz")
    data=dict(task="bms",profile=profile(origin="BAIC EU500",nominal_ah=145,mode="charge",level="pack"),confirmed="1",
              file=(io.BytesIO(frame.to_json(orient="records").encode()),"bms.json"))
    response=client.post("/api/assessment",data=data)
    assert response.status_code==200,response.json
    assert response.json["record"]["source_name"]=="bms.json"
    assert response.json["record"]["details"]["source"]["kind"]=="upload"


def test_service_and_frontend_assets(client):
    assert client.get("/").headers["Cache-Control"] == "no-cache"
    assert client.get("/api/readiness").json["ready"]
    assert client.get("/static/assessment.js").status_code==200
    assert client.get("/api/version").json["frontend"]==client.get("/api/readiness").json["frontend"]


@pytest.mark.parametrize("model", ["Random Forest", "Ridge-RF residual", "Ridge", "LightGBM", "CatBoost", "XGBoost"])
def test_every_available_sdu_model_has_validation_and_explanation(client, model):
    response=client.post("/api/assessment",data=dict(task="sdu",sample="1",profile="{}",model=model))
    assert response.status_code==200,response.json
    record=response.json["record"]
    assert record["validation"][0]["model"]==model
    assert record["explanation"]["evidence"]["reconstruction_ok"]
    assert "<svg" in response.json["report_html"]


def test_numeric_error_identifies_selected_data_rows(client):
    frame=pd.DataFrame(dict(time=[0,60,120],terminal_voltage=[4,None,3.5],terminal_current=[-2]*3,temperature=[25]*3))
    response=client.post("/api/assessment/check",data=upload_data(frame))
    assert response.status_code==400
    assert "terminal_voltage" in response.json["error"]
    assert "2" in response.json["error"]


@pytest.mark.parametrize("column,value", [("cycle", "bad"), ("phase_code", 9)])
def test_invalid_context_in_file_cannot_be_replaced_with_form_defaults(client,column,value):
    frame=pd.DataFrame(dict(time=[0,30,60,90,120],terminal_voltage=[4,3.95,3.9,3.85,3.8],terminal_current=[-2]*5,temperature=[25]*5))
    frame[column]=value
    response=client.post('/api/assessment/check',data=upload_data(frame))
    assert response.status_code==400,response.json
