from sqlalchemy import delete, exists, func, select, or_

from app.core.db import DbConnection
from app.daos.base import BaseDao
from app.models.user import User
from app.schemas.user import UserBase


class UserDao(BaseDao):
    def __init__(self, db_connection: DbConnection) -> None:
        self.session = db_connection.session
        self.columns = User.__table__.c.keys()

    async def create(self, user_data: UserBase) -> User:
        _data = user_data.model_dump(include=set(self.columns))
        _user = User(**_data)
        self.session.add(_user)
        await self.session.commit()
        await self.session.refresh(_user)
        return _user

    async def get_by_id(self, user_id: int) -> User | None:
        statement = select(User).where(User.id == user_id)
        return await self.session.scalar(statement=statement)

    async def get_by_email(self, email) -> User | None:
        statement = select(User).where(User.email == email)
        return await self.session.scalar(statement=statement)

    async def get_by_identity(self, identity: str) -> User | None:
        statement = select(User).where(User.identity == identity)
        return await self.session.scalar(statement=statement)

    async def get_all(self) -> list[User]:
        statement = select(User).order_by(User.id)
        result = await self.session.execute(statement=statement)
        return result.scalars().all()

    async def get_by_referral_id(self, referral_id: str, limit: int, offset: int) -> tuple[int, list[User]]:
        query = select(
            User
        ).filter(User.referral_id == referral_id).limit(limit).offset(offset)
        result = await self.session.execute(query)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        users = result.scalars().all()
        return total, users

    async def delete_all(self) -> None:
        await self.session.execute(delete(User))
        await self.session.commit()

    async def delete_by_id(self, user_id: int) -> User | None:
        _user = await self.get_by_id(user_id=user_id)
        statement = delete(User).where(User.id == user_id)
        await self.session.execute(statement=statement)
        await self.session.commit()
        return _user

    async def exists(self, identity: str, email: str) -> bool:
        return await self.session.scalar(
            exists(
                select(User)
                .where(
                    or_(User.email == email, User.identity == identity)
                )
            ).select()
        )
