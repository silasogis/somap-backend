"""initial schema

Revision ID: 0001
"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # Criar o enum userrole antes de usá-lo na tabela
    op.execute("CREATE TYPE userrole AS ENUM ('admin', 'editor', 'viewer')")
    op.execute("CREATE TYPE layertype AS ENUM ('wms', 'wfs', 'geojson', 'xyz')")

    op.create_table("users",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String, nullable=False),
        sa.Column("role", sa.Enum("admin", "editor", "viewer",
                                  name="userrole", create_type=False),
                  nullable=False, server_default="viewer"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table("workspaces",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.Text, server_default=""),
    )

    op.create_table("layers",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("workspace_id", sa.String, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("visible", sa.Boolean, server_default="true"),
        sa.Column("opacity", sa.Float, server_default="1.0"),
        sa.Column("z_index", sa.Integer, server_default="0"),
        sa.Column("style", sa.JSON, nullable=True),
        sa.Column("source", sa.JSON, nullable=False),
        sa.Column("bbox", sa.JSON, nullable=True),
        sa.Column("attribution", sa.String(300), nullable=True),
        sa.Column("geometry", geoalchemy2.types.Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True),
    )
    
    op.create_index("ix_layers_workspace_id", "layers", ["workspace_id"])
    op.execute("CREATE INDEX ix_layers_geometry ON layers USING GIST (geometry)")

def downgrade():
    op.execute("DROP TYPE IF EXISTS layertype")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.drop_table("layers")
    op.drop_table("workspaces")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
