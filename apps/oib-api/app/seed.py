import argparse
import ast
import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy import FromClause, Table, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    Asset,
    AssetHealthSnapshot,
    ConnectivityAssessment,
    DataSource,
    Depot,
    ImportBatch,
    ImportRejection,
    Manufacturer,
    Occupation,
    Part,
    PartInventorySnapshot,
    ProductionFlowSnapshot,
    QualitySnapshot,
    ReadinessSnapshot,
    ReadinessTrendPoint,
    ScoringRuleVersion,
    WorkCenter,
    WorkforceCapacitySnapshot,
    WorkforceSummarySnapshot,
)
from app.scoring import ScoringRules, load_rules, score_assessment
from app.seed_schemas import (
    AssetRow,
    ConnectivityRow,
    DepotReadinessRow,
    ManifestFile,
    PartRow,
    ProductionFlowRow,
    QualityRow,
    ReadinessTrendRow,
    SeedManifest,
    WorkforceCapacityRow,
    WorkforceSourceRow,
)

CSV_MODELS: dict[str, type[BaseModel]] = {
    "assets": AssetRow,
    "connectivity_assessments": ConnectivityRow,
    "depot_readiness": DepotReadinessRow,
    "parts": PartRow,
    "production_flow": ProductionFlowRow,
    "quality": QualityRow,
    "readiness_trend": ReadinessTrendRow,
    "workforce_capacity": WorkforceCapacityRow,
    "workforce_source": WorkforceSourceRow,
}
REQUIRED_DATASETS = set(CSV_MODELS) | {"scoring_rules"}
MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


@dataclass(frozen=True)
class SeedIssue:
    dataset: str
    row_number: int
    field_name: str | None
    raw_value: str | None
    reason: str


class SeedValidationError(Exception):
    def __init__(self, issues: list[SeedIssue]) -> None:
        super().__init__(f"Seed validation failed with {len(issues)} issue(s)")
        self.issues = issues


@dataclass(frozen=True)
class PreparedSeed:
    manifest: SeedManifest
    manifest_sha256: str
    rows: dict[str, list[BaseModel]]
    rules: ScoringRules
    rules_sha256: str
    raw_rules: dict[str, object]


@dataclass(frozen=True)
class SeedResult:
    batch_id: UUID
    idempotent_replay: bool
    row_counts: dict[str, Any]
    original_assessment_grades: dict[str, int]
    regenerated_assessment_grades: dict[str, int]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_file(manifest_path: Path, entry: ManifestFile) -> Path:
    candidate = (manifest_path.parent / entry.path).resolve()
    repository_root = manifest_path.resolve().parents[2]
    if not candidate.is_relative_to(repository_root):
        raise SeedValidationError(
            [SeedIssue(entry.dataset, 0, "path", entry.path, "Path leaves repository root")]
        )
    if not candidate.is_file():
        raise SeedValidationError(
            [SeedIssue(entry.dataset, 0, "path", entry.path, "File does not exist")]
        )
    actual_sha = _sha256(candidate)
    if actual_sha != entry.sha256:
        raise SeedValidationError(
            [
                SeedIssue(
                    entry.dataset,
                    0,
                    "sha256",
                    actual_sha,
                    f"Checksum does not match manifest value {entry.sha256}",
                )
            ]
        )
    return candidate


def _read_csv(path: Path, entry: ManifestFile, model: type[BaseModel]) -> list[BaseModel]:
    parsed: list[BaseModel] = []
    issues: list[SeedIssue] = []
    with path.open("r", encoding="utf-8-sig", newline="") as file_handle:
        reader = csv.DictReader(file_handle)
        for row_number, row in enumerate(reader, start=2):
            try:
                parsed.append(model.model_validate(row))
            except ValidationError as error:
                for detail in error.errors():
                    field_name = ".".join(str(part) for part in detail["loc"])
                    issues.append(
                        SeedIssue(
                            entry.dataset,
                            row_number,
                            field_name,
                            str(row.get(field_name, ""))[:1000],
                            str(detail["msg"]),
                        )
                    )
    if len(parsed) != entry.row_count:
        issues.append(
            SeedIssue(
                entry.dataset,
                0,
                "row_count",
                str(len(parsed)),
                f"Expected {entry.row_count} valid rows",
            )
        )
    if issues:
        raise SeedValidationError(issues)
    return parsed


