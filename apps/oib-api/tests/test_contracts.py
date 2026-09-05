from pathlib import Path

from app.main import app
from app.models import Base
from app.reconcile import build_reconciliation

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_schema_has_expected_tables_without_individual_workforce_storage() -> None:
    tables = set(Base.metadata.tables)

    assert len(tables) == 21
    assert "workforce_summary_snapshots" in tables
    assert "workforce_capacity_snapshots" in tables
    assert not tables.intersection({"workers", "employees", "workforce_members"})


def test_phase_four_only_exposes_the_approved_business_write() -> None:
    schema = app.openapi()
    business_paths = {
        path: operations
        for path, operations in schema["paths"].items()
        if path.startswith("/api/v1/") and "/health/" not in path
    }

    assert business_paths
    write_operations = {
        (path, method)
        for path, operations in business_paths.items()
        for method in operations
        if method in {"post", "put", "patch", "delete"}
    }
    assert write_operations == {("/api/v1/connectivity-assessments", "post")}


def test_reconciliation_has_no_operational_kpi_differences() -> None:
    report = build_reconciliation(REPOSITORY_ROOT / "docs" / "oib-source" / "baseline-kpis.json")

    assert report["status"] == "PASS"
    assert report["differences"] == []
    assert report["scoring_regeneration"]["status"] == "APPROVED_CHANGE"
