import uuid
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession

from .models import Auth
from .schemas import AuthCreate, AuthUpdate


class AuthServices:

    async def get_all(self, session: AsyncSession) -> list[Auth]:
        statement = select(Auth).order_by(desc(Auth.created_at))
        result = await session.exec(statement)
        return result.all()

    async def get_by_id(self, session: AsyncSession, item_id: uuid.UUID) -> Auth | None:
        statement = select(Auth).where(Auth.id == item_id)
        result = await session.exec(statement)
        return result.first()

    async def create(self, session: AsyncSession, data: AuthCreate) -> Auth:
        item = Auth(**data.model_dump())
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item

    async def update(
        self,
        session: AsyncSession,
        item_id: uuid.UUID,
        data: AuthUpdate,
    ) -> Auth | None:
        item = await self.get_by_id(session, item_id)
        if item is None:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        await session.commit()
        await session.refresh(item)
        return item

    async def delete(self, session: AsyncSession, item_id: uuid.UUID) -> Auth | None:
        item = await self.get_by_id(session, item_id)
        if item is None:
            return None
        await session.delete(item)
        await session.commit()
        return item
