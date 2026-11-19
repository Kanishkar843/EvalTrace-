from app.engine import Engine
revision='0001'
down_revision=None
branch_labels=None
depends_on=None
def upgrade():Engine().migrate()
def downgrade():raise RuntimeError('Restore a backup; destructive downgrade unsupported')
