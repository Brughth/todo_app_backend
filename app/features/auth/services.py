import uuid
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.security import generate_password_hash

from .models import User
from .schemas import  UserCreate


class AuthServices:
    
    async def get_user_by_email(
        self,
        db: AsyncSession,
        email: str
    ) -> User | None:
        result = await db.exec(
            select(User).where(User.email == email) 
        )
        user = result.first()
        return user if user else None
    
    async def get_user_by_id(
        self,
        db: AsyncSession,
        id: uuid.UUID
    ) -> User | None:
        result = await db.exec(
            select(User).where(User.id == id) 
        )
        user = result.first()
        return user if user else None
    

    async def create_user(
        self,
        db: AsyncSession,
        user_data: UserCreate
    ):
        user_create_dict = user_data.model_dump()
        
        new_user = User(**user_create_dict)
        
        new_user.password = generate_password_hash(user_data.password)
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user
    
    
