"""add_pago_prestamo_pendiente_enum

Revision ID: b01d340bd90e
Revises: d7e8f9a0b1c2
Create Date: 2025-12-21 14:36:25.197372

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b01d340bd90e'
down_revision = 'd7e8f9a0b1c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agregar valores faltantes al enum tipotransaccion
    op.execute("ALTER TYPE tipotransaccion ADD VALUE 'pago_prestamos'")
    op.execute("ALTER TYPE tipotransaccion ADD VALUE 'pago_prestamo_pendiente'")


def downgrade() -> None:
    # Nota: PostgreSQL no permite remover valores de enum fácilmente.
    # En producción, se necesitaría recrear la tabla o usar un approach diferente.
    pass