def _prepare_seed(manifest_path: Path) -> PreparedSeed:
    manifest_bytes = manifest_path.read_bytes()
    manifest = SeedManifest.model_validate_json(manifest_bytes)
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    entries = {entry.dataset: entry for entry in manifest.files}
    if set(entries) != REQUIRED_DATASETS:
        missing = sorted(REQUIRED_DATASETS - set(entries))
        unexpected = sorted(set(entries) - REQUIRED_DATASETS)
        raise SeedValidationError(
            [
                SeedIssue(
                    "manifest",
                    0,
                    "files",
                    None,
                    f"Missing datasets={missing}; unexpected datasets={unexpected}",
                )
            ]
        )

    rows: dict[str, list[BaseModel]] = {}
    for dataset, model in CSV_MODELS.items():
        entry = entries[dataset]
        rows[dataset] = _read_csv(_resolve_file(manifest_path, entry), entry, model)

    rules_entry = entries["scoring_rules"]
    rules_path = _resolve_file(manifest_path, rules_entry)
    rules, rules_sha256, raw_rules = load_rules(rules_path)
    if rules_entry.row_count != 1:
        raise SeedValidationError(
            [SeedIssue("scoring_rules", 0, "row_count", str(rules_entry.row_count), "Must be 1")]
        )

    prepared = PreparedSeed(
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        rows=rows,
        rules=rules,
        rules_sha256=rules_sha256,
        raw_rules=raw_rules,
    )
    _validate_relationships(prepared)
    return prepared


def _typed_rows(prepared: PreparedSeed, dataset: str, row_type: type[BaseModel]) -> list[Any]:
    rows = prepared.rows[dataset]
    if not all(isinstance(row, row_type) for row in rows):
        raise TypeError(f"Prepared dataset {dataset} has an unexpected row type")
    return rows


def _validate_relationships(prepared: PreparedSeed) -> None:
    issues: list[SeedIssue] = []
    assets = {row.asset_id: row for row in _typed_rows(prepared, "assets", AssetRow)}
    depot_rows = _typed_rows(prepared, "depot_readiness", DepotReadinessRow)
    depot_codes = {row.depot for row in depot_rows}
    workforce_rows = _typed_rows(prepared, "workforce_source", WorkforceSourceRow)
    occupation_codes: dict[str, str] = {}
    for row in workforce_rows:
        previous = occupation_codes.setdefault(row.occupation, row.onet_soc)
        if previous != row.onet_soc:
            issues.append(
                SeedIssue(
                    "workforce_source",
                    0,
                    "onet_soc",
                    row.onet_soc,
                    f"Occupation {row.occupation} maps to both {previous} and {row.onet_soc}",
                )
            )

    for dataset, rows in prepared.rows.items():
        for index, row in enumerate(rows, start=2):
            depot = getattr(row, "depot", None)
            if depot is not None and depot not in depot_codes:
                issues.append(SeedIssue(dataset, index, "depot", depot, "Unknown depot code"))

    for index, row in enumerate(
        _typed_rows(prepared, "workforce_capacity", WorkforceCapacityRow), start=2
    ):
        if row.occupation not in occupation_codes:
            issues.append(
                SeedIssue(
                    "workforce_capacity",
                    index,
                    "occupation",
                    row.occupation,
                    "Occupation has no O*NET code in workforce source",
                )
            )

    for index, row in enumerate(
        _typed_rows(prepared, "connectivity_assessments", ConnectivityRow), start=2
    ):
        asset = assets.get(row.asset_id)
        if asset is None:
            issues.append(
                SeedIssue(
                    "connectivity_assessments",
                    index,
                    "asset_id",
                    row.asset_id,
                    "Asset does not exist",
                )
            )
            continue
        for field in ("depot", "asset_type", "manufacturer"):
            if getattr(row, field) != getattr(asset, field):
                issues.append(
                    SeedIssue(
                        "connectivity_assessments",
                        index,
                        field,
                        str(getattr(row, field)),
                        f"Does not match asset master value {getattr(asset, field)}",
                    )
                )
        try:
            score_assessment(
                {
                    "connectivity": row.connectivity,
                    "protocol": row.protocol,
                    "data_rights": row.data_rights,
                    "cyber_status": row.cyber_status,
                    "history": row.history,
                    "data_quality": row.data_quality,
                },
                prepared.rules,
            )
        except ValueError as error:
            issues.append(SeedIssue("connectivity_assessments", index, None, None, str(error)))

    if issues:
        raise SeedValidationError(issues)


