"""Reproducible offline training; never executed by an HTTP request."""
import hashlib
import json
from pathlib import Path
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import GroupKFold
from .features import load_records, features

ROOT = Path(__file__).resolve().parents[1]


def make_model():
    return RandomForestRegressor(n_estimators=40, max_depth=5, min_samples_leaf=8, random_state=7, n_jobs=1)


def train():
    records = load_records()
    x = [features(r) for r in records]
    y = np.array([r["target"] for r in records])
    groups = [r["group"] for r in records]
    predictions, mean_baseline = np.zeros(len(y)), np.zeros(len(y))
    folds = []
    for train_idx, test_idx in GroupKFold(n_splits=len(set(groups))).split(x, y, groups):
        vectorizer = DictVectorizer(sparse=False)
        model = make_model()
        model.fit(vectorizer.fit_transform([x[i] for i in train_idx]), y[train_idx])
        predictions[test_idx] = model.predict(vectorizer.transform([x[i] for i in test_idx]))
        mean_baseline[test_idx] = y[train_idx].mean()
        folds.append(dict(held_out_groups=sorted({groups[i] for i in test_idx}),
                          train_rows=len(train_idx), validation_rows=len(test_idx),
                          mae_minutes=float(mean_absolute_error(y[test_idx], predictions[test_idx]))))
    def scores(values):
        return dict(mae_minutes=float(mean_absolute_error(y, values)),
                    rmse_minutes=float(mean_squared_error(y, values)**0.5))
    evaluation = dict(method="Leave-one-metro-corridor-out GroupKFold; no model tuning on held-out labels",
                      records=len(records), trains=len({r['train_id'] for r in records}),
                      model=scores(predictions), mean_baseline=scores(mean_baseline), folds=folds,
                      target="aggregate_average_delay_minutes", sklearn_version=sklearn.__version__)
    vectorizer = DictVectorizer(sparse=False)
    model = make_model().fit(vectorizer.fit_transform(x), y)
    trees = []
    for estimator in model.estimators_:
        tree = estimator.tree_
        trees.append(dict(left=tree.children_left.tolist(), right=tree.children_right.tolist(),
                          feature=tree.feature.tolist(), threshold=tree.threshold.tolist(),
                          value=tree.value[:, 0, 0].tolist()))
    profiles = [{k:v for k,v in r.items() if k not in {"target", "group"}} for r in records]
    artifact = dict(version="aggregate-delay-rf-v1", target=evaluation["target"],
                    source="PUBLIC_HISTORICAL_DATA", features=vectorizer.get_feature_names_out().tolist(),
                    trees=trees, profiles=profiles, evaluation=evaluation)
    destination = ROOT / "models/aggregate_delay.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(artifact, separators=(",", ":")), encoding="utf-8")
    (ROOT / "data/ml/evaluation.json").write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    print(json.dumps(evaluation, indent=2))
    print("Artifact SHA256:", hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__ == "__main__":
    train()
