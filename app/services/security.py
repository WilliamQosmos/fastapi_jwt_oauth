from enum import Enum
from typing import Awaitable, Callable, Tuple
from fastapi import HTTPException, Request, status
from fastapi.openapi.models import HTTPBearer as HTTPBearerModel
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security.http import HTTPBase
from fastapi.security.utils import get_authorization_scheme_param
from jose import JOSEError

from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.authentication import AuthenticationBackend
from starlette.requests import HTTPConnection
from starlette.authentication import AuthenticationError
from starlette.responses import Response
from starlette.types import Scope, Send, Receive, ASGIApp

from fastapi_oauth2.middleware import Auth, User
from fastapi_oauth2.config import OAuth2Config
from fastapi_oauth2.core import OAuth2Core

from dishka import Scope as DIScope

from datetime import datetime
from datetime import timezone

import bcrypt

from app.core.db import DbConnection
from app.daos.user import UserDao
from app.schemas.user import UserBase


class SecurityService:
    def get_password_hash(self, password: str) -> str:
        pwd_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
        return hashed_password.decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        password_byte_enc = plain_password.encode("utf-8")
        return bcrypt.checkpw(password=password_byte_enc, hashed_password=hashed_password.encode("utf-8"))


class HTTPBearer(HTTPBase):
    def __init__(
        self,
        *,
        bearerFormat: str | None = None,
        scheme_name: str | None = None,
        description: str | None = None,
        auto_error: bool = True,
    ):
        self.model = HTTPBearerModel(bearerFormat=bearerFormat, description=description)
        self.scheme_name = scheme_name or self.__class__.__name__
        self.auto_error = auto_error

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        authorization = request.headers.get("Authorization")
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"error": "Unauthorized", "error_description": "Token not provided"},
                )
            else:
                return None
        if scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error": "Forbidden", "error_description": "Invalid token schema"},
                )
            else:
                return None
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)


class OAuth2Providers(str, Enum):
    github = "github"
    google = "google-oauth2"


class OAuth2Backend(AuthenticationBackend):
    """Authentication backend for AuthenticationMiddleware."""

    def __init__(
            self,
            config: OAuth2Config,
            callback: Callable[[Auth, User, Request], Awaitable[None] | None] = None,
    ) -> None:
        Auth.ssr = config.enable_ssr
        Auth.http = config.allow_http
        Auth.secret = config.jwt_secret
        Auth.expires = config.jwt_expires
        Auth.same_site = config.same_site
        Auth.algorithm = config.jwt_algorithm
        Auth.clients = {
            client.backend.name: OAuth2Core(client)
            for client in config.clients
        }
        self.callback = callback

    async def authenticate(self, request: Request) -> Tuple[Auth, User] | None:
        authorization = request.headers.get(
            "Authorization",
            request.cookies.get("Authorization"),
        )
        scheme, param = get_authorization_scheme_param(authorization)

        if not scheme or not param:
            return Auth(), User()

        try:
            token_data = Auth.jwt_decode(param)
        except JOSEError as e:
            raise AuthenticationError(str(e))
        if token_data["exp"] and token_data["exp"] < int(datetime.now(timezone.utc).timestamp()):
            raise AuthenticationError("Token expired")

        user = User(token_data)
        auth = Auth(user.pop("scope", []))
        auth.provider = auth.clients.get(user.get("provider"))
        claims = auth.provider.claims if auth.provider else {}

        if callable(self.callback):
            coroutine = self.callback(auth, user.use_claims(claims), request)
            if issubclass(type(coroutine), Awaitable):
                await coroutine
        return auth, user.use_claims(claims)


class OAuth2Middleware:
    """Wrapper for the Starlette AuthenticationMiddleware."""

    auth_middleware: AuthenticationMiddleware = None

    def __init__(
            self,
            app: ASGIApp,
            config: OAuth2Config | dict,
            callback: Callable[[Auth, User, Request], Awaitable[None] | None] = None,
            on_error: Callable[[HTTPConnection, AuthenticationError], Response] | None = None,
    ) -> None:
        """Initiates the middleware with the given configuration.

        :param app: FastAPI application instance
        :param config: middleware configuration
        :param callback: callback function to be called after authentication
        """
        if isinstance(config, dict):
            config = OAuth2Config(**config)
        elif not isinstance(config, OAuth2Config):
            raise TypeError("config is not a valid type")
        self.default_application_middleware = app
        on_error = on_error or AuthenticationMiddleware.default_on_error
        self.auth_middleware = AuthenticationMiddleware(app, backend=OAuth2Backend(config, callback), on_error=on_error)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            return await self.auth_middleware(scope, receive, send)
        await self.default_application_middleware(scope, receive, send)


async def on_auth(auth: Auth, user: User, request: Request):
    context = {Request: request}
    di_scope = DIScope.REQUEST
    async with request.app.state.dishka_container(context, scope=di_scope) as container:
        conn = await container.get(DbConnection)
        user_dao = UserDao(db_connection=conn)
        if user.identity and not await user_dao.exists(user.identity, user.email):
            await user_dao.create(UserBase(email=user.email, name=user.name, identity=user.identity))
