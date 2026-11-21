import os
from alembic import context
from sqlalchemy import create_engine
engine=create_engine(os.getenv("DATABASE_URL","sqlite:///./evaltrace.db"))
with engine.connect() as connection:
    context.configure(connection=connection)
    with context.begin_transaction():context.run_migrations()
