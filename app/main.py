from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.main import init_db
from app.features.auth.routes import auth_router
from app.features.todos.routes import todos_router
from app.features.posts.routes import post_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    await init_db()
    yield
    print("Shutting down...")


app = FastAPI(
    title="TODO APP",
    version="1.0.0",
    description="A simple TODO app built with FastAPI and SQLModel",
    lifespan=lifespan,
)

# Register routers here:

app.include_router(auth_router)
app.include_router(todos_router)

app.include_router(post_router)
