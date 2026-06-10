import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.main import get_session
from app.core.dependencies import AccessTokenBearer, SessionDep
from .schemas import TodosCreate, TodosUpdate
from .models import Todos
from .services import TodosServices


todos_router = APIRouter(prefix="/todos", tags=["Todos"])

# Fix 5: service injected via Depends — not instantiated at module level
def get_todos_services() -> TodosServices:
    return TodosServices()

TodosServicesDep = Annotated[TodosServices, Depends(get_todos_services)]
access_token_bearer = AccessTokenBearer()


@todos_router.get("/", response_model=list[Todos], status_code=status.HTTP_200_OK)
async def get_all_todoss(
    service: TodosServicesDep,
    session: SessionDep,
    token_data=Depends(access_token_bearer),
):
    return await service.get_all(session)


@todos_router.post("/", response_model=Todos, status_code=status.HTTP_201_CREATED)
async def create_todos(
    data: TodosCreate,
    service: TodosServicesDep,
    session: SessionDep,
    token_data=Depends(access_token_bearer),
):
    return await service.create(session, data)


@todos_router.get("/{item_id}", response_model=Todos, status_code=status.HTTP_200_OK)
async def get_todos_by_id(
    item_id: uuid.UUID,
    service: TodosServicesDep,
    session: SessionDep,
    token_data=Depends(access_token_bearer),
):
    item = await service.get_by_id(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "code": "TODO_NOT_FOUND",
            "message": "Todos not found"
        })
    return item


@todos_router.put("/{item_id}", response_model=Todos, status_code=status.HTTP_200_OK)
async def update_todos(
    item_id: uuid.UUID,
    data: TodosUpdate,
    service: TodosServicesDep,
    session: SessionDep,
    token_data=Depends(access_token_bearer),
):
    item = await service.update(session, item_id, data)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "code": "TODO_NOT_FOUND",
            "message": "Todos not found"
        })
    return item


@todos_router.delete("/{item_id}", response_model=Todos, status_code=status.HTTP_200_OK)
async def delete_todos(
    item_id: uuid.UUID,
    service: TodosServicesDep,
    session: SessionDep,
    token_data=Depends(access_token_bearer),
):
    item = await service.delete(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "code": "TODO_NOT_FOUND",
            "message": "Todos not found"
        })
    return item
