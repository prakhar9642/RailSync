import json
import pytest
from .features import features, load_records
from . import inference


def test_preprocessing_is_deterministic_and_excludes_outcomes():
    row = load_records()[0]
    clean = features(row)
    assert clean == features(dict(row,target=-999,average_delay=900,criticality=10))
    assert set(clean) == {"station_code","train_type","route_position"}
    assert load_records() == load_records()


@pytest.mark.parametrize("changes",[{"train_type":None},{"station_code":""},{"route_position":float("nan")},{"route_position":True}])
def test_missing_features_do_not_create_guesses(changes):
    with pytest.raises(ValueError):
        features(dict(load_records()[0],**changes))


@pytest.mark.parametrize("minutes,level",[(0,"LOW"),(14.99,"LOW"),(15,"MEDIUM"),(59.99,"MEDIUM"),(60,"HIGH")])
def test_risk_thresholds(minutes,level):
    assert inference.risk_level(minutes) == level


def test_inference_and_disabled_unavailable_fallback(monkeypatch):
    row = load_records()[0]
    occupancy = [dict(train_id="FIXTURE",section_id="SEC")]
    binding = dict(train_id="FIXTURE",section_id="SEC",historical_train_id=row["train_id"],historical_station_id=row["station_code"])
    penalties, risk = inference.planning_risk(occupancy,"ML_ASSISTED",[binding])
    prediction = risk["predictions"][0]
    assert prediction["model_available"]
    assert prediction["source"] == "SYNTHETIC_FORECAST_SCENARIO"
    assert prediction["expected_delay_minutes"] >= 0
    assert penalties[("FIXTURE","SEC")] >= prediction["expected_delay_minutes"]
    assert inference.planning_risk(occupancy,"STATIC",[binding])[0] == {}
    assert inference.planning_risk(occupancy,"ML_ASSISTED",[])[0] == {}
    monkeypatch.setattr(inference,"load_model",lambda:None)
    penalties,risk = inference.planning_risk(occupancy,"ML_ASSISTED",[binding])
    assert penalties == {}
    assert risk["effective_mode"] == "STATIC"
    assert risk["predictions"][0]["expected_delay_minutes"] is None


def test_exported_forest_is_deterministic_and_evaluation_is_complete():
    records = load_records()
    artifact = inference.load_model()
    for i in range(0,len(records),73):
        prediction = inference.predict_features(records[i],artifact)
        assert prediction == inference.predict_features(records[i],artifact)
        assert prediction >= 0
    evaluation = artifact["evaluation"]
    assert sum(f["validation_rows"] for f in evaluation["folds"]) == len(records)
    assert len(evaluation["folds"]) == 4
    assert evaluation["model"]["mae_minutes"] > 0


def test_json_tree_inference_routes_features_without_training():
    model = {"features":["route_position"], "trees":[
        {"left":[1,-1,-1],"right":[2,-1,-1],"feature":[0,-2,-2],
         "threshold":[0.5,-2,-2],"value":[0,10,80]}]}
    row = dict(train_type="Superfast",station_code="GHY",route_position=0.4)
    assert inference.predict_features(row,model) == 10
    assert inference.predict_features(dict(row,route_position=0.8),model) == 80


def test_frozen_source_hashes():
    import hashlib
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "data/ml"
    manifest = json.loads((root / "provenance.json").read_text())
    for path,expected in manifest["sha256"].items():
        assert hashlib.sha256((root/path).read_bytes()).hexdigest() == expected
    assert hashlib.sha256(inference.ARTIFACT.read_bytes()).hexdigest() == manifest["model_sha256"]
