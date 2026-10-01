"""Configure the database search path for project schemas.

Revision ID: 003
Revises: 002
"""

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        r"""
        DO $$
        BEGIN
            EXECUTE format(
                'ALTER DATABASE %I SET search_path TO "$user", public, gtfs, osm',
                current_database()
            );
        END
        $$
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format(
                'ALTER DATABASE %I RESET search_path',
                current_database()
            );
        END
        $$
        """
    )
