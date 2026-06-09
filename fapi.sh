#!/usr/bin/env bash
# =============================================================================
#  fapi — FastAPI project scaffold CLI
#
#  Usage:
#    fapi init                        Init full project scaffold + install packages
#    fapi feature <name>              Add a feature module (router + service + schemas + model)
#    fapi feature <name> --no-router  Add feature without HTTP router
#
#  Stack:
#    FastAPI + SQLModel + Alembic + PostgreSQL (async) + Redis + Celery
#    PyJWT · pwdlib[argon2] · pydantic-settings
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

log_info()    { echo -e "${CYAN}  ->  ${RESET} $1"; }
log_success() { echo -e "${GREEN}  ok  ${RESET} $1"; }
log_warning() { echo -e "${YELLOW}  !!  ${RESET} $1"; }
log_error()   { echo -e "${RED}  xx  ${RESET} $1"; }
log_section() { echo -e "\n${BOLD}${CYAN}>> $1${RESET}"; }

mkf() {
  local path="$1" content="$2"
  mkdir -p "$(dirname "$path")"
  if [[ -f "$path" ]]; then
    log_warning "exists - skipped: $path"
  else
    printf '%s' "$content" > "$path"
    log_success "$path"
  fi
}

mkd() { mkdir -p "$1"; log_info "dir: $1"; }

to_pascal() {
  echo "$1" | awk -F'_' '{
    result=""
    for(i=1; i<=NF; i++) {
      result = result toupper(substr($i,1,1)) substr($i,2)
    }
    print result
  }'
}

