from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.config import Config



engine = create_async_engine(
    url=Config.DATABASE_URL,
    echo=True,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """
    Called at startup — verifies the DB connection only.
    """
    async with engine.begin() as conn:
        await conn.run_sync(lambda _: None)  # health check only


async def get_session():
    """
    FastAPI dependency — yields an async DB session per request.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
