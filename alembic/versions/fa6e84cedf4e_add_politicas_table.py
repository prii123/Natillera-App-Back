"""add politicas table

Revision ID: fa6e84cedf4e
Revises: c0175bb9778b
Create Date: 2025-12-23 09:22:43.766377

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fa6e84cedf4e'
down_revision = 'c0175bb9778b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear tabla de políticas
    op.create_table('politicas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('natillera_id', sa.Integer(), nullable=False),
        sa.Column('titulo', sa.String(), nullable=False),
        sa.Column('descripcion', sa.String(), nullable=False),
        sa.Column('orden', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['natillera_id'], ['natilleras.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_politicas_id'), 'politicas', ['id'], unique=False)


def downgrade() -> None:
    # Eliminar tabla de políticas
    op.drop_index(op.f('ix_politicas_id'), table_name='politicas')
    op.drop_table('politicas')
