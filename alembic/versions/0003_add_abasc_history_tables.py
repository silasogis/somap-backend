"""add abasc history tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-23 13:46:00.000000

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create abasc_routes table
    op.create_table("abasc_routes",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("route_date", sa.Date, nullable=False),
        sa.Column("driver_name", sa.String(120), nullable=False),
        sa.Column("driver_phone", sa.String(20), nullable=True),
        sa.Column("vehicle", sa.String(80), nullable=True),
        sa.Column("total_distance_km", sa.Float, nullable=False),
        sa.Column("total_duration_minutes", sa.Integer, nullable=False),
        sa.Column("google_maps_url", sa.Text, nullable=True),
        sa.Column("geom_route", geoalchemy2.types.Geometry(geometry_type="MULTILINESTRING", srid=4326), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    # Spatial index for routes geometry
    op.execute("CREATE INDEX ix_abasc_routes_geom ON abasc_routes USING GIST (geom_route)")

    # 2. Create abasc_route_stops table
    op.create_table("abasc_route_stops",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("route_id", sa.String, sa.ForeignKey("abasc_routes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stop_order", sa.Integer, nullable=False),
        sa.Column("stop_type", sa.String(20), nullable=False),
        sa.Column("item_name", sa.String(120), nullable=True),
        sa.Column("donor_name", sa.String(120), nullable=True),
        sa.Column("address", sa.Text, nullable=False),
        sa.Column("geom_stop", geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    # Spatial index for stops geometry
    op.execute("CREATE INDEX ix_abasc_route_stops_geom ON abasc_route_stops USING GIST (geom_stop)")
    op.create_index("ix_abasc_route_stops_route_id", "abasc_route_stops", ["route_id"])

def downgrade():
    op.drop_index("ix_abasc_route_stops_route_id", table_name="abasc_route_stops")
    op.execute("DROP INDEX IF EXISTS ix_abasc_route_stops_geom")
    op.drop_table("abasc_route_stops")

    op.execute("DROP INDEX IF EXISTS ix_abasc_routes_geom")
    op.drop_table("abasc_routes")
