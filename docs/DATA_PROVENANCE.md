# RailSync Data Provenance

RailSync separates source ingestion from optimization:

`Planning territory → source adapter → canonical RailSync data → CP-SAT optimizer`

The optimization engine is decoupled from data ingestion through a canonical
RailSync schema. Authorized Railway data sources can later be connected through
source-specific adapters without redesigning the core optimization model.
Production integration will still require source authorization, schema mapping,
validation, operational rules, security controls, and acceptance testing.

## Provenance labels

| Label | Meaning |
| --- | --- |
| `PUBLIC_TIMETABLE_DERIVED` | Frozen passenger timetable or corridor information derived from an identified public source. It is not live operational data. |
| `SYNTHETIC_PROTOTYPE` | Manually constructed data used by the current prototype. |
| `SYNTHETIC_SCENARIO` | Explicitly generated maintenance, resource, freight, or disruption inputs for scenario analysis. |
| `TEST_FIXTURE` | Deterministic fictional data used only for tests and demonstrations. |
| `PUBLIC_HISTORICAL_DATA` | Frozen, attributed community train–station aggregate performance; not individual-run history or an official operational feed. |
| `SYNTHETIC_FORECAST_SCENARIO` | Explicitly user-selected hypothetical delay or historical-profile transfer onto fictional planning inputs. |

Territory manifests record provenance per available dataset. A territory marked
`PLACEHOLDER` has no loadable datasets or scenario references. The loader rejects
it rather than returning an empty object that could be mistaken for verified data.

## Current registrations

| ID | Status | Meaning |
| --- | --- | --- |
| `delhi_agra` | `POPULATED` | Preserves its documented mixed public-derived corridor and synthetic occupancy provenance. |
| `eastern_hdn` | `PLACEHOLDER` | Contains no data. Intended provenance is `PUBLIC_TIMETABLE_DERIVED` only after verified sources are supplied. |
| `western_hdn` | `PLACEHOLDER` | Contains no data. Intended provenance is `PUBLIC_TIMETABLE_DERIVED` only after verified sources are supplied. |
| `eastern_hdn_test_fixture` | `POPULATED` | All stations, sections, occupancy, and maintenance tasks are fictional `TEST_FIXTURE` data. |
| `saktigarh_memari_public_demo` | `POPULATED` | Historical public timetable-derived Saktigarh–Memari subset with synthetic prototype maintenance and resources. |

Fixture manifests live under `data/fixtures/` and require their explicit fixture
ID. A real/future corridor ID never falls back to a fixture.

The Eastern fixture manifest also fixes its six-hour planning horizon and points
to a `TEST_FIXTURE` resource context. Crew capacities and power windows in that
file are deterministic demonstration assumptions, not official Railway data.

## Phase 8 Lite public timetable demo

The `saktigarh_memari_public_demo` territory uses the official Eastern Railway
*Combined Suburban Time Table No. 10*, published for 1 November 2017 through
30 June 2018. Its frozen planning horizon is 1 November 2017, 03:30–08:00.
This is historical public information and no live Indian Railways operational
feed is connected.

The five consecutive stations are Saktigarh (`SKG`), Palsit (`PLAE`), Rasulpur
(`RSLR`), Nimo Halt (`NMF`), and Memari (`MYM`). The four IDs `SKM_SEC01` through
`SKM_SEC04` represent consecutive RailSync planning sections only; they are not
claims about signalling block boundaries.

| Service | SKG | PLAE | RSLR | NMF | MYM | PDF page (printed) |
| --- | --- | --- | --- | --- | --- | --- |
| 37786 | 03:45 | 03:49 | 03:53 | 03:56 | 03:59 | 29 (28) |
| 37814 | 04:16 | 04:19 | 04:23 | 04:27 | 04:30 | 30 (29) |
| 37818 | 05:53 | 05:56 | 06:00 | 06:04 | 06:07 | 31 (30) |
| 37782 | 06:55 | 06:59 | 07:03 | 07:06 | 07:09 | 32 (31) |
| 37824 | 07:11 | 07:14 | 07:18 | 07:22 | 07:25 | 33 (32) |

For each adjacent pair, occupancy starts at the printed upstream station time
and ends at the printed downstream station time. The historical table provides
one intermediate-station time marked `d`, so the derivation does not invent a
separate arrival time and conservatively includes any downstream dwell. The
source URL, local PDF digest, and machine-readable transcription are recorded in
`data/corridors/saktigarh_memari_public_demo/timetable_evidence.json`.

Stations, passenger service identifiers, and section occupancy are
`PUBLIC_TIMETABLE_DERIVED`. Maintenance requests and crew/power availability are
fictional `SYNTHETIC_PROTOTYPE` inputs. The timetable does not print service
names in these columns, so the UI honestly displays the printed identifiers.
The selected services are a compact demonstration subset, not a complete traffic
picture, and the timetable's historical validity does not imply current operation.

## Phase 7 historical-risk source

`data/ml/raw` freezes Ankita Anand's public aggregate delay dataset at revision
`eccd6cb773b33f5e990f5dc64793e079d2823b52` on 2026-09-09:
https://github.com/ankitaanand28/DA323_IndianRailwayTrainDelayDatasets

The source describes March 2023–March 2024 coverage. There are 1,479 train–station
aggregate rows across 42 route files plus train metadata. Its README declares
CC BY-NC-SA 4.0 and is retained with the snapshot; attribution and source-file
SHA256 hashes are in `data/ml/provenance.json`. No synthetic targets were added.
The processed target is observed aggregate average delay; only train type,
station code and normalized route-row position enter the model. Delay severity
and punctuality percentages do not enter features. Full split/evaluation and
limitations are in [ML_RISK_MODEL.md](ML_RISK_MODEL.md).

Historical data remains separate from the Eastern fixture's fictional occupancy,
maintenance and resource data. A user may explicitly bind a public profile to a
fixture train/section as a SYNTHETIC_FORECAST_SCENARIO; no identity equivalence or
real-corridor validity is implied. The response preserves both provenance labels.

## Intended source split

Public or grounded inputs are frozen passenger timetable snapshots and corridor
information. Every snapshot should retain source identity, retrieval date,
coverage, transformation notes, and version information.

Synthetic and transparent inputs are maintenance demand, crew availability,
machine availability, power availability, freight forecasts, and disruption
scenarios. These inputs must carry an explicit synthetic provenance label and
document their assumptions.

RailSync does not claim live access to Railway production maintenance or control
systems. It has no current CRIS, TMS, SMMS, TDMS, or COA connection. The adapter
boundary is an extension point, not a claim of zero-effort production integration.

## Adapter boundary

Adapters validate source shape and emit the existing canonical station, section,
train-occupancy, and maintenance-task records. Territory metadata remains outside
the optimizer payload. `ResourceContext` is also passed separately to the optimizer;
future scenario adapters may construct it from explicitly labelled synthetic data.
The same pattern can later cover frozen public passenger snapshots, synthetic
maintenance scenarios, synthetic resource contexts, and synthetic freight forecasts.
