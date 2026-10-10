"""Persist host order without replacing IDs or group memberships."""
import sqlalchemy as sa
from alembic import op

revision = "yuku0013order"
down_revision = "yuku0012desc"
branch_labels = None
depends_on = None

def upgrade():
    columns = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('hosts')}
    if 'position' not in columns:
        op.add_column('hosts', sa.Column('position', sa.Integer(), nullable=False, server_default='0'))
        # IDs reproduce the previously observed order until a user reorders it.
        op.execute('UPDATE hosts SET position = id')

def downgrade():
    op.drop_column('hosts', 'position')
