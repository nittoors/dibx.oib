# Data Dictionary (summary)

- `asset_master.csv`: depot, asset type, manufacturer-like label, age, criticality, connectivity, protocol, health, failure risk.
- `workforce_master.csv`: pseudonymous worker, O*NET-SOC-style occupation, shift, availability, certifications, training due.
- `parts_master.csv.gz`: synthetic part/FSC/CAGE-like structure, source count, lead time, inventory, forecast demand, supply risk.
- `work_orders.csv.gz`: synthetic maintenance events, labor, parts wait, downtime, status.
- `production_operations.csv.gz`: plan/actual output and normalized constraint factors.
- `quality_events.csv.gz`: defects, severity, source, CAPA requirement, closure.
- `connectivity_assessment_seed.csv`: machine-to-AI readiness dimensions and score.
- `depot_readiness_summary.csv`: synthetic depot-level readiness indices and drivers.
