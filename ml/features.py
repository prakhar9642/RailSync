"""Shared, target-free preprocessing for training and inference."""
import csv
import math
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data/ml/raw/Dataset"
METRO = {"GHY": "Guwahati", "KYQ": "Guwahati", "DLI": "Delhi", "NDLS": "Delhi",
         "ANVT": "Delhi", "PER": "Chennai", "MS": "Chennai", "HWH": "Kolkata",
         "KOAA": "Kolkata", "LTT": "Mumbai"}


def features(record):
    """Missing/invalid inputs abstain; historical outcome fields are never features."""
    kind, station, position = (record.get(k) for k in ("train_type", "station_code", "route_position"))
    if not isinstance(kind, str) or not kind.strip() or not isinstance(station, str) or not station.strip():
        raise ValueError("train_type and station_code are required")
    if isinstance(position, bool) or not isinstance(position, (int, float)) or not math.isfinite(position) or not 0 <= position <= 1:
        raise ValueError("route_position must be finite and between zero and one")
    return {"train_type": kind.strip(), "station_code": station.strip().upper(), "route_position": float(position)}


def load_records(root=RAW):
    metadata = {r["Train_Number"]: r for r in csv.DictReader((root / "Train_List.csv").open(encoding="utf-8-sig"))}
    records = []
    seen = set()
    for path in sorted((root / "Train_Route").glob("*.csv")):
        train = metadata[path.stem]
        rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
        group = " / ".join(sorted({METRO[train["From_Station"]], METRO[train["To_Station"]]}))
        for index, row in enumerate(rows):
            target = float(row["Average_Delay(min)"])
            if not math.isfinite(target) or target < 0:
                raise ValueError(f"Invalid observed aggregate target: {path}")
            key = (path.stem, row["Station"].strip())
            if key in seen:
                raise ValueError(f"Duplicate train/station aggregate: {key}")
            seen.add(key)
            records.append(dict(train_id=path.stem, train_name=train["Train_Name"],
                                station_code=row["Station"].strip(), station_name=row["Station_Name"].strip(),
                                train_type=train["Type"], route_position=index / max(1, len(rows)-1),
                                target=target, group=group))
    return records
