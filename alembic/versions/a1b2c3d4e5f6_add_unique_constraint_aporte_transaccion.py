"""add unique constraint aporte transaccion

Revision ID: a1b2c3d4e5f6
Revises: 9f83d7a4b1c2
Create Date: 2025-12-14 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '9f83d7a4b1c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Primero, eliminar duplicados existentes (mantener solo el más reciente de cada aporte)
    op.execute("""
        DELETE FROM transacciones 
        WHERE id IN (
            SELECT id FROM (
                SELECT id, 
                       ROW_NUMBER() OVER (PARTITION BY aporte_id ORDER BY id DESC) as rn
                FROM transacciones 
                WHERE aporte_id IS NOT NULL
            ) t
            WHERE t.rn > 1
        )
    """)
    
    # Crear índice único para aporte_id (permitiendo NULL)
    op.create_index(
        'ix_transacciones_aporte_id_unique', 
        'transacciones', 
        ['aporte_id'], 
        unique=True,
        postgresql_where=sa.text('aporte_id IS NOT NULL')
    )


def downgrade() -> None:
    # Eliminar índice único
    op.drop_index('ix_transacciones_aporte_id_unique', table_name='transacciones')
