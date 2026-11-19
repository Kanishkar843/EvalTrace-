from alembic import context
from app.engine import Engine
engine=Engine()
with engine.db.connect() as connection:
    context.configure(connection=connection)
    with context.begin_transaction():context.run_migrations()
