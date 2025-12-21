"""add invitaciones table

Revision ID: 8e94c82d3f5b
Revises: 7d83b91f2c4a
Create Date: 2025-12-12 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8e94c82d3f5b'
down_revision = '7d83b91f2c4a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear tabla de invitaciones directamente (el enum se crea automáticamente si no existe)
    op.create_table('invitaciones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('natillera_id', sa.Integer(), nullable=False),
        sa.Column('invited_user_id', sa.Integer(), nullable=False),
        sa.Column('inviter_user_id', sa.Integer(), nullable=False),
        sa.Column('estado', sa.Enum('pendiente', 'aceptada', 'rechazada', name='invitacionestado'), nullable=False, server_default='pendiente'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['natillera_id'], ['natilleras.id'], ),
        sa.ForeignKeyConstraint(['invited_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['inviter_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invitaciones_id'), 'invitaciones', ['id'], unique=False)


def downgrade() -> None:
    # Eliminar tabla
    op.drop_index(op.f('ix_invitaciones_id'), table_name='invitaciones')
    op.drop_table('invitaciones')
    
    # Eliminar el tipo ENUM
    invitacion_estado = sa.Enum('pendiente', 'aceptada', 'rechazada', name='invitacionestado')
    invitacion_estado.drop(op.get_bind(), checkfirst=True)
