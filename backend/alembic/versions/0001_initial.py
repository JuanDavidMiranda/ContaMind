"""Esquema inicial de usuarios, empresas y conciliaciones."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("tax_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "company_memberships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "company_id", name="uq_membership_user_company"),
    )
    op.create_table(
        "reconciliations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("tolerance", sa.Numeric(18, 4), nullable=False),
        sa.Column("erp_mapping", sa.JSON(), nullable=True),
        sa.Column("dian_mapping", sa.JSON(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("rules", sa.JSON(), nullable=True),
        sa.Column("validation_errors", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_reconciliations_company_id", "reconciliations", ["company_id"])
    op.create_index("ix_reconciliations_status", "reconciliations", ["status"])
    op.create_table(
        "reconciliation_files",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "reconciliation_id",
            sa.Uuid(),
            sa.ForeignKey("reconciliations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("detected_type", sa.String(16), nullable=False),
        sa.Column("encoding", sa.String(32), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("headers", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("reconciliation_id", "source", name="uq_reconciliation_file_source"),
    )
    op.create_index("ix_reconciliation_files_reconciliation_id", "reconciliation_files", ["reconciliation_id"])
    op.create_table(
        "reconciliation_results",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "reconciliation_id",
            sa.Uuid(),
            sa.ForeignKey("reconciliations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_key", sa.String(255), nullable=False),
        sa.Column("primary_category", sa.String(32), nullable=False),
        sa.Column("flags_text", sa.String(255), nullable=False),
        sa.Column("duplicate_kind", sa.String(32), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("reconciliation_id", "document_key", name="uq_reconciliation_document_key"),
    )
    op.create_index("ix_reconciliation_results_reconciliation_id", "reconciliation_results", ["reconciliation_id"])
    op.create_index("ix_reconciliation_results_document_key", "reconciliation_results", ["document_key"])
    op.create_index("ix_reconciliation_results_primary_category", "reconciliation_results", ["primary_category"])
    op.create_table(
        "reconciliation_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "reconciliation_id",
            sa.Uuid(),
            sa.ForeignKey("reconciliations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reconciliation_events_reconciliation_id", "reconciliation_events", ["reconciliation_id"])


def downgrade() -> None:
    op.drop_table("reconciliation_events")
    op.drop_table("reconciliation_results")
    op.drop_table("reconciliation_files")
    op.drop_table("reconciliations")
    op.drop_table("company_memberships")
    op.drop_table("companies")
    op.drop_table("users")
