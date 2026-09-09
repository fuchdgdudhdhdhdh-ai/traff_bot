from alembic import op
import sqlalchemy as sa

revision = "002_membership_channels"
down_revision = "001_v5_initial"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "join_requests",
        sa.Column("user_id", sa.BigInteger(), primary_key=True),
        sa.Column("channel_key", sa.String(50), primary_key=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )

def downgrade():
    op.drop_table("join_requests")
