from datetime import datetime, timezone
from fastapi import HTTPException, status

import logging

from jose import JWTError, jwt
from sqlalchemy import and_, select

from app.core.config import settings
from app.core.db import DbConnection
from app.daos.user import UserDao
from app.models.referrers import Referrer
from app.models.user import User as UserModel
from app.schemas.token import TokenData
from app.schemas.user import UserIn
from app.services.redis import RedisService
from app.services.security import SecurityService


class AuthService:
    def __init__(self, db_connection: DbConnection, redis_service: RedisService):
        self.session = db_connection.session
        self.redis_service = redis_service
        self.security_service = SecurityService()
        self.user_dao = UserDao(db_connection=db_connection)

    async def register_user(self, user_data: UserIn) -> UserModel:
        user_exist = await self.user_email_exists(user_data.email)

        if user_exist:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Bad Request",
                        "error_description": "User already exists"},
            )

        if user_data.referrer_id:
            cache = await self.redis_service.get_cache(key=user_data.referrer_id)
            if cache:
                cache: Referrer
                if cache.until_at < datetime.now(timezone.utc):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"error": "Bad Request",
                                "error_description": "Referrer ID has expired"},
                    )
            else:
                referrer = await self.session.scalar(
                    select(Referrer)
                    .where(
                        and_(Referrer.referrer_id == user_data.referrer_id,
                             Referrer.until_at > datetime.now(timezone.utc))
                    )
                )
                if not referrer:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"error": "Bad Request",
                                "error_description": "Referrer ID does not exists or has expired"},
                    )
                await self.redis_service.set_cache(
                    key=user_data.referrer_id, value=referrer)

        user_data.password = self.security_service.get_password_hash(
            user_data.password)
        new_user = await self.user_dao.create(user_data)
        logging.info(f"New user created successfully: {new_user}!!!")
        return new_user

    async def authenticate_user(self, email: str, password: str) -> UserModel | bool:
        _user = await self.user_dao.get_by_email(email)
        if not _user or not self.security_service.verify_password(password, _user.password):
            return False
        return _user

    async def user_email_exists(self, email: str) -> UserModel | None:
        _user = await self.user_dao.get_by_email(email)
        return _user if _user else None

    async def login(self, email: str, password: str) -> UserModel:
        _user = await self.authenticate_user(email, password)
        if not _user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Bad Request",
                        "error_description": "Incorrect email or password"},
            )

        return _user

    async def get_current_user(self, token: str) -> UserModel:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Unauthorized",
                    "error_description": "Could not validate credentials"},
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[
                                 self.security_service.ALGORITHM])
            email: str = payload.get("sub")
            if not email:
                raise credentials_exception
            token_data = TokenData(email=email)
        except JWTError:
            raise credentials_exception
        _user = await self.user_dao.get_by_email(email=token_data.email)
        if not _user:
            raise credentials_exception
        return _user
