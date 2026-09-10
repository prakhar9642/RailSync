# Saktigarh–Memari public timetable demo

This territory proves that RailSync's existing corridor-independent loader and optimizer can consume a compact historical public timetable subset. It covers five consecutive stations on the Eastern Railway Barddhaman–Bandel–Howrah down table and uses service numbers exactly as printed.

## Provenance

- `stations.json`, `sections.json`, `train_occupancy.json`, and `train_services.json` are `PUBLIC_TIMETABLE_DERIVED` from the official *Eastern Railway Combined Suburban Time Table No. 10*, valid 1 November 2017 through 30 June 2018.
- The frozen local source is `../eastern_hdn_public_demo_source.pdf`; `timetable_evidence.json` records its URL, SHA-256 digest, relevant pages, transcription, and occupancy derivation.
- `maintenance_tasks.json` and `resource_context.json` are `SYNTHETIC_PROTOTYPE` inputs. They are fictional and exist only to exercise maintenance integration, priority, deadlines, crew capacity, and power-window constraints.

This is historical demonstration data, not current or live Indian Railways operational data. RailSync has no connection to Railway production systems. The published table gives a single intermediate-station time marked `d`; RailSync uses the upstream printed time as section entry and the next station's printed time as section exit, without estimating an unpublished arrival time.

Run it through the normal public interfaces with `load_territory("saktigarh_memari_public_demo")` or `POST /api/optimize` using the same `territory_id`.
