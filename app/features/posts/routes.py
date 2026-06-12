from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Annotated
from app.features.posts.schemas import  PostCreate, PostUpdate
from app.features.posts.services import PostService
from app.core.pagination import PaginationParams, PaginatedResponse, PaginationDep
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.dependencies import AccessTokenBearer, SessionDep
from app.features.posts.models import Post


post_router = APIRouter(prefix="/posts", tags=["Posts"])

def get_post_services() -> PostService:
    return PostService()

PostServicesDep = Annotated[PostService, Depends(get_post_services)]

access_token_bearer = AccessTokenBearer()

@post_router.get("/", response_model=PaginatedResponse, status_code=status.HTTP_200_OK)
async def get_all_posts(
    service: PostServicesDep,
    session: SessionDep,
    params: PaginationDep,
    search: str | None = Query(None, min_length=1, description="Search term for title or description"),
    token_data: dict = Depends(access_token_bearer)
):
    return await service.get_all_posts(session, params, search)

@post_router.post("/", response_model=list[Post], status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: list[PostCreate],
    service: PostServicesDep,
    session: SessionDep,
    token_data: dict = Depends(access_token_bearer)
):
    return await service.create_post(session, post_data)

@post_router.get("/{post_id}", response_model=PostCreate, status_code=status.HTTP_200_OK)
async def get_post_by_id(
    post_id: str,
    service: PostServicesDep,
    session: SessionDep,
    token_data: dict = Depends(access_token_bearer)
):
    post = await service.get_post_by_id(session, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "code": "POST_NOT_FOUND",
            "message": "Post not found"
        })
    return post

@post_router.put("/{post_id}", response_model=PostCreate, status_code=status.HTTP_200_OK)
async def update_post(
    post_id: str,
    post_data: PostUpdate,
    service: PostServicesDep,
    session: SessionDep,
    token_data: dict = Depends(access_token_bearer)
):
    updated_post = await service.update_post(session, post_id, post_data)
    if not updated_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "code": "POST_NOT_FOUND",
            "message": "Post not found"
        })
    return updated_post

@post_router.delete("/{post_id}", response_model=PostCreate, status_code=status.HTTP_200_OK)
async def delete_post(
    post_id: str,
    service: PostServicesDep,
    session: SessionDep,
    token_data: dict = Depends(access_token_bearer)
):
    deleted_post = await service.delete_post(session, post_id)
    if not deleted_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "code": "POST_NOT_FOUND",
            "message": "Post not found"
        })
    return deleted_post