import os
from alembic import context
from sqlalchemy import create_engine, pool
from backend.app.auth import Base
# Register every ORM model without opening the application database.
from backend.app import ledger, payments, services, analytics

config = context.config
url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
