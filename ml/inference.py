"""Lightweight JSON forest inference; no pickle loading, sklearn or online training."""
from functools import lru_cache
import json
import math
import struct
from pathlib import Path
from .features import features

ARTIFACT = Path(__file__).resolve().parents[1] / "models/aggregate_delay.json"


@lru_cache(maxsize=1)
def load_model():
    try:
        model = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        if model["version"] != "aggregate-delay-rf-v1" or not model["trees"] or not model["profiles"] or not model["features"] or not model["evaluation"]:
            return None
        return model
    except (OSError, ValueError, KeyError, TypeError):
        return None


def risk_level(minutes):
    if not math.isfinite(minutes) or minutes < 0:
        raise ValueError("Delay estimate must be finite and nonnegative")
    return "LOW" if minutes < 15 else "MEDIUM" if minutes < 60 else "HIGH"


def predict_features(record, model):
    clean = features(record)
    encoded = {f"{k}={v}" if isinstance(v, str) else k: 1.0 if isinstance(v, str) else v for k,v in clean.items()}
    # sklearn's forest evaluates float32 features; preserve split-boundary parity.
    vector = [struct.unpack("f", struct.pack("f", encoded.get(name, 0.0)))[0] for name in model["features"]]
    estimates = []
    for tree in model["trees"]:
        node = 0
        while tree["left"][node] != -1:
            node = tree["left"][node] if vector[tree["feature"][node]] <= tree["threshold"][node] else tree["right"][node]
        estimates.append(tree["value"][node])
    value = sum(estimates) / len(estimates)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Invalid model estimate")
    return value


def status():
    model = load_model()
    return dict(model_available=model is not None, model_version=model["version"] if model else None,
                target="aggregate_average_delay_minutes", source="PUBLIC_HISTORICAL_DATA",
                evaluation=model["evaluation"] if model else None,
                profiles=model["profiles"] if model else [],
                limitation="Historical train–station aggregates, not future run predictions. Fictional trains have no automatic mapping.")


def planning_risk(occupancy, mode="STATIC", profiles=()):
    if mode not in {"STATIC", "ML_ASSISTED"}:
        raise ValueError("Unknown risk mode")
    pairs = {(r["train_id"], r["section_id"]) for r in occupancy}
    model = load_model() if mode == "ML_ASSISTED" else None
    source_profiles = {(r["train_id"],r["station_code"]):r for r in model["profiles"]} if model else {}
    predictions, penalties, seen = [], {}, set()
    for binding in profiles:
        key = (binding["train_id"], binding["section_id"])
        if key not in pairs or key in seen:
            raise ValueError("Risk binding must identify one unique supplied train/section occupancy")
        seen.add(key)
        source_key = (binding["historical_train_id"], binding["historical_station_id"])
        profile = source_profiles.get(source_key)
        if model and profile is None:
            raise ValueError("Historical risk profile does not exist in the frozen snapshot")
        value = None
        if model and profile:
            try:
                value = predict_features(profile, model)
            except (ValueError, KeyError, IndexError, TypeError):
                value = None
        predictions.append(dict(**binding, expected_delay_minutes=round(value, 3) if value is not None else None,
                                risk_level=risk_level(value) if value is not None else "UNKNOWN",
                                model_available=value is not None,
                                model_version=model["version"] if value is not None else None,
                                source="SYNTHETIC_FORECAST_SCENARIO", historical_source="PUBLIC_HISTORICAL_DATA"))
        if value is not None:
            penalties[key] = math.ceil(value)
    return penalties, dict(requested_mode=mode, effective_mode="ML_ASSISTED" if penalties else "STATIC",
                           model_available=model is not None, predictions=predictions,
                           message="Optional aggregate-delay reserve preference; hard safety margins unchanged."
                           if penalties else "Static planning: risk disabled, model unavailable, or no explicit historical profile binding.")
