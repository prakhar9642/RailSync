# RailSync Day 1 Corridor Data

## Corridor

### Delhi–Agra main line (synthetic timetable, real station names)

This is a small test corridor for the RailSync prototype. Station names are taken from the publicly documented Delhi–Agra route on Indian Railways, but train movements and timings are synthetic and must not be treated as live operational data.

Stations in corridor order:


1. STN01 — New Delhi
2. STN02 — Hazrat Nizamuddin
3. STN03 — Faridabad
4. STN04 — Palwal
5. STN05 — Kosi Kalan
6. STN06 — Mathura Junction
7. STN07 — Chata
8. STN08 — Raja Ki Mandi
9. STN09 — Agra Cantt

Eight consecutive sections (SEC01–SEC08) connect adjacent stations from New Delhi to Agra Cantt.

## Dataset Summary

- stations.json — 9 ordered corridor endpoints
- sections.json — 8 consecutive inter-station blocks
- train_occupancy.json — 21 records across 7 distinct trains (TR101–TR107)

## Public Timetable Source

Source checked: Indian Railways enquiry portal and RailYatri train route pages for Delhi–Agra corridor station lists and typical running patterns.

Access date: 2026-08-31
What was used: Real station names and corridor ordering from public route information.
What is synthetic: Train IDs, departure/arrival times, and section occupancy windows. Times are manually constructed to satisfy temporal ordering and overlap constraints for optimizer testing.


Assumptions:

All trains run in the down direction (New Delhi → Agra Cantt).
Section travel times are approximated at 13–22 minutes depending on train category.
No bidirectional or crossing movements are modelled on Day 1.
TR104 occupancy on SEC03 matches the shared contract example in CONTRACTS.md.

## Data Rules

Field names train_id, section_id, entry_time, and exit_time follow CONTRACTS.md exactly.
Every section_id in train_occupancy.json exists in sections.json.
All occupancy records have entry_time earlier than exit_time.
Trains moving across multiple sections progress forward in time along consecutive sections.

## Validation

python data/validate_data.py

The validator checks JSON parsing, referential integrity, temporal ordering, and consecutive-section continuity for each train.