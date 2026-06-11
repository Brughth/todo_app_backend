from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.sql.selectable import Select
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

T = TypeVar("T")


# ── Query params (réutilisable via Depends) ───────────────────────────────────

class PaginationParams(BaseModel):
    page: int
    per_page: int


def pagination_params(
    page: int = Query(1, ge=1, description="Numéro de page (commence à 1)"),
    per_page: int = Query(20, ge=1, le=100, description="Éléments par page (max 100)"),
) -> PaginationParams:
    return PaginationParams(page=page, per_page=per_page)


PaginationDep = Annotated[PaginationParams, Depends(pagination_params)]


# ── Réponse paginée générique ─────────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    total: int          # nombre total d'éléments
    per_page: int       # éléments par page
    current_page: int   # page demandée
    total_pages: int    # nombre total de pages
    data: list[T]       # les éléments de la page


# ── Helper ────────────────────────────────────────────────────────────────────

async def paginate(
    session: AsyncSession,
    statement: Select,
    params: PaginationParams,
) -> PaginatedResponse:
    """Applique COUNT + offset/limit sur un statement SELECT et renvoie une page."""
    # Total (sans offset/limit), en réutilisant le statement comme sous-requête
    count_statement = select(func.count()).select_from(statement.subquery())
    total = (await session.exec(count_statement)).one()

    # Slice de la page courante
    offset = (params.page - 1) * params.per_page
    page_statement = statement.offset(offset).limit(params.per_page)
    items = (await session.exec(page_statement)).all()

    total_pages = (total + params.per_page - 1) // params.per_page if total else 0

    return PaginatedResponse(
        total=total,
        per_page=params.per_page,
        current_page=params.page,
        total_pages=total_pages,
        data=items,
    )
