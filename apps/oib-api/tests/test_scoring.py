from pathlib import Path

import pytest
from pydantic import ValidationError

from app.scoring import ScoringRules, load_rules, score_assessment

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RULES_PATH = REPOSITORY_ROOT / "data" / "oib" / "seed" / "scoring-rules-v1.json"


def test_approved_rules_load_with_stable_hash() -> None:
    rules, checksum, raw = load_rules(RULES_PATH)

    assert rules.code == "prototype-v1"
    assert checksum == "b54c9714895d4424177054264a73ebb96133845873bae316d75c6edb11ee1e5a"
    assert raw["code"] == rules.code


@pytest.mark.parametrize(
    ("values", "expected_score", "expected_grade"),
    [
        (
            {
                "connectivity": "Native Digital",
                "protocol": "OPC UA",
                "data_rights": "Government usable",
                "cyber_status": "Approved",
                "history": ">24 months",
                "data_quality": "Good",
            },
            100,
            "Green",
        ),
        (
            {
                "connectivity": "Vendor Digital",
                "protocol": "Modbus TCP",
                "data_rights": "Limited license",
                "cyber_status": "Needs review",
                "history": "6-24 months",
                "data_quality": "Mixed",
            },
            57,
            "Yellow",
        ),
        (
            {
                "connectivity": "Legacy Analog",
                "protocol": "None",
                "data_rights": "No access",
                "cyber_status": "Not assessed",
                "history": "None",
                "data_quality": "Unknown",
            },
            8,
            "Red",
        ),
    ],
)
def test_assessments_use_approved_bands(
    values: dict[str, str], expected_score: int, expected_grade: str
) -> None:
    rules, _, _ = load_rules(RULES_PATH)

    result = score_assessment(values, rules)

    assert result.score == expected_score
    assert result.grade == expected_grade
    if values["protocol"] == "Modbus TCP":
        assert result.canonical_values["protocol"] == "MODBUS"


def test_unknown_and_missing_values_are_rejected() -> None:
    rules, _, _ = load_rules(RULES_PATH)
    values = {
        "connectivity": "Native Digital",
        "protocol": "OPC UA",
        "data_rights": "Government usable",
        "cyber_status": "Approved",
        "history": ">24 months",
        "data_quality": "Good",
    }

    with pytest.raises(ValueError, match="Unknown protocol value"):
        score_assessment({**values, "protocol": "Unapproved protocol"}, rules)
    with pytest.raises(ValueError, match="Missing scoring dimension"):
        score_assessment({key: value for key, value in values.items() if key != "history"}, rules)


def test_invalid_rule_contract_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ScoringRules.model_validate(
            {
                "code": "invalid",
                "effective_from": "2026-01-01",
                "description": "invalid",
                "dimensions": {
                    "one": {"max_points": 99, "values": {"A": 100}, "aliases": {"a": "B"}}
                },
                "bands": [],
            }
        )
