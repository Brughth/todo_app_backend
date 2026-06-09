from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.main import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    await init_db()
    yield
    print("Shutting down...")


app = FastAPI(
    title="TODO APP",
    version="1.0.0",
    lifespan=lifespan,
)

# Register routers here:
# from app.features.auth.routes import auth_router
# app.include_router(auth_router)
