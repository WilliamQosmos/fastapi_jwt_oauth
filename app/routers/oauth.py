from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from starlette.requests import Request

from app.services.security import OAuth2Providers

router = APIRouter(prefix="/oauth2")


@router.get("/{provider}/authorize")
def authorize(request: Request, provider: OAuth2Providers):
    if request.auth.ssr:
        return request.auth.clients[provider.value].authorization_redirect(request)
    return dict(url=request.auth.clients[provider.value].authorization_url(request))


@router.get("/{provider}/token")
async def token(request: Request, provider: OAuth2Providers):
    if request.auth.ssr:
        return await request.auth.clients[provider.value].token_redirect(request)
    return await request.auth.clients[provider.value].token_data(request)


@router.get("/logout")
def logout(request: Request):
    response = RedirectResponse(request.base_url)
    response.delete_cookie("Authorization")
    return response
