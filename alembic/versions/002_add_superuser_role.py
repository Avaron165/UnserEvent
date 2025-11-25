"""Add superuser role

Revision ID: 002_add_superuser_role
Revises: 001_initial
Create Date: 2024-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002_add_superuser_role'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add superuser role with highest privileges
    op.execute("""
        INSERT INTO roles (id, name, description) VALUES
        (gen_random_uuid(), 'superuser', 'Superuser with full access to all resources regardless of division membership')
    """)


def downgrade() -> None:
    op.execute("DELETE FROM roles WHERE name = 'superuser'")
