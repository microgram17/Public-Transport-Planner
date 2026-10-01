"""Enable PostGIS and create the OSM schema.

Revision ID: 002
Revises: 001
"""

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE SCHEMA IF NOT EXISTS osm")


def downgrade() -> None:
    # PostGIS and imported OSM data may be used outside this migration, so a
    # downgrade deliberately leaves both in place.
    pass
