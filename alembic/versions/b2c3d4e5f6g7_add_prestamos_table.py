"""add prestamos table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-14 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear tabla de préstamos
    op.create_table('prestamos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('natillera_id', sa.Integer(), nullable=False),
        sa.Column('monto', sa.Numeric(10, 2), nullable=False),
        sa.Column('tasa_interes', sa.Numeric(5, 2), nullable=False),
        sa.Column('plazo_meses', sa.Integer(), nullable=False),
        sa.Column('fecha_inicio', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('fecha_vencimiento', sa.DateTime(), nullable=False),
        sa.Column('nombre_prestatario', sa.String(), nullable=False),
        sa.Column('telefono_prestatario', sa.String(), nullable=True),
        sa.Column('email_prestatario', sa.String(), nullable=True),
        sa.Column('direccion_prestatario', sa.String(), nullable=True),
        sa.Column('referente_id', sa.Integer(), nullable=False),
        sa.Column('estado', sa.Enum('activo', 'pagado', 'vencido', 'cancelado', name='estadoprestamo'), nullable=False, server_default='activo'),
        sa.Column('monto_pagado', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('notas', sa.String(), nullable=True),
        sa.Column('creado_por', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['natillera_id'], ['natilleras.id'], ),
        sa.ForeignKeyConstraint(['referente_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['creado_por'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prestamos_id'), 'prestamos', ['id'], unique=False)
    
    # Agregar columna prestamo_id a transacciones
    op.add_column('transacciones', sa.Column('prestamo_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_transacciones_prestamo_id', 'transacciones', 'prestamos', ['prestamo_id'], ['id'])


def downgrade() -> None:
    # Eliminar foreign key y columna de transacciones
    op.drop_constraint('fk_transacciones_prestamo_id', 'transacciones', type_='foreignkey')
    op.drop_column('transacciones', 'prestamo_id')
    
    # Eliminar tabla de préstamos
    op.drop_index(op.f('ix_prestamos_id'), table_name='prestamos')
    op.drop_table('prestamos')
    
    # Eliminar el tipo ENUM
    estado_prestamo = sa.Enum('activo', 'pagado', 'vencido', 'cancelado', name='estadoprestamo')
    estado_prestamo.drop(op.get_bind(), checkfirst=True)
