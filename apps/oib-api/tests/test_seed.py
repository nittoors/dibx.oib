from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import ConnectivityAssessment, ImportBatch, WorkforceSummarySnapshot
from app.seed import SeedValidationError, _prepare_seed, _resolve_file, run_seed
from app.seed_schemas import ManifestFile

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPOSITORY_ROOT / "data" / "oib" / "seed" / "manifest.json"


def test_manifest_validates_all_sources_and_relationships() -> None:
    prepared = _prepare_seed(MANIFEST_PATH)

    assert prepared.manifest.dataset_version == "synthetic-v1"
    assert len(prepared.rows["assets"]) == 1600
    assert len(prepared.rows["workforce_source"]) == 2600
    assert len(prepared.rows["connectivity_assessments"]) == 400


def test_manifest_rejects_a_path_outside_repository() -> None:
    entry = ManifestFile(
        dataset="assets",
        path="../../../outside.csv",
        sha256="0" * 64,
        row_count=1,
    )

    with pytest.raises(SeedValidationError, match="Seed validation failed") as error:
        _resolve_file(MANIFEST_PATH, entry)

    assert error.value.issues[0].reason == "Path leaves repository root"


def test_seed_is_audited_aggregate_only_and_idempotent() -> None:
    first = run_seed(MANIFEST_PATH)
    replay = run_seed(MANIFEST_PATH)

    assert first.row_counts["stored"]["workforce_individual_rows"] == 0
    assert first.regenerated_assessment_grades == {"Green": 64, "Yellow": 252, "Red": 84}
    assert replay.idempotent_replay is True
    assert replay.batch_id == first.batch_id
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ImportBatch)) == 1
        assert session.scalar(select(func.count()).select_from(WorkforceSummarySnapshot)) == 4
        assert session.scalar(select(func.count()).select_from(ConnectivityAssessment)) == 400
