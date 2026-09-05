# Production seed-data staging area

This directory contains the validated, versioned seed package introduced in Phase 2. The
prototype CSV files remain in `data/` and are not moved or rewritten.

The package includes:

- `manifest.json`, with file hashes, schema version, row counts, observation time, and provenance;
- `scoring-rules-v1.json`, the versioned 100-point assessment rules approved in Phase 0;
- strict Pydantic validation and cross-file relationship checks;
- idempotent PostgreSQL upserts inside a transaction; and
- an audit batch for every successful or rejected import.

From the repository root, run:

```bash
bash scripts/load-local-data.sh
```

To reconcile the database against the frozen Phase 0 KPI baseline:

```bash
cd backend
python -m app.reconcile
```

The individual workforce CSV is validated and aggregated during import, but individual worker
rows are intentionally not persisted. Parts remain explicitly global because the prototype data
does not contain a defensible part-to-depot relationship.
