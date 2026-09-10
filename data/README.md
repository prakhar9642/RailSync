# RailSync territory data

Each corridors/{territory_id}/manifest.json declares provenance, adapters, datasets, horizon, scenarios, and resource context. fixtures/ contains deterministic test-only inputs. territories.py loads canonical records without mixing manifest metadata into the optimizer payload.

The normal API exposes three populated public-timetable territories:

- saktigarh_memari_public_demo
- western_hdn
- delhi_agra

eastern_hdn remains an unavailable placeholder. eastern_hdn_test_fixture remains loadable only by explicit ID or include_test=true and is never the public default.

Canonical datasets are stations, sections, train_occupancy, optional train_services, and optional maintenance_tasks. ResourceContext is loaded separately. Rich additive fields support section_ids, capacity_resource_ids, direction mapping, tracks, machines, rosters, and power isolation.

Run:

    python -m data.validate_data

The validator checks manifests, adapters, required fields, references, interval order, and consecutive movement continuity in either direction. See [data provenance](../docs/DATA_PROVENANCE.md).
