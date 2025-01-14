import asyncio

from alembic import context
from app.models.base import Base
from app.models import *  # noqa
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine

target_metadata = Base.metadata


def run_migrations(connection):
    context.configure(
        connection=connection,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema=target_metadata.schema,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_async_engine(settings.SQLALCHEMY_DATABASE_URI.unicode_string(), future=True)

    async with connectable.connect() as connection:
        await connection.run_sync(run_migrations)


asyncio.run(run_migrations_online())
