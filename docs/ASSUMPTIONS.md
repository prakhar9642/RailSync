# RailSync v2 assumptions and validation boundary

## Implemented engineering semantics

- Occupancies and possessions are half-open intervals. Candidate generation unions conflicting movements, complements them within the horizon, then subtracts train-safety margins.
- A possession reserves setup + productive work + release. Shared possessions start compatible tasks together and end at the longest member reservation.
- Multi-section availability is the intersection across every required capacity resource. A train conflicts only when its footprint intersects the possession footprint.
- Sections may expose explicit track/capacity resources and direction mappings. Direction alone never means track. Missing mappings protect the whole configured section conservatively.
- Compatibility requires an identical possession footprint and an eligible prototype group. Equal group labels are conditional eligibility, not a Railway rule.
- Crew and machine pools use cumulative CP-SAT capacity. Optional roster calendars, machine calendars, and all required section power windows constrain the full reservation.
- CP-SAT lexicographically serves criticality, urgency, overdue days, and task count before optimizing possession use, block count, robustness, optional risk reserve, and timing.
- Baseline comparison uses the same model, data, horizon, allowances, resources, and budget with integration disabled. Savings are reported only for the same delivered task set.
- FULLY_OPTIMAL means every objective stage was proven. FEASIBLE_BOUNDED is a constraint-safe incumbent and is never presented as proven optimal.

## Prototype-only assumptions

Maintenance demand, priorities, compatibility labels, crew/machine capacities and calendars, power windows, 15-minute train margins, 10-minute setup, 5-minute release, disruptions, and historical-profile transfer are synthetic prototype inputs—not official Railway rules.

## Requires domain and production validation

Real signalling/block boundaries, track topology, allowed concurrent work, possession protection, isolation/restoration, staff competencies and travel, machine logistics, running forecasts, freight, operational approvals, security, retention, and authorized integrations require owner-supplied data and formal acceptance. RailSync does not issue movement or work authority.
