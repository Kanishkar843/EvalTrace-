from alembic import op
import sqlalchemy as sa
import json
revision="0001"
down_revision=None
branch_labels=None
depends_on=None
STATEMENTS=['CREATE TABLE IF NOT EXISTS datasets (id VARCHAR(64) PRIMARY KEY, name VARCHAR(200), version VARCHAR(64) NOT NULL, cases TEXT NOT NULL, created_at VARCHAR(40), UNIQUE(name,version))', 'CREATE TABLE IF NOT EXISTS runs (id VARCHAR(64) PRIMARY KEY, dataset_id VARCHAR(64) REFERENCES datasets(id), target VARCHAR(40), status VARCHAR(40), result TEXT, created_at VARCHAR(40))', 'CREATE TABLE IF NOT EXISTS gate_policies (id INTEGER PRIMARY KEY, policy TEXT NOT NULL)']
POLICY={'structured_validity': 1.0, 'tool_accuracy': 1.0, 'recall_at_5': 0.8, 'ndcg_at_10': 0.8, 'citation_reference_validity': 1.0, 'task_completion': 1.0}
def upgrade():
    c=op.get_bind()
    for ddl in STATEMENTS:c.execute(sa.text(ddl))
    c.execute(sa.text("INSERT INTO gate_policies VALUES (1,:p) ON CONFLICT(id) DO NOTHING"),{"p":json.dumps(POLICY)})
def downgrade():
    raise RuntimeError("Restore backup; destructive downgrade unsupported")
