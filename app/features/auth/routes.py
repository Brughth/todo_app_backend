import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.main import get_session
from app.core.dependencies import AccessTokenBearer, SessionDep
from .schemas import Auth, AuthCreate, AuthUpdate
from .services import AuthServices


auth_router = APIRouter(prefix="/auths", tags=["Auth"])

# Fix 5: service injected via Depends — not instantiated at module level
def get_auth_services() -> AuthServices:
    return AuthServices()

AuthServicesDep = Annotated[AuthServices, Depends(get_auth_services)]
access_token_bearer = AccessTokenBearer()


@auth_router.get("/", response_model=list[Auth], status_code=status.HTTP_200_OK)
async def get_all_auths(
    service: AuthServicesDep,
    session: SessionDep,
    current_user=Depends(access_token_bearer),
):
    return await service.get_all(session)


@auth_router.post("/", response_model=Auth, status_code=status.HTTP_201_CREATED)
async def create_auth(
    data: AuthCreate,
    service: AuthServicesDep,
    session: SessionDep,
    current_user=Depends(access_token_bearer),
):
    return await service.create(session, data)


@auth_router.get("/{item_id}", response_model=Auth, status_code=status.HTTP_200_OK)
async def get_auth_by_id(
    item_id: uuid.UUID,
    service: AuthServicesDep,
    session: SessionDep,
    current_user=Depends(access_token_bearer),
):
    item = await service.get_by_id(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth not found")
    return item


@auth_router.put("/{item_id}", response_model=Auth, status_code=status.HTTP_200_OK)
async def update_auth(
    item_id: uuid.UUID,
    data: AuthUpdate,
    service: AuthServicesDep,
    session: SessionDep,
    current_user=Depends(access_token_bearer),
):
    item = await service.update(session, item_id, data)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth not found")
    return item


@auth_router.delete("/{item_id}", response_model=Auth, status_code=status.HTTP_200_OK)
async def delete_auth(
    item_id: uuid.UUID,
    service: AuthServicesDep,
    session: SessionDep,
    current_user=Depends(access_token_bearer),
):
    item = await service.delete(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth not found")
    return item