def _upsert(
    session: Session,
    table: FromClause,
    rows: list[dict[str, Any]],
    key_columns: list[str],
    update_columns: list[str],
) -> None:
    if not rows:
        return
    typed_table = cast(Table, table)
    statement = insert(typed_table).values(rows)
    statement = statement.on_conflict_do_update(
        index_elements=[table.c[column] for column in key_columns],
        set_={column: getattr(statement.excluded, column) for column in update_columns},
    )
    session.execute(statement)


def _insert_ignore(
    session: Session, table: FromClause, rows: list[dict[str, Any]], key_columns: list[str]
) -> None:
    if rows:
        typed_table = cast(Table, table)
        session.execute(
            insert(typed_table)
            .values(rows)
            .on_conflict_do_nothing(index_elements=[table.c[column] for column in key_columns])
        )


def _source_values(manifest: SeedManifest) -> dict[str, Any]:
    return {
        "code": manifest.source_code,
        "name": manifest.source_name,
        "classification": manifest.source_classification,
        "description": manifest.source_description,
    }


def _record_failed_batch(
    manifest: SeedManifest,
    manifest_sha256: str,
    issues: list[SeedIssue],
) -> None:
    started_at = datetime.now(UTC)
    with SessionLocal() as session, session.begin():
        _upsert(
            session,
            DataSource.__table__,
            [_source_values(manifest)],
            ["code"],
            ["name", "classification", "description"],
        )
        batch = ImportBatch(
            source_code=manifest.source_code,
            dataset_version=manifest.dataset_version,
            schema_version=manifest.schema_version,
            manifest_sha256=manifest_sha256,
            status="FAILED",
            started_at=started_at,
            completed_at=datetime.now(UTC),
            row_counts={},
            rejection_count=len(issues),
        )
        session.add(batch)
        session.flush()
        session.add_all(
            ImportRejection(
                batch_id=batch.id,
                dataset=issue.dataset,
                row_number=issue.row_number,
                field_name=issue.field_name,
                raw_value=issue.raw_value,
                reason=issue.reason,
            )
            for issue in issues
        )


def _parse_drivers(raw_value: str) -> list[dict[str, Any]]:
    parsed = ast.literal_eval(raw_value)
    if not isinstance(parsed, list):
        raise ValueError("top_drivers must be a list")
    drivers: list[dict[str, Any]] = []
    for entry in parsed:
        if not isinstance(entry, tuple) or len(entry) != 2:
            raise ValueError("Each top driver must be a name/score pair")
        drivers.append({"name": str(entry[0]), "score": float(entry[1])})
    return drivers


