from alembic import op
import sqlalchemy as sa
revision="001_v5_initial";down_revision=None;branch_labels=None;depends_on=None
def upgrade():
 op.create_table("users",sa.Column("id",sa.Integer,primary_key=True),sa.Column("username",sa.String(64)),sa.Column("referrer_id",sa.Integer),sa.Column("balance",sa.Numeric(12,2),server_default="0"),sa.Column("captcha_ok",sa.Boolean,server_default=sa.false()),sa.Column("verified",sa.Boolean,server_default=sa.false()),sa.Column("blocked",sa.Boolean,server_default=sa.false()),sa.Column("created_at",sa.DateTime(timezone=True)))
 op.create_table("admins",sa.Column("user_id",sa.Integer,primary_key=True),sa.Column("role",sa.String(20)))
 op.create_table("rewards",sa.Column("id",sa.Integer,primary_key=True),sa.Column("referrer_id",sa.Integer),sa.Column("referral_id",sa.Integer,unique=True),sa.Column("amount",sa.Numeric(12,2)),sa.Column("status",sa.String(20)),sa.Column("hold_until",sa.DateTime(timezone=True)),sa.Column("last_ok",sa.Boolean))
 op.create_table("ledger",sa.Column("id",sa.Integer,primary_key=True),sa.Column("user_id",sa.Integer),sa.Column("amount",sa.Numeric(12,2)),sa.Column("kind",sa.String(40)),sa.Column("description",sa.Text),sa.Column("created_at",sa.DateTime(timezone=True)))
 op.create_table("withdrawals",sa.Column("id",sa.Integer,primary_key=True),sa.Column("user_id",sa.Integer),sa.Column("amount",sa.Numeric(12,2)),sa.Column("method",sa.String(40)),sa.Column("destination",sa.Text),sa.Column("status",sa.String(20)),sa.Column("created_at",sa.DateTime(timezone=True)))
 op.create_table("tickets",sa.Column("id",sa.Integer,primary_key=True),sa.Column("user_id",sa.Integer),sa.Column("status",sa.String(20)),sa.Column("created_at",sa.DateTime(timezone=True)))
 op.create_table("ticket_messages",sa.Column("id",sa.Integer,primary_key=True),sa.Column("ticket_id",sa.Integer),sa.Column("sender_id",sa.Integer),sa.Column("text",sa.Text),sa.Column("created_at",sa.DateTime(timezone=True)))
 op.create_table("settings",sa.Column("key",sa.String(100),primary_key=True),sa.Column("value",sa.Text))
 op.create_table("media",sa.Column("key",sa.String(100),primary_key=True),sa.Column("file_id",sa.String(255)))
 op.create_table("notices",sa.Column("id",sa.Integer,primary_key=True),sa.Column("position",sa.Integer),sa.Column("text",sa.Text),sa.Column("enabled",sa.Boolean,server_default=sa.true()))
 op.create_table("states",sa.Column("user_id",sa.Integer,primary_key=True),sa.Column("action",sa.String(50)),sa.Column("data",sa.Text))
def downgrade():
 for t in ["states","notices","media","settings","ticket_messages","tickets","withdrawals","ledger","rewards","admins","users"]:op.drop_table(t)
