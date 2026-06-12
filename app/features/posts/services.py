from sqlalchemy.ext.asyncio import AsyncSession
from app.features.posts.models import Post
from app.features.posts.schemas import PostCreate, PostUpdate
from app.core.pagination import PaginationParams, PaginatedResponse, paginate
from sqlmodel import select, desc, col
import uuid


class PostService:
    
    async def get_all_posts(
        self,
        db: AsyncSession,
        params: PaginationParams,
        search: str | None = None,
    ) -> PaginatedResponse:
        
        statement = select(Post).order_by(desc(Post.created_at))
        
        if search:
            statement = statement.filter(
                col(Post.title).ilike(f"%{search}%") | (col(Post.description).ilike(f"%{search}%") | (col(Post.create_by).ilike(f"%{search}%")))
            )
        return await paginate(db, statement, params)
    
    async def get_post_by_id(self, db: AsyncSession, post_id: uuid.UUID) -> Post | None:
        return await db.get(Post, post_id)
    
    async def create_post(
        self,
        db: AsyncSession,
        post_data: list[PostCreate]
    ) -> list[Post]:
        new_posts = [Post(**data.model_dump()) for data in post_data]
        db.add_all(new_posts)
        await db.commit()
        for post in new_posts:
            await db.refresh(post)
        return new_posts
    
    async def update_post(
        self,
        db: AsyncSession,
        post_id: uuid.UUID,
        post_data: PostUpdate
    ) -> Post | None:
        post = await self.get_post_by_id(db, post_id)
        if not post:
            return None
        
        for key, value in post_data.model_dump(exclude_unset=True).items():
            setattr(post, key, value)
        
        await db.commit()
        await db.refresh(post)
        return post

    async def delete_post(self, db: AsyncSession, post_id: uuid.UUID) -> Post | None:
        post = await self.get_post_by_id(db, post_id)
        if not post:
            return None
        
        await db.delete(post)
        await db.commit()
        return post
    
        
        
        
    