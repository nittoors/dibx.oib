import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from app.api.read import readiness_summary
from app.auth import ADMIN_GROUP, ALL_DEPOTS, Principal
from app.db import SessionLocal

PARITY_SECTIONS = ("command", "assets", "workforce", "flow", "quality")
RECONCILIATION_PRINCIPAL = Principal(
    subject="local-reconciliation",
    groups=frozenset({ADMIN_GROUP}),
    depots=ALL_DEPOTS,
    authentication_mode="development",
)


def _repository_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "data" / "oib").is_dir():
            return parent
    return Path("/service")


def build_reconciliation(baseline_path: Path) -> dict[str, Any]:
    repository_root = _repository_root()
    baseline = cast(dict[str, Any], json.loads(baseline_path.read_text(encoding="utf-8")))
    differences: list[dict[str, Any]] = []
    actual_by_depot: dict[str, dict[str, Any]] = {}

    with SessionLocal() as session:
        for depot in ("ALL", "RRAD", "ANAD", "SIAD", "WVA"):
            actual = readiness_summary(
                session, RECONCILIATION_PRINCIPAL, depot
            ).model_dump(mode="json")
            actual_by_depot[depot] = actual
            for section in PARITY_SECTIONS:
                if actual[section] != baseline[depot][section]:
                    differences.append(
                        {
                            "depot": depot,
                            "section": section,
                            "expected": baseline[depot][section],
                            "actual": actual[section],
                        }
                    )

        actual_supply = dict(actual_by_depot["ALL"]["supply"])
        supply_scope = actual_supply.pop("scope")
        if actual_supply != baseline["global"]["supply"]:
            differences.append(
                {
                    "depot": "GLOBAL",
                    "section": "supply",
                    "expected": baseline["global"]["supply"],
                    "actual": actual_supply,
                }
            )

    actual_assessment = dict(actual_by_depot["ALL"]["assessment"])
    ruleset = actual_assessment.pop("ruleset")
    return {
        "status": "PASS" if not differences else "FAIL",
        "generated_at": datetime.now(UTC).isoformat(),
        "baseline": str(baseline_path.relative_to(repository_root)),
        "checked_depots": ["ALL", "RRAD", "ANAD", "SIAD", "WVA"],
        "exact_parity_sections": list(PARITY_SECTIONS) + ["supply"],
        "differences": differences,
        "scoring_regeneration": {
            "status": "APPROVED_CHANGE",
            "ruleset": ruleset,
            "legacy_csv_distribution": baseline["global"]["assessment"],
            "regenerated_distribution": actual_assessment,
            "reason": "Connectivity scores are regenerated from the approved versioned ruleset.",
        },
        "data_scope": {
            "supply": supply_scope,
            "workforce": "AGGREGATE_ONLY",
        },
    }


def main() -> None:
    repository_root = _repository_root()
    parser = argparse.ArgumentParser(description="Reconcile PostgreSQL KPIs to Phase 0 baseline")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=repository_root / "docs" / "oib-source" / "baseline-kpis.json",
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = build_reconciliation(arguments.baseline.resolve())
    rendered = json.dumps(report, indent=2) + "\n"
    if arguments.output is not None:
        arguments.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
