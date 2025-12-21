"""add estado to natilleras

Revision ID: 7d83b91f2c4a
Revises: 6bf82f83c6eb
Create Date: 2025-12-12 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7d83b91f2c4a'
down_revision = '6bf82f83c6eb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear el tipo ENUM para PostgreSQL
    natillera_estado = sa.Enum('activo', 'inactivo', name='natilleraestado')
    natillera_estado.create(op.get_bind(), checkfirst=True)
    
    # Agregar la columna estado con valor por defecto 'activo'
    op.add_column('natilleras', 
        sa.Column('estado', natillera_estado, nullable=False, server_default='activo')
    )


def downgrade() -> None:
    # Eliminar la columna estado
    op.drop_column('natilleras', 'estado')
    
    # Eliminar el tipo ENUM
    natillera_estado = sa.Enum('activo', 'inactivo', name='natilleraestado')
    natillera_estado.drop(op.get_bind(), checkfirst=True)
