from datetime import datetime, timedelta, timezone
import secrets
import string
from typing import Annotated
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import EmailStr
from sqlalchemy import and_, delete, exists, select

from app.core.db import DbConnection
from app.daos.user import UserDao
from app.models.referrers import Referrer
from app.schemas.user import UserOut
from app.schemas.utils import ReferrerIdCommonParams, ResponseOffsetPagination
from app.services.redis import RedisService

router = APIRouter(route_class=DishkaRoute, tags=[
                   "Referrer"], prefix="/referrer")


@router.post("/create")
async def create_referrer(
    request: Request,
    until_at: datetime,
    db: FromDishka[DbConnection],
):
    if request.user.is_authenticated:
        user = await UserDao(db_connection=db).get_by_email(request.user.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Unauthorized",
                        "error_description": "Could not validate credentials"}
            )
        if await db.session.scalar(
            exists(
                select(Referrer)
                .where(
                    Referrer.user_id == user.id
                )
            ).select()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Bad Request",
                        "error_description": "Referrer ID already exists, you can only have one referrer ID"}
            )
        else:
            ref_id = ''.join(secrets.choice(
                string.ascii_letters + string.digits) for _ in range(10))
            db.session.add(
                Referrer(
                    user_id=user.id,
                    referrer_id=ref_id,
                    until_at=until_at or datetime.now(
                        timezone.utc) + timedelta(days=14),
                )
            )
            await db.session.commit()
            return {"ref_id": ref_id}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Unauthorized",
                    "error_description": "Could not validate credentials"}
        )


@router.post("/delete")
async def delete_referrer(
    request: Request,
    referrer_id: str,
    redis_service: FromDishka[RedisService],
    db: FromDishka[DbConnection],
):
    if request.user.is_authenticated:
        user = await UserDao(db_connection=db).get_by_email(request.user.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Unauthorized",
                        "error_description": "Could not validate credentials"}
            )
        if not await db.session.scalar(
            exists(
                select(Referrer)
                .where(
                    Referrer.user_id == user.id
                )
            ).select()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Bad Request",
                        "error_description": "Referrer ID does not exists for the user"}
            )
        _referrer = await db.session.scalar(
            select(Referrer)
            .where(
                Referrer.referrer_id == referrer_id
            )
        )
        if not _referrer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Bad Request",
                        "error_description": "Referrer ID does not exists"}
            )
        if _referrer.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Bad Request",
                        "error_description": "Referrer ID does not belongs to the user"}
            )
        await db.session.execute(
            delete(Referrer).where(
                and_(
                    Referrer.user_id == user.id,
                    Referrer.referrer_id == referrer_id
                )
            )
        )
        await db.session.commit()
        cache = await redis_service.get_cache(key=referrer_id)
        if cache:
            await redis_service.delete_cache(key=referrer_id)
        return {"message": "Referrer ID deleted"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Unauthorized",
                    "error_description": "Could not validate credentials"}
        )


@router.get("/get_referrer")
async def get_referrer(
    email: Annotated[EmailStr, Query()],
    db: FromDishka[DbConnection],
):
    user = await UserDao(db_connection=db).get_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Bad Request",
                    "error_description": "User does not exists"}
        )
    if not await db.session.scalar(
        exists(
            select(Referrer)
            .where(
                Referrer.user_id == user.id
            )
        ).select()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Bad Request",
                    "error_description": "Referrer ID does not exists for the user"}
        )
    _referrer = await db.session.scalar(
        select(Referrer)
        .where(
            and_(Referrer.user_id == user.id,
                 Referrer.until_at > datetime.now(timezone.utc))
        )
    )
    if not _referrer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Bad Request",
                    "error_description": "Does not have an active referrer ID"}
        )
    return {"ref_id": _referrer.referrer_id}


@router.get("/get_referrals")
async def get_referrals(
    filter_query: Annotated[ReferrerIdCommonParams, Query()],
    db: FromDishka[DbConnection],
) -> ResponseOffsetPagination[UserOut]:
    _referrer = await db.session.scalar(
        select(Referrer)
        .where(
            Referrer.referrer_id == filter_query.referrer_id
        )
    )
    if not _referrer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Bad Request",
                    "error_description": "Referrer ID does not exists"}
        )
    total, users = await UserDao(db_connection=db).get_by_referral_id(
        filter_query.referrer_id,
        filter_query.limit,
        filter_query.offset
    )
    return ResponseOffsetPagination(total=total, offset=filter_query.offset, limit=filter_query.limit, items=users)
