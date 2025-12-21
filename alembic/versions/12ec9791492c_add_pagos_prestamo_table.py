"""add_pagos_prestamo_table

Revision ID: 12ec9791492c
Revises: b01d340bd90e
Create Date: 2025-12-21 15:19:13.914917

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '12ec9791492c'
down_revision = 'b01d340bd90e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear tabla pagos_prestamo
    op.create_table('pagos_prestamo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('prestamo_id', sa.Integer(), nullable=False),
        sa.Column('monto', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('fecha_pago', sa.DateTime(), nullable=False),
        sa.Column('estado', sa.Enum('PENDIENTE', 'APROBADO', 'RECHAZADO', name='estadopago'), nullable=False),
        sa.Column('registrado_por', sa.Integer(), nullable=False),
        sa.Column('aprobado_por', sa.Integer(), nullable=True),
        sa.Column('fecha_aprobacion', sa.DateTime(), nullable=True),
        sa.Column('notas', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['aprobado_por'], ['users.id'], ),
        sa.ForeignKeyConstraint(['prestamo_id'], ['prestamos.id'], ),
        sa.ForeignKeyConstraint(['registrado_por'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pagos_prestamo_id'), 'pagos_prestamo', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_pagos_prestamo_id'), table_name='pagos_prestamo')
    op.drop_table('pagos_prestamo')
