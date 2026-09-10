# RailSync v2 data provenance

RailSync keeps ingestion outside the optimizer:

    territory manifest → validated adapter → canonical records → CP-SAT

## Labels

- PUBLIC_TIMETABLE_DERIVED: attributed public timetable or network material; frozen, incomplete, and not live.
- SYNTHETIC_PROTOTYPE: prototype maintenance, resources, power, compatibility, and planning inputs.
- SYNTHETIC_SCENARIO: temporary forecast/disruption input.
- TEST_FIXTURE: deterministic fictional data hidden from the normal selector.

## Public territories

| Territory | Public portion | Prototype portion | Horizon |
| --- | --- | --- | --- |
| saktigarh_memari_public_demo | Five historical Eastern Railway local services across Saktigarh–Memari, transcribed from the bundled official Combined Suburban Time Table No. 10 (valid 2017-11-01–2018-06-30) | Six tasks and resource calendars | 2017-11-01 03:30–08:00 |
| western_hdn | Ten named services 93001–93010 across Virar–Dahanu Road; route context from Western Railway material and public schedule pages accessed 2026-09-10 | Twelve tasks, directional capacity, crews, machines, and power | 2026-09-10 04:30–10:30 |
| delhi_agra | Eight named services across Hazrat Nizamuddin–Palwal; alignment context from the Northern Railway system map and public schedule pages accessed 2026-09-10 | Twelve tasks, directional capacity, crews, machines, and power | 2026-09-10 00:00–12:30 |

Source URLs are recorded per train in train_services.json; manifests record provenance per dataset. Occupancy is derived from successive published station times. RailSync section IDs are planning segments, not claims about signalling block limits.

The train selections are demonstration slices, not complete traffic. Public pages may change and do not represent actual running on the planning date. No CRIS, TMS, COA, SMMS, TDMS, crew, isolation, freight, or control-office feed is connected.

The optional historical risk artifact is described in [ML_RISK_MODEL.md](ML_RISK_MODEL.md); it never relaxes hard constraints.