# ==============================================================================
#  COMMAND: init
# ==============================================================================
cmd_init() {
  log_section "Initializing FastAPI scaffold"

  # ── Directories ──────────────────────────────────────────────────────────────
  log_section "Directories"
  mkd "app/core"
  mkd "app/db"
  mkd "app/features"

  log_section "Files"

  # ── app/__init__.py ───────────────────────────────────────────────────────────
  mkf "app/__init__.py" ""

  # ── app/main.py ───────────────────────────────────────────────────────────────
  mkf "app/main.py" 'from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.main import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    await init_db()
    yield
    print("Shutting down...")


app = FastAPI(
    title="App",
    version="1.0.0",
    lifespan=lifespan,
)

# Register routers here:
# from app.features.auth.routes import auth_router
# app.include_router(auth_router)
'

  # ── app/core/config.py ────────────────────────────────────────────────────────
  mkf "app/core/config.py" 'from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Database ────────────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── Auth ────────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Redis ────────────────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


Config = Settings()
'

  # ── app/db/__init__.py ────────────────────────────────────────────────────────
  mkf "app/db/__init__.py" ""

  # ── app/db/main.py ────────────────────────────────────────────────────────────
  mkf "app/db/main.py" 'from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.config import Config


# ── Fix 1: create_async_engine — not AsyncEngine(create_engine()) ─────────────
engine = create_async_engine(
    url=Config.DATABASE_URL,
    echo=True,
)

# ── Fix 2: sessionmaker created ONCE at module level, not per request ──────────
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
'

  # ── app/db/redis.py ────────────────────────────────────────────────────────────
  mkf "app/db/redis.py" 'from redis.asyncio import Redis
from app.core.config import Config


token_blocklist = Redis(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=0,
    decode_responses=True,
)


async def add_jti_to_blocklist(jti: str, ttl: int) -> None:
    """
    Add a token JTI to the Redis blocklist.

    Fix 7: ttl is dynamic — equals the remaining lifetime of the token.
    Redis auto-deletes the key after ttl seconds, so no manual cleanup needed.

    Usage:
        exp = token_data["exp"]
        ttl = exp - int(datetime.now(timezone.utc).timestamp())
        if ttl > 0:
            await add_jti_to_blocklist(jti, ttl=ttl)
    """
    await token_blocklist.set(
        name=jti,
        value="revoked",
        ex=ttl,
    )


async def is_token_in_blocklist(jti: str) -> bool:
    """Return True if the JTI has been revoked."""
    value = await token_blocklist.get(jti)
    return value is not None
'

  # ── app/core/security.py ──────────────────────────────────────────────────────
  mkf "app/core/security.py" 'import uuid
import logging
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import Config

password_hash = PasswordHash.recommended()


# ── Password ──────────────────────────────────────────────────────────────────

def generate_password_hash(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(
    user_data: dict,
    expires_delta: timedelta | None = None,
    refresh: bool = False,
) -> str:
    """Create a signed JWT access (or refresh) token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload = {
        "user": user_data,
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "refresh": refresh,
    }

    return jwt.encode(
        payload=payload,
        key=Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict | None:
    """Decode a JWT token. Returns None if invalid or expired."""
    try:
        return jwt.decode(
            jwt=token,
            key=Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM],
        )
    except jwt.PyJWTError as e:
        logging.exception(e)
        return None
'

  # ── app/core/dependencies.py ──────────────────────────────────────────────────
  mkf "app/core/dependencies.py" 'from typing import Annotated
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import decode_access_token
from app.db.main import get_session
from app.db.redis import is_token_in_blocklist, add_jti_to_blocklist


class TokenBearer(HTTPBearer):
    """Base class — validates token signature and blocklist."""

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(
        self,
        request: Request,
        session: AsyncSession = Depends(get_session),
    ) -> dict:
        creds: HTTPAuthorizationCredentials = await super().__call__(request)
        token = creds.credentials

        # 1. Decode and validate signature / expiry
        token_data = decode_access_token(token)
        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"},
            )

        # 2. Check Redis blocklist
        jti = token_data.get("jti")
        if jti and await is_token_in_blocklist(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "TOKEN_REVOKED", "message": "Token has been revoked"},
            )

        # 3. Delegate type-specific checks to subclasses
        self.verify_token_data(token_data)

        # Store on request state for easy access in route handlers
        request.state.token_data = token_data

        return token_data

    def verify_token_data(self, token_data: dict) -> None:
        raise NotImplementedError("Subclasses must implement verify_token_data()")


class AccessTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data.get("refresh") is True:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Use an access token, not a refresh token"},
            )


class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if not token_data.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_REFRESH_TOKEN", "message": "Use a refresh token"},
            )


# ── Fix 5: services injected via Depends — not instantiated manually ──────────

def get_session_dep(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    return session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ── get_current_user ──────────────────────────────────────────────────────────

async def get_current_user(
    token_data: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session),
):
    """Returns the full User object for the authenticated request."""
    from app.features.auth.services import AuthServices  # avoid circular import
    user_id = token_data["user"]["id"]
    user = await AuthServices().get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "User not found"},
        )
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]


# ── logout helper — dynamic TTL ───────────────────────────────────────────────

async def revoke_token(token_data: dict) -> None:
    """
    Add the token JTI to the Redis blocklist with dynamic TTL.
    Fix 7: TTL = remaining lifetime of the token, not a fixed value.
    """
    jti = token_data.get("jti")
    exp = token_data.get("exp")
    if jti and exp:
        ttl = exp - int(datetime.now(timezone.utc).timestamp())
        if ttl > 0:
            await add_jti_to_blocklist(jti, ttl=ttl)
'

  # ── app/core/exceptions.py ────────────────────────────────────────────────────
  mkf "app/core/exceptions.py" 'from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, status_code: int, detail: str | dict, code: str | None = None):
        self.status_code = status_code
        self.detail = detail
        self.code = code


class NotFoundException(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status.HTTP_404_NOT_FOUND,
            {"code": "NOT_FOUND", "message": f"{resource} not found."},
        )


class ForbiddenException(AppException):
    def __init__(self, message: str = "Access denied."):
        super().__init__(
            status.HTTP_403_FORBIDDEN,
            {"code": "FORBIDDEN", "message": message},
        )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."},
        )
'

  # ── .env ──────────────────────────────────────────────────────────────────────
  mkf ".env" 'DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/app_db

JWT_SECRET_KEY=change-me-use-openssl-rand-hex-32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

REDIS_HOST=localhost
REDIS_PORT=6379
'

  # ── .env.example ─────────────────────────────────────────────────────────────
  mkf ".env.example" 'DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DB_NAME

JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

REDIS_HOST=localhost
REDIS_PORT=6379
'

  # ── .gitignore ────────────────────────────────────────────────────────────────
  mkf ".gitignore" '__pycache__/
*.py[cod]
*.pyo
.env
.venv
venv/
.pytest_cache/
.ruff_cache/
*.egg-info/
dist/
build/
.coverage
htmlcov/
'

  # ── pyproject.toml ────────────────────────────────────────────────────────────
  mkf "pyproject.toml" '[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
'

  # ── Install packages + generate requirements.txt ──────────────────────────────
  log_section "Installing packages"

  local runtime=(
    "fastapi[standard]"
    "sqlmodel"
    "sqlalchemy[asyncio]"
    "asyncpg"
    "alembic"
    "redis"
    "celery[redis]"
    "pydantic-settings"
    "pwdlib[argon2]"
    "PyJWT"
    "httpx"
    "python-multipart"
    "uvicorn[standard]"
  )

  local dev_pkgs=(
    "pytest"
    "pytest-asyncio"
    "pytest-cov"
  )

  if ! command -v pip &>/dev/null; then
    log_warning "pip not found — activate your venv then run:"
    echo ""
    for pkg in "${runtime[@]}" "${dev_pkgs[@]}"; do
      echo "  pip install \"$pkg\""
    done
    echo "  pip freeze > requirements.txt"
    echo ""
    _print_init_success
    return
  fi

  log_info "Installing runtime packages (latest versions)..."
  for pkg in "${runtime[@]}"; do
    log_info "pip install \"$pkg\""
    pip install "$pkg" --quiet || {
      log_error "Failed to install: $pkg"
      exit 1
    }
  done
  log_success "Runtime packages installed."

  log_info "Installing dev/test packages..."
  for pkg in "${dev_pkgs[@]}"; do
    log_info "pip install \"$pkg\""
    pip install "$pkg" --quiet || {
      log_error "Failed to install: $pkg"
      exit 1
    }
  done
  log_success "Dev packages installed."

  log_info "Generating requirements.txt with pinned versions..."
  pip freeze > requirements.txt
  log_success "requirements.txt generated — $(wc -l < requirements.txt | tr -d ' ') packages pinned."

  _print_init_success
}

_print_init_success() {
  echo ""
  echo -e "${BOLD}${GREEN}  Scaffold ready.${RESET}"
  echo ""
  echo -e "${YELLOW}  Next steps:${RESET}"
  echo "    1. Fill in .env with your DB credentials"
  echo "    2. alembic init -t async migrations"
  echo "    3. Configure migrations/env.py"
  echo "    4. fapi feature auth"
  echo "    5. fapi feature <name>"
  echo "    6. fastapi dev app/main.py"
  echo ""
}

# ==============================================================================
#  COMMAND: feature
# ==============================================================================
cmd_feature() {
  local name="${1:-}"
  local no_router=false
  [[ "${2:-}" == "--no-router" ]] && no_router=true

  if [[ -z "$name" ]]; then
    log_error "Feature name is required."
    echo "  Usage: fapi feature <name> [--no-router]"
    exit 1
  fi

  if [[ ! "$name" =~ ^[a-z][a-z0-9_]*$ ]]; then
    log_error "Feature name must be snake_case (ex: auth, books, biens)."
    exit 1
  fi

  local pascal
  pascal=$(to_pascal "$name")
  local BASE="app/features/$name"

  if [[ -d "$BASE" ]]; then
    log_error "Feature '$name' already exists at $BASE"
    exit 1
  fi

  log_section "Feature: $name  ->  $pascal"

  mkd "$BASE"

  # ── __init__.py ───────────────────────────────────────────────────────────────
  mkf "$BASE/__init__.py" ""

  # ── models.py ─────────────────────────────────────────────────────────────────
  mkf "$BASE/models.py" "import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
import sqlalchemy.dialects.postgresql as pg


class ${pascal}(SQLModel, table=True):
    __tablename__ = '${name}s'

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    # TODO: add your columns
    # title: str = Field(sa_column=Column(pg.VARCHAR(255), nullable=False))

    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=datetime.now,
            nullable=False,
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=datetime.now,
            nullable=False,
        )
    )

    def __repr__(self) -> str:
        return f\"<${pascal}(id={self.id})>\"
"

  # ── schemas.py ────────────────────────────────────────────────────────────────
  mkf "$BASE/schemas.py" "import uuid
from datetime import datetime
from pydantic import BaseModel


class ${pascal}(BaseModel):
    \"\"\"Response schema.\"\"\"
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    # TODO: add response fields


class ${pascal}Create(BaseModel):
    \"\"\"Payload for creating a ${pascal}.\"\"\"
    # TODO: add create fields
    pass


class ${pascal}Update(BaseModel):
    \"\"\"Payload for updating a ${pascal} — all fields optional.\"\"\"
    # TODO: add update fields (all Optional)
    pass
"

  # ── services.py ───────────────────────────────────────────────────────────────
  mkf "$BASE/services.py" "import uuid
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession

from .models import ${pascal}
from .schemas import ${pascal}Create, ${pascal}Update


class ${pascal}Services:

    async def get_all(self, session: AsyncSession) -> list[${pascal}]:
        statement = select(${pascal}).order_by(desc(${pascal}.created_at))
        result = await session.exec(statement)
        return result.all()

    async def get_by_id(self, session: AsyncSession, item_id: uuid.UUID) -> ${pascal} | None:
        statement = select(${pascal}).where(${pascal}.id == item_id)
        result = await session.exec(statement)
        return result.first()

    async def create(self, session: AsyncSession, data: ${pascal}Create) -> ${pascal}:
        item = ${pascal}(**data.model_dump())
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item

    async def update(
        self,
        session: AsyncSession,
        item_id: uuid.UUID,
        data: ${pascal}Update,
    ) -> ${pascal} | None:
        item = await self.get_by_id(session, item_id)
        if item is None:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        await session.commit()
        await session.refresh(item)
        return item

    async def delete(self, session: AsyncSession, item_id: uuid.UUID) -> ${pascal} | None:
        item = await self.get_by_id(session, item_id)
        if item is None:
            return None
        await session.delete(item)
        await session.commit()
        return item
"

  # ── router.py (optional) ──────────────────────────────────────────────────────
  if [[ "$no_router" == false ]]; then
    mkf "$BASE/routes.py" "import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.main import get_session
from app.core.dependencies import AccessTokenBearer, SessionDep
from .schemas import ${pascal}, ${pascal}Create, ${pascal}Update
from .services import ${pascal}Services


${name}_router = APIRouter(prefix=\"/${name}s\", tags=[\"${pascal}\"])

# Fix 5: service injected via Depends — not instantiated at module level
def get_${name}_services() -> ${pascal}Services:
    return ${pascal}Services()

${pascal}ServicesDep = Annotated[${pascal}Services, Depends(get_${name}_services)]
access_token_bearer = AccessTokenBearer()


@${name}_router.get(\"/\", response_model=list[${pascal}], status_code=status.HTTP_200_OK)
async def get_all_${name}s(
    service: ${pascal}ServicesDep,
    session: SessionDep,
    current_user=Depends(access_token_bearer),
):
    return await service.get_all(session)


@${name}_router.post(\"/\", response_model=${pascal}, status_code=status.HTTP_201_CREATED)
async def create_${name}(
    data: ${pascal}Create,
    service: ${pascal}ServicesDep,
    session: SessionDep,
    current_user=Depends(access_token_bearer),
):
    return await service.create(session, data)


@${name}_router.get(\"/{item_id}\", response_model=${pascal}, status_code=status.HTTP_200_OK)
async def get_${name}_by_id(
    item_id: uuid.UUID,
    service: ${pascal}ServicesDep,
    session: SessionDep,
    current_user=Depends(access_token_bearer),
):
    item = await service.get_by_id(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=\"${pascal} not found\")
    return item


@${name}_router.put(\"/{item_id}\", response_model=${pascal}, status_code=status.HTTP_200_OK)
async def update_${name}(
    item_id: uuid.UUID,
    data: ${pascal}Update,
    service: ${pascal}ServicesDep,
    session: SessionDep,
    current_user=Depends(access_token_bearer),
):
    item = await service.update(session, item_id, data)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=\"${pascal} not found\")
    return item


@${name}_router.delete(\"/{item_id}\", response_model=${pascal}, status_code=status.HTTP_200_OK)
async def delete_${name}(
    item_id: uuid.UUID,
    service: ${pascal}ServicesDep,
    session: SessionDep,
    current_user=Depends(access_token_bearer),
):
    item = await service.delete(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=\"${pascal} not found\")
    return item
"
  fi

  # ── Post-generation checklist ─────────────────────────────────────────────────
  echo ""
  log_section "Checklist"

  echo ""
  echo -e "  ${YELLOW}1. app/main.py${RESET} — register the router:"
  if [[ "$no_router" == false ]]; then
    echo "     from app.features.${name}.routes import ${name}_router"
    echo "     app.include_router(${name}_router)"
  fi

  echo ""
  echo -e "  ${YELLOW}2. app/db/main.py${RESET} — import model in init_db():"
  echo "     from app.features.${name}.models import ${pascal}  # noqa: F401"

  echo ""
  echo -e "  ${YELLOW}3. Create & apply migration:${RESET}"
  echo "     alembic revision --autogenerate -m \"add_${name}s_table\""
  echo "     alembic upgrade head"

  echo ""
  echo -e "${BOLD}${GREEN}  Feature '${name}' ready.${RESET}"
  echo ""
}

# ==============================================================================
#  ENTRYPOINT
# ==============================================================================
usage() {
  echo ""
  echo -e "${BOLD}fapi${RESET} — FastAPI scaffold CLI"
  echo ""
  echo -e "  ${CYAN}fapi init${RESET}                        Init full project scaffold"
  echo -e "  ${CYAN}fapi feature <name>${RESET}              Add a feature module"
  echo -e "  ${CYAN}fapi feature <name> --no-router${RESET}  Add feature without HTTP router"
  echo ""
  echo "  Examples:"
  echo "    fapi init"
  echo "    fapi feature auth"
  echo "    fapi feature books"
  echo "    fapi feature biens"
  echo "    fapi feature notifications --no-router"
  echo ""
}

case "${1:-}" in
  init)    cmd_init ;;
  feature) shift; cmd_feature "${1:-}" "${2:-}" ;;
  -h|--help|"") usage ;;
  *) log_error "Unknown command: $1"; usage; exit 1 ;;
esac