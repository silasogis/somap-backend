"""rename abasc to logistics

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-01 22:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Renomear tabelas
    op.rename_table('abasc_routes', 'logistics_routes')
    op.rename_table('abasc_route_stops', 'logistics_route_stops')

    # 2. Renomear índices
    op.execute("ALTER INDEX IF EXISTS ix_abasc_routes_geom RENAME TO ix_logistics_routes_geom")
    op.execute("ALTER INDEX IF EXISTS ix_abasc_route_stops_geom RENAME TO ix_logistics_route_stops_geom")
    op.execute("ALTER INDEX IF EXISTS ix_abasc_route_stops_route_id RENAME TO ix_logistics_route_stops_route_id")

def downgrade():
    # 1. Reverter índices
    op.execute("ALTER INDEX IF EXISTS ix_logistics_routes_geom RENAME TO ix_abasc_routes_geom")
    op.execute("ALTER INDEX IF EXISTS ix_logistics_route_stops_geom RENAME TO ix_abasc_route_stops_geom")
    op.execute("ALTER INDEX IF EXISTS ix_logistics_route_stops_route_id RENAME TO ix_abasc_route_stops_route_id")

    # 2. Reverter tabelas
    op.rename_table('logistics_route_stops', 'abasc_route_stops')
    op.rename_table('logistics_routes', 'abasc_routes')
