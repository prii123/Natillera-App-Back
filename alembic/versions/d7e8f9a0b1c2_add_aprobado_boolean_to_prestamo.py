"""Add aprobado boolean field to Prestamo

Revision ID: d7e8f9a0b1c2
Revises: c1a2b3c4d5e6
Create Date: 2025-12-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd7e8f9a0b1c2'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('prestamos', sa.Column('aprobado', sa.Boolean(), nullable=True, server_default=None))

def downgrade():
    op.drop_column('prestamos', 'aprobado')