def _load_transaction(session: Session, prepared: PreparedSeed, batch: ImportBatch) -> SeedResult:
    manifest = prepared.manifest
    observed_at = manifest.observed_at
    source_system = manifest.source_code
    batch_id = batch.id

    depot_rows = _typed_rows(prepared, "depot_readiness", DepotReadinessRow)
    _upsert(
        session,
        Depot.__table__,
        [{"code": row.depot, "name": row.name, "location": row.location} for row in depot_rows],
        ["code"],
        ["name", "location"],
    )

    _upsert(
        session,
        ScoringRuleVersion.__table__,
        [
            {
                "code": prepared.rules.code,
                "effective_from": date.fromisoformat(prepared.rules.effective_from),
                "rules": prepared.raw_rules,
                "sha256": prepared.rules_sha256,
            }
        ],
        ["code"],
        ["effective_from", "rules", "sha256"],
    )

    asset_rows = _typed_rows(prepared, "assets", AssetRow)
    manufacturer_names = sorted({row.manufacturer for row in asset_rows})
    _insert_ignore(
        session,
        Manufacturer.__table__,
        [{"name": name} for name in manufacturer_names],
        ["name"],
    )
    manufacturers = {
        name: manufacturer_id
        for manufacturer_id, name in session.execute(
            select(Manufacturer.id, Manufacturer.name)
        ).all()
    }

    production_rows = _typed_rows(prepared, "production_flow", ProductionFlowRow)
    quality_rows = _typed_rows(prepared, "quality", QualityRow)
    center_keys = sorted(
        {(row.depot, row.work_center) for row in asset_rows}
        | {(row.depot, row.work_center) for row in production_rows}
        | {(row.depot, row.work_center) for row in quality_rows}
    )
    _insert_ignore(
        session,
        WorkCenter.__table__,
        [{"depot_code": depot, "name": name} for depot, name in center_keys],
        ["depot_code", "name"],
    )
    centers = {
        (depot, name): center_id
        for center_id, depot, name in session.execute(
            select(WorkCenter.id, WorkCenter.depot_code, WorkCenter.name)
        ).all()
    }

    workforce_source = _typed_rows(prepared, "workforce_source", WorkforceSourceRow)
    occupations = {row.occupation: row.onet_soc for row in workforce_source}
    _upsert(
        session,
        Occupation.__table__,
        [{"code": code, "name": name} for name, code in sorted(occupations.items())],
        ["code"],
        ["name"],
    )

    _upsert(
        session,
        Asset.__table__,
        [
            {
                "asset_id": row.asset_id,
                "depot_code": row.depot,
                "asset_type": row.asset_type,
                "manufacturer_id": manufacturers[row.manufacturer],
                "model": row.model,
                "age_years": row.age_years,
                "criticality": row.criticality,
                "connectivity_tier": row.connectivity_tier,
                "protocol": row.protocol,
                "work_center_id": centers[(row.depot, row.work_center)],
                "source_system": source_system,
                "import_batch_id": batch_id,
            }
            for row in asset_rows
        ],
        ["asset_id"],
        [
            "depot_code",
            "asset_type",
            "manufacturer_id",
            "model",
            "age_years",
            "criticality",
            "connectivity_tier",
            "protocol",
            "work_center_id",
            "source_system",
            "import_batch_id",
        ],
    )
    _upsert(
        session,
        AssetHealthSnapshot.__table__,
        [
            {
                "asset_id": row.asset_id,
                "health_score": row.health_score,
                "failure_risk_30d": row.failure_risk_30d,
                "operating_hours": row.operating_hours,
                "observed_at": observed_at,
                "effective_from": observed_at,
                "source_system": source_system,
                "import_batch_id": batch_id,
            }
            for row in asset_rows
        ],
        ["asset_id", "observed_at"],
        [
            "health_score",
            "failure_risk_30d",
            "operating_hours",
            "effective_from",
            "source_system",
            "import_batch_id",
        ],
    )

    workforce_by_depot: dict[str, list[WorkforceSourceRow]] = defaultdict(list)
    for row in workforce_source:
        workforce_by_depot[row.depot].append(row)
    workforce_summary_rows = []
    for depot, rows in sorted(workforce_by_depot.items()):
        average = (sum(row.availability_pct for row in rows) / Decimal(len(rows))).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        workforce_summary_rows.append(
            {
                "depot_code": depot,
                "worker_count": len(rows),
                "average_availability_pct": average,
                "training_due_count": sum(row.training_due == "Yes" for row in rows),
                "observed_at": observed_at,
                "effective_from": observed_at,
                "source_system": source_system,
                "import_batch_id": batch_id,
            }
        )
    _upsert(
        session,
        WorkforceSummarySnapshot.__table__,
        workforce_summary_rows,
        ["depot_code", "observed_at"],
        [
            "worker_count",
            "average_availability_pct",
            "training_due_count",
            "effective_from",
            "source_system",
            "import_batch_id",
        ],
    )

    capacity_rows = _typed_rows(prepared, "workforce_capacity", WorkforceCapacityRow)
    _upsert(
        session,
        WorkforceCapacitySnapshot.__table__,
        [
            {
                "depot_code": row.depot,
                "occupation_code": occupations[row.occupation],
                "assigned_workers": row.assigned_workers,
                "available_workers": row.available_workers,
                "required_workers": row.required_workers,
                "capacity_gap": max(0, row.required_workers - row.available_workers),
                "training_due": row.training_due,
                "coverage_pct": row.coverage_pct,
                "observed_at": observed_at,
                "effective_from": observed_at,
                "source_system": source_system,
                "import_batch_id": batch_id,
            }
            for row in capacity_rows
        ],
        ["depot_code", "occupation_code", "observed_at"],
        [
            "assigned_workers",
            "available_workers",
            "required_workers",
            "capacity_gap",
            "training_due",
            "coverage_pct",
            "effective_from",
            "source_system",
            "import_batch_id",
        ],
    )

    part_rows = _typed_rows(prepared, "parts", PartRow)
    _upsert(
        session,
        Part.__table__,
        [
            {
                "part_id": row.part_id,
                "fsc": row.fsc,
                "part_name": row.part_name,
                "source_count": row.source_count,
                "lead_time_days": row.lead_time_days,
                "criticality": row.criticality,
                "recommended_action": row.recommended_action,
                "source_system": source_system,
                "import_batch_id": batch_id,
            }
            for row in part_rows
        ],
        ["part_id"],
        [
            "fsc",
            "part_name",
            "source_count",
            "lead_time_days",
            "criticality",
            "recommended_action",
            "source_system",
            "import_batch_id",
        ],
    )
    _upsert(
        session,
        PartInventorySnapshot.__table__,
        [
            {
                "part_id": row.part_id,
                "scope_key": "GLOBAL",
                "depot_code": None,
                "on_hand": row.on_hand,
                "projected_60d_demand": row.projected_60d_demand,
                "supply_risk": row.supply_risk,
                "observed_at": observed_at,
                "effective_from": observed_at,
                "source_system": source_system,
                "import_batch_id": batch_id,
            }
            for row in part_rows
        ],
        ["part_id", "scope_key", "observed_at"],
        [
            "depot_code",
            "on_hand",
            "projected_60d_demand",
            "supply_risk",
            "effective_from",
            "source_system",
            "import_batch_id",
        ],
    )

    _upsert(
        session,
        ProductionFlowSnapshot.__table__,
        [
            {
                "work_center_id": centers[(row.depot, row.work_center)],
                "weekly_plan": row.weekly_plan,
                "forecast_output": row.forecast_output,
                "plan_attainment_pct": row.plan_attainment_pct,
                "queue_hours": row.queue_hours,
                "downtime_hours": row.downtime_hours,
                "labor_gap_pct": row.labor_gap_pct,
                "constraint_driver": row.constraint_driver,
                "observed_at": observed_at,
                "effective_from": observed_at,
                "source_system": source_system,
                "import_batch_id": batch_id,
            }
            for row in production_rows
        ],
        ["work_center_id", "observed_at"],
        [
            "weekly_plan",
            "forecast_output",
            "plan_attainment_pct",
            "queue_hours",
            "downtime_hours",
            "labor_gap_pct",
            "constraint_driver",
            "effective_from",
            "source_system",
            "import_batch_id",
        ],
    )
    _upsert(
        session,
        QualitySnapshot.__table__,
        [
            {
                "work_center_id": centers[(row.depot, row.work_center)],
                "inspections": row.inspections,
                "defect_rate_pct": row.defect_rate_pct,
                "first_pass_yield_pct": row.first_pass_yield_pct,
                "open_ncr": row.open_ncr,
                "repeat_ncr": row.repeat_ncr,
                "top_defect": row.top_defect,
                "ai_focus": row.ai_focus,
                "observed_at": observed_at,
                "effective_from": observed_at,
                "source_system": source_system,
                "import_batch_id": batch_id,
            }
            for row in quality_rows
        ],
        ["work_center_id", "observed_at"],
        [
            "inspections",
            "defect_rate_pct",
            "first_pass_yield_pct",
            "open_ncr",
            "repeat_ncr",
            "top_defect",
            "ai_focus",
            "effective_from",
            "source_system",
            "import_batch_id",
        ],
    )

    _upsert(
        session,
        ReadinessSnapshot.__table__,
        [
            {
                "depot_code": row.depot,
                "readiness_score": row.readiness,
                "top_drivers": _parse_drivers(row.top_drivers),
                "observed_at": observed_at,
                "effective_from": observed_at,
                "source_system": source_system,
                "import_batch_id": batch_id,
            }
            for row in depot_rows
        ],
        ["depot_code", "observed_at"],
        [
            "readiness_score",
            "top_drivers",
            "effective_from",
            "source_system",
            "import_batch_id",
        ],
    )

    trend_rows = _typed_rows(prepared, "readiness_trend", ReadinessTrendRow)
    _upsert(
        session,
        ReadinessTrendPoint.__table__,
        [
            {
                "depot_code": row.depot,
                "reporting_period": date(manifest.reporting_year, MONTHS[row.month], 1),
                "display_month": row.month,
                "readiness_score": row.readiness,
                "source_system": source_system,
                "import_batch_id": batch_id,
            }
            for row in trend_rows
        ],
        ["depot_code", "reporting_period"],
        ["display_month", "readiness_score", "source_system", "import_batch_id"],
    )

    connectivity_rows = _typed_rows(prepared, "connectivity_assessments", ConnectivityRow)
    original_grades = Counter(row.readiness_grade for row in connectivity_rows)
    regenerated_grades: Counter[str] = Counter()
    assessment_values = []
    for row in connectivity_rows:
        result = score_assessment(
            {
                "connectivity": row.connectivity,
                "protocol": row.protocol,
                "data_rights": row.data_rights,
                "cyber_status": row.cyber_status,
                "history": row.history,
                "data_quality": row.data_quality,
            },
            prepared.rules,
        )
        regenerated_grades[result.grade] += 1
        assessment_values.append(
            {
                "asset_id": row.asset_id,
                "ruleset_code": prepared.rules.code,
                "connectivity_code": result.canonical_values["connectivity"],
                "connectivity_label": row.connectivity,
                "protocol_code": result.canonical_values["protocol"],
                "protocol_label": row.protocol,
                "data_rights_code": result.canonical_values["data_rights"],
                "data_rights_label": row.data_rights,
                "cyber_status_code": result.canonical_values["cyber_status"],
                "cyber_status_label": row.cyber_status,
                "history_code": result.canonical_values["history"],
                "history_label": row.history,
                "data_quality_code": result.canonical_values["data_quality"],
                "data_quality_label": row.data_quality,
                "dimension_points": result.dimension_points,
                "readiness_score": result.score,
                "readiness_grade": result.grade,
                "recommended_action": result.recommended_action,
                "observed_at": observed_at,
                "source_system": source_system,
                "import_batch_id": batch_id,
            }
        )
    _upsert(
        session,
        ConnectivityAssessment.__table__,
        assessment_values,
        ["asset_id", "ruleset_code", "observed_at"],
        [
            "connectivity_code",
            "connectivity_label",
            "protocol_code",
            "protocol_label",
            "data_rights_code",
            "data_rights_label",
            "cyber_status_code",
            "cyber_status_label",
            "history_code",
            "history_label",
            "data_quality_code",
            "data_quality_label",
            "dimension_points",
            "readiness_score",
            "readiness_grade",
            "recommended_action",
            "source_system",
            "import_batch_id",
        ],
    )

    input_counts = {entry.dataset: entry.row_count for entry in manifest.files}
    stored_counts = {
        "assets": len(asset_rows),
        "asset_health_snapshots": len(asset_rows),
        "connectivity_assessments": len(connectivity_rows),
        "depots": len(depot_rows),
        "part_inventory_snapshots": len(part_rows),
        "parts": len(part_rows),
        "production_flow_snapshots": len(production_rows),
        "quality_snapshots": len(quality_rows),
        "readiness_snapshots": len(depot_rows),
        "readiness_trend_points": len(trend_rows),
        "workforce_capacity_snapshots": len(capacity_rows),
        "workforce_individual_rows": 0,
        "workforce_summary_snapshots": len(workforce_summary_rows),
    }
    row_counts = {"input": input_counts, "stored": stored_counts}
    return SeedResult(
        batch_id=batch_id,
        idempotent_replay=False,
        row_counts=row_counts,
        original_assessment_grades=dict(original_grades),
        regenerated_assessment_grades=dict(regenerated_grades),
    )


