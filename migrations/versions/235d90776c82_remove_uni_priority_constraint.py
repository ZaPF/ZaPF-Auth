"""

Remove unique constraint

Revision ID: 235d90776c82
Revises: 257e0b50e1b2
Create Date: 2017-04-02 16:21:47.112784

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '235d90776c82'
down_revision = '257e0b50e1b2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('registration', naming_convention = naming_convention) as batch_op:
        batch_op.drop_constraint('uq_registration_priority_uni', type_='unique')


def downgrade():
    with op.batch_alter_table('registration', naming_convention = naming_convention) as batch_op:
        batch_op.create_unique_constraint('uq_registration_priority_uni', ['priority','uni_id'])
