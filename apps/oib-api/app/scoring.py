import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, model_validator


class DimensionRules(BaseModel):
    max_points: int = Field(ge=0, le=100)
    values: dict[str, int]
    aliases: dict[str, str]

    @model_validator(mode="after")
    def validate_dimension(self) -> Self:
        unknown_codes = set(self.aliases.values()) - set(self.values)
        if unknown_codes:
            raise ValueError(f"Aliases reference unknown codes: {sorted(unknown_codes)}")
        if any(points < 0 or points > self.max_points for points in self.values.values()):
            raise ValueError("Dimension points must fall between zero and max_points")
        return self


class GradeBand(BaseModel):
    grade: str
    minimum: int = Field(ge=0, le=100)
    recommended_action: str


class ScoringRules(BaseModel):
    code: str
    effective_from: str
    description: str
    dimensions: dict[str, DimensionRules]
    bands: list[GradeBand]

    @model_validator(mode="after")
    def validate_rules(self) -> Self:
        if sum(dimension.max_points for dimension in self.dimensions.values()) != 100:
            raise ValueError("Dimension maximums must total 100")
        if sorted((band.minimum for band in self.bands), reverse=True) != [75, 45, 0]:
            raise ValueError("Approved grade bands must be 75, 45, and 0")
        return self


@dataclass(frozen=True)
class ScoreResult:
    canonical_values: dict[str, str]
    dimension_points: dict[str, int]
    score: int
    grade: str
    recommended_action: str


def load_rules(path: Path) -> tuple[ScoringRules, str, dict[str, object]]:
    raw_bytes = path.read_bytes()
    raw_rules: dict[str, object] = json.loads(raw_bytes)
    rules = ScoringRules.model_validate(raw_rules)
    return rules, hashlib.sha256(raw_bytes).hexdigest(), raw_rules


def score_assessment(values: dict[str, str], rules: ScoringRules) -> ScoreResult:
    canonical_values: dict[str, str] = {}
    dimension_points: dict[str, int] = {}

    for dimension_name, dimension in rules.dimensions.items():
        display_value = values.get(dimension_name)
        if display_value is None:
            raise ValueError(f"Missing scoring dimension: {dimension_name}")
        canonical_code = dimension.aliases.get(display_value)
        if canonical_code is None:
            raise ValueError(f"Unknown {dimension_name} value: {display_value}")
        canonical_values[dimension_name] = canonical_code
        dimension_points[dimension_name] = dimension.values[canonical_code]

    score = min(100, sum(dimension_points.values()))
    band = next(
        band
        for band in sorted(rules.bands, key=lambda candidate: candidate.minimum, reverse=True)
        if score >= band.minimum
    )
    return ScoreResult(
        canonical_values=canonical_values,
        dimension_points=dimension_points,
        score=score,
        grade=band.grade,
        recommended_action=band.recommended_action,
    )
