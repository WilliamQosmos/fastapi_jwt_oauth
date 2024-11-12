from abc import abstractmethod
from typing import Protocol

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

postgres_url = settings.SQLALCHEMY_DATABASE_URI.unicode_string()

engine = create_async_engine(postgres_url, echo=False, future=True)
AsyncSessionFactory = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
    class_=AsyncSession,
)


class BaseDbConnection(Protocol):
    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError


class DbConnection(BaseDbConnection):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def close(self) -> None:
        await self.session.close()
