from typing import Annotated
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import EmailStr

from app.schemas.user import UserIn
from app.services.auth import AuthService

router = APIRouter(route_class=DishkaRoute, prefix="/auth")


@router.post("/login")
async def login(
    request: Request,
    email: Annotated[EmailStr, Form()],
    password: Annotated[str, Form(min_length=8)],
    auth_service: FromDishka[AuthService],
):
    user = await auth_service.login(email, password)
    access_token = request.auth.jwt_create({
        "id": user.id,
        "identity": user.identity,
        "email": user.email,
    })
    response = RedirectResponse("/")
    response.set_cookie(
        "Authorization",
        value=f"Bearer {access_token}",
        max_age=request.auth.expires,
        expires=request.auth.expires,
        httponly=request.auth.http,
        samesite=request.auth.same_site,
    )
    return response


@router.post("/register")
async def register(
    request: Request,
    user_data: UserIn,
    auth_service: FromDishka[AuthService],
):
    user = await auth_service.register_user(user_data)
    access_token = request.auth.jwt_create({
        "id": user.id,
        "identity": user.identity,
        "email": user.email,
    })
    response = RedirectResponse("/")
    response.set_cookie(
        "Authorization",
        value=f"Bearer {access_token}",
        max_age=request.auth.expires,
        expires=request.auth.expires,
        httponly=request.auth.http,
        samesite=request.auth.same_site,
    )
    return response


@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse("/")
    response.delete_cookie("Authorization")
    return response
