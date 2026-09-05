"""add basemap to layers

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-12 12:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    # Check if basemap column exists
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='layers' AND column_name='basemap'"
    )).fetchone()
    
    if not result:
        op.add_column('layers', sa.Column('basemap', sa.Boolean(), nullable=True))
    
    # Update any existing NULL values to false
    op.execute("UPDATE layers SET basemap = false WHERE basemap IS NULL")
    
    # Alter column to be NOT NULL and set server default to false
    op.alter_column('layers', 'basemap',
               existing_type=sa.Boolean(),
               nullable=False,
               server_default=sa.text('false'))

def downgrade():
    op.alter_column('layers', 'basemap',
               existing_type=sa.Boolean(),
               nullable=True,
               server_default=None)
