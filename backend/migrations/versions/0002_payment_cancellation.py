"""Durable cancellation tombstones for peer payment references."""
from alembic import op
import sqlalchemy as sa

revision = "0002_payment_cancellation"
down_revision = "0001_demo_baseline"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("demo_cancelled_payments",
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("request_key", sa.String(96), primary_key=True))

def downgrade():
    # Downgrading removes protection against replay of cancelled references.
    op.drop_table("demo_cancelled_payments")
