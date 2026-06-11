import uuid
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.pagination import PaginationParams, PaginatedResponse, paginate
from .models import Todos
from .schemas import TodosCreate, TodosUpdate


class TodosServices:

    async def get_all(
        self, session: AsyncSession, params: PaginationParams, is_completed: bool | None = None
    ) -> PaginatedResponse:
        statement = select(Todos).order_by(desc(Todos.created_at))
        if is_completed is not None:
            statement = statement.where(Todos.is_completed == is_completed)
        return await paginate(session, statement, params)

    async def get_by_id(self, session: AsyncSession, item_id: uuid.UUID) -> Todos | None:
        statement = select(Todos).where(Todos.id == item_id)
        result = await session.exec(statement)
        return result.first()

    async def create(self, session: AsyncSession, data: TodosCreate) -> Todos:
        item = Todos(**data.model_dump())
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item

    async def update(
        self,
        session: AsyncSession,
        item_id: uuid.UUID,
        data: TodosUpdate,
    ) -> Todos | None:
        item = await self.get_by_id(session, item_id)
        if item is None:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        await session.commit()
        await session.refresh(item)
        return item

    async def delete(self, session: AsyncSession, item_id: uuid.UUID) -> Todos | None:
        item = await self.get_by_id(session, item_id)
        if item is None:
            return None
        await session.delete(item)
        await session.commit()
        return item
    
    async def mark_as_completed(
        self,
        session: AsyncSession,
        item_id: uuid.UUID,
    ):
        item = await self.get_by_id(session, item_id)
        if item is None:
            return None
        if item.is_completed:
            return item  # déjà complété, pas de changement
        item.is_completed = True
        await session.commit()
        await session.refresh(item)
        return item
    
    async def mark_as_uncompleted(
        self,
        session: AsyncSession,
        item_id: uuid.UUID,
    ):
        item = await self.get_by_id(session, item_id)
        if item is None:
            return None
        if not item.is_completed:
            return item  # déjà non complété, pas de changement
        item.is_completed = False
        await session.commit()
        await session.refresh(item)
        return item
