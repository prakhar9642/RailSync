# Experimental historical risk estimate

The primary target is **aggregate average delay in minutes** at a train–station
pair. This is a public community snapshot, not observations of individual runs,
and not a forecast of a particular future train. No maintenance, compatibility,
freight or failure labels are generated or learned.

## Source and reproducibility

Ankita Anand, *Indian Railway Express Trains Delay Datasets* (2024):
https://github.com/ankitaanand28/DA323_IndianRailwayTrainDelayDatasets

Frozen revision: `eccd6cb773b33f5e990f5dc64793e079d2823b52`, retrieved 2026-09-09.
The author describes March 2023–March 2024 coverage. The 42 route CSVs contain
1,479 train–station aggregates. Source files and the author's attribution/license
README are preserved byte-for-byte under `data/ml/raw`. SHA256 checksums are in
`data/ml/provenance.json`. The source specifies CC BY-NC-SA 4.0; retain attribution
and the noncommercial/share-alike conditions for source and derived material.
The supplied source is not an official Indian Railways operational feed.

Reproduce offline from the repository root:

```powershell
python -m pip install -r ml/requirements.txt
python -m ml.train
python -m pytest ml -vv
```

Training is offline only. The saved artifact is a plain JSON
forest in `models/aggregate_delay.json`; inference needs only Python's standard
library. No untrusted pickle is loaded, and no training or download occurs in an
HTTP request. Restore an absent model with the training command; static planning
continues to work without it.

## Features, model and evaluation

Features: supplied train type, station code, and normalized position in the
source's ordered route rows (`row_index / (row_count - 1)`). This last feature is
an ordinal route-position proxy, not distance, elapsed travel time or scheduled
hour. Train identity identifies an inference profile but is not a model feature.
Station codes and train types use deterministic one-hot encoding. Missing or
invalid features cause abstention. Target delay, right-time percentage, delay
severity percentages and cancellation statistics are excluded to avoid leakage.

One RandomForestRegressor: 40 trees, max depth 5, minimum leaf size 8, seed 7,
one worker. It captures modest category/progress interactions without a complex
model or hyperparameter search. A training-mean predictor supplies the evaluation
baseline; it is distinct from the non-integrated CP-SAT planning comparison.

Four leave-one-metro-corridor-out folds hold out all trains and both directions
in a route group. Delhi terminal codes are grouped together, as are Chennai,
Kolkata, Mumbai and Guwahati terminals. These documented terminal mappings are
used only for splitting. Encoding and model fitting use each training fold only.
Stations can appear in several corridors; entire train identities and reverse
metro routes cannot straddle a fold. There are no individual timestamps to permit
an honest temporal evaluation. Final artifact is refit to the full snapshot after
evaluation; its in-snapshot estimates are not independent validation results.

| Predictor | MAE (minutes) | RMSE (minutes) |
| --- | ---: | ---: |
| Random forest | 61.0251 | 90.1723 |
| Training-fold mean | 82.5855 | 106.1127 |

Exact metrics and fold sizes are frozen in `data/ml/evaluation.json`. Errors are
substantial. No accuracy percentage or operational reliability claim is made.
Sample sizes behind aggregates, individual run histories, collection bias and
future stability are unavailable. Some source rows have substantial unknown or
cancelled proportions; there is no justified run-count weighting. The four-fold
result is a limited cross-route experiment, not a national railway benchmark.

## Optional CP-SAT preference

`risk_mode=STATIC` is the default and preserves the prior nine-stage solver.
`ML_ASSISTED` requires explicit `risk_profiles` binding a supplied train/section
to a historical train/station profile. Fictional fixture identities are never
automatically mapped. Such transfer is labelled `SYNTHETIC_FORECAST_SCENARIO`
and has no demonstrated predictive validity for that fictional corridor.

Predictions are returned as `expected_delay_minutes` with the explicit aggregate
target above. LOW means <15, MEDIUM 15–<60, HIGH >=60 minutes. These are prototype
display thresholds, not calibrated probabilities. Unavailable estimates are null
and UNKNOWN; no profile means static fallback.

After possession minutes and block count, optional stages maximize minimum then
total risk-adjusted reserve: `min(before_slack - ceil(previous_estimate),
after_slack - ceil(next_estimate))`. Only mapped trains actually defining a
nominal candidate boundary contribute; the largest estimate is used at ties.
Unmapped boundaries contribute zero *preference penalty*, not a claim of zero
risk. Clipped horizon boundaries without an exact supplied train endpoint receive
no inferred estimate. Subtracting next-boundary uncertainty is a conservative
preference heuristic, not a claim that late arrival makes a window smaller.
Negative reserve is allowed and denotes a heuristic deficit, not infeasibility.

Static margins, protected occupancy, deadlines, setup/release, compatibility and
resources remain hard constraints. ML never changes them. Original raw boundary
slack remains reported separately and retains its existing definition. Both normal
comparison modes receive identical risk input. Recovery places its stability
stages above efficiency and this optional risk preference. Applying a profile
does not guarantee that the selected plan changes.
