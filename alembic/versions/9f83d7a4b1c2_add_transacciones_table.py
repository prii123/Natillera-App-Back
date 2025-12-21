"""add transacciones table

Revision ID: 9f83d7a4b1c2
Revises: 8e94c82d3f5b
Create Date: 2025-12-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f83d7a4b1c2'
down_revision = '8e94c82d3f5b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear tabla de transacciones
    op.create_table('transacciones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('natillera_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.Enum('efectivo', 'prestamo', 'ingreso', 'gasto', name='tipotransaccion'), nullable=False),
        sa.Column('categoria', sa.String(), nullable=False),
        sa.Column('monto', sa.Numeric(10, 2), nullable=False),
        sa.Column('descripcion', sa.String(), nullable=True),
        sa.Column('fecha', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('creado_por', sa.Integer(), nullable=False),
        sa.Column('aporte_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['natillera_id'], ['natilleras.id'], ),
        sa.ForeignKeyConstraint(['creado_por'], ['users.id'], ),
        sa.ForeignKeyConstraint(['aporte_id'], ['aportes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transacciones_id'), 'transacciones', ['id'], unique=False)


def downgrade() -> None:
    # Eliminar tabla
    op.drop_index(op.f('ix_transacciones_id'), table_name='transacciones')
    op.drop_table('transacciones')
    
    # Eliminar el tipo ENUM
    tipo_transaccion = sa.Enum('efectivo', 'prestamo', 'ingreso', 'gasto', name='tipotransaccion')
    tipo_transaccion.drop(op.get_bind(), checkfirst=True)
