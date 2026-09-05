"""create user workspace association

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-27 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "user_workspaces",
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    )
    op.create_index("ix_user_workspaces_user_id", "user_workspaces", ["user_id"])
    op.create_index("ix_user_workspaces_workspace_id", "user_workspaces", ["workspace_id"])

def downgrade():
    op.drop_index("ix_user_workspaces_workspace_id", table_name="user_workspaces")
    op.drop_index("ix_user_workspaces_user_id", table_name="user_workspaces")
    op.drop_table("user_workspaces")
