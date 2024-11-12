from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from fastapi_oauth2.exceptions import OAuth2Error

from contextlib import asynccontextmanager

from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka

from app import __version__
from app.core.config import settings
from app.core.ioc import AdaptersProvider, InteractorProvider
from app.routers import api_router
from app.services.security import OAuth2Middleware, on_auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await app.state.dishka_container.close()


app = FastAPI(title=settings.PROJECT_NAME, docs_url=None, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.BASE_PATH_PREFIX)
app.add_middleware(OAuth2Middleware, config=settings.oauth2_config, callback=on_auth)
app.mount("/static", StaticFiles(directory="static"), name="static")

container = make_async_container(AdaptersProvider(), InteractorProvider())
setup_dishka(container, app)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    content = jsonable_encoder(
        {"error": "Validation error", "error_description": "Invalid input data", "fields": exc.errors()}
    )
    return JSONResponse(status_code=422, content=content)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    content = jsonable_encoder(
        {"error": exc.detail.get("error"), "error_description": exc.detail.get("error_description")}
    )
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(OAuth2Error)
async def error_handler(request: Request, e: OAuth2Error):
    print("An error occurred in OAuth2Middleware", e)
    return RedirectResponse(url="/", status_code=303)


@app.get("/specs", include_in_schema=False)
async def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/specs/openapi.json",
        title=settings.PROJECT_NAME,
    )


@app.get("/specs/openapi.json", include_in_schema=False)
async def openapi(req: Request) -> JSONResponse:
    openapi = get_openapi(
        title=settings.PROJECT_NAME,
        version=__version__,
        routes=app.routes,
    )
    return JSONResponse(openapi)