def run_seed(manifest_path: Path) -> SeedResult:
    manifest_path = manifest_path.resolve()
    manifest_bytes = manifest_path.read_bytes()
    manifest = SeedManifest.model_validate_json(manifest_bytes)
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    try:
        prepared = _prepare_seed(manifest_path)
    except SeedValidationError as error:
        _record_failed_batch(manifest, manifest_sha256, error.issues)
        raise

    with SessionLocal() as session:
        try:
            with session.begin():
                existing = session.scalar(
                    select(ImportBatch).where(
                        ImportBatch.manifest_sha256 == prepared.manifest_sha256,
                        ImportBatch.status == "SUCCEEDED",
                    )
                )
                if existing is not None:
                    grades = existing.row_counts.get("assessment_grades", {})
                    return SeedResult(
                        batch_id=existing.id,
                        idempotent_replay=True,
                        row_counts=existing.row_counts,
                        original_assessment_grades=grades.get("original", {}),
                        regenerated_assessment_grades=grades.get("regenerated", {}),
                    )
                _upsert(
                    session,
                    DataSource.__table__,
                    [_source_values(prepared.manifest)],
                    ["code"],
                    ["name", "classification", "description"],
                )
                batch = ImportBatch(
                    source_code=prepared.manifest.source_code,
                    dataset_version=prepared.manifest.dataset_version,
                    schema_version=prepared.manifest.schema_version,
                    manifest_sha256=prepared.manifest_sha256,
                    status="RUNNING",
                    started_at=datetime.now(UTC),
                    row_counts={},
                    rejection_count=0,
                )
                session.add(batch)
                session.flush()
                result = _load_transaction(session, prepared, batch)
                batch.status = "SUCCEEDED"
                batch.completed_at = datetime.now(UTC)
                batch.row_counts = {
                    **result.row_counts,
                    "assessment_grades": {
                        "original": result.original_assessment_grades,
                        "regenerated": result.regenerated_assessment_grades,
                    },
                }
        except Exception as error:
            issue = SeedIssue("database", 0, None, None, str(error))
            _record_failed_batch(prepared.manifest, prepared.manifest_sha256, [issue])
            raise
    return result


def _default_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "seed" / "manifest.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and seed Depot Readiness PostgreSQL")
    parser.add_argument("--manifest", type=Path, default=_default_manifest_path())
    arguments = parser.parse_args()
    try:
        result = run_seed(arguments.manifest)
    except SeedValidationError as error:
        print(json.dumps({"status": "FAILED", "issues": [asdict(i) for i in error.issues]}))
        raise SystemExit(2) from error
    print(json.dumps({"status": "SUCCEEDED", **asdict(result)}, default=str, indent=2))


if __name__ == "__main__":
    main()
