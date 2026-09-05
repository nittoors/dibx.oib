"""add authenticated assessment persistence and audit events

Revision ID: 7e9d4c2b1a30
Revises: d56306b87a56
Create Date: 2026-09-04 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7e9d4c2b1a30"
down_revision: str | Sequence[str] | None = "d56306b87a56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "submitted_connectivity_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("depot_code", sa.String(length=16), nullable=False),
        sa.Column("asset_type", sa.String(length=120), nullable=False),
        sa.Column("manufacturer", sa.String(length=160), nullable=False),
        sa.Column("connectivity_code", sa.String(length=64), nullable=False),
        sa.Column("connectivity_label", sa.String(length=64), nullable=False),
        sa.Column("protocol_code", sa.String(length=64), nullable=False),
        sa.Column("protocol_label", sa.String(length=64), nullable=False),
        sa.Column("data_rights_code", sa.String(length=64), nullable=False),
        sa.Column("data_rights_label", sa.String(length=64), nullable=False),
        sa.Column("cyber_status_code", sa.String(length=64), nullable=False),
        sa.Column("cyber_status_label", sa.String(length=64), nullable=False),
        sa.Column("history_code", sa.String(length=64), nullable=False),
        sa.Column("history_label", sa.String(length=64), nullable=False),
        sa.Column("data_quality_code", sa.String(length=64), nullable=False),
        sa.Column("data_quality_label", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("dimension_points", sa.JSON(), nullable=False),
        sa.Column("readiness_score", sa.Integer(), nullable=False),
        sa.Column("readiness_grade", sa.String(length=16), nullable=False),
        sa.Column("recommended_action", sa.String(length=200), nullable=False),
        sa.Column("ruleset_code", sa.String(length=64), nullable=False),
        sa.Column("actor_subject", sa.String(length=256), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "depot_code IN ('RRAD', 'ANAD', 'SIAD', 'WVA', 'Other')",
            name="submitted_assessments_depot_check",
        ),
        sa.CheckConstraint(
            "readiness_grade IN ('Green', 'Yellow', 'Red')",
            name="submitted_assessments_grade_check",
        ),
        sa.CheckConstraint(
            "readiness_score BETWEEN 0 AND 100", name="submitted_assessments_score_check"
        ),
        sa.ForeignKeyConstraint(["ruleset_code"], ["scoring_rule_versions.code"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("actor_subject", "idempotency_key"),
    )
    op.create_index(
        "ix_submitted_assessments_depot_time",
        "submitted_connectivity_assessments",
        ["depot_code", "assessed_at"],
        unique=False,
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_subject", sa.String(length=256), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("depot_code", sa.String(length=16), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('SUCCEEDED', 'DENIED', 'FAILED')", name="audit_events_outcome_check"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_actor", "audit_events", ["actor_subject"], unique=False)
    op.create_index("ix_audit_events_time", "audit_events", ["occurred_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_events_time", table_name="audit_events")
    op.drop_index("ix_audit_events_actor", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index(
        "ix_submitted_assessments_depot_time",
        table_name="submitted_connectivity_assessments",
    )
    op.drop_table("submitted_connectivity_assessments")
