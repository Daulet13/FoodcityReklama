"""remove payment_type from realization

Revision ID: e74b5588a901
Revises: 87637e09c7ec
Create Date: 2025-10-30 14:12:37.066674

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e74b5588a901'
down_revision = '87637e09c7ec'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite не поддерживает ALTER TABLE DROP COLUMN напрямую
    # Но так как это development окружение, можно воссоздать таблицу
    with op.batch_alter_table('realization', schema=None) as batch_op:
        batch_op.drop_column('payment_type')


def downgrade():
    with op.batch_alter_table('realization', schema=None) as batch_op:
        batch_op.add_column(sa.Column('payment_type', sa.VARCHAR(length=20), nullable=True))
