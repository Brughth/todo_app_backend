import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.main import get_session
from app.core.dependencies import AccessTokenBearer, CurrentUser, SessionDep, RefreshTokenBearer, revoke_token
from .schemas import UserCreate, LoginResponse, UserLogin, TokenData
from .models import User
from .services import AuthServices
from app.core.security import verify_password, create_access_token
from datetime import timedelta
from fastapi.responses import JSONResponse


auth_router = APIRouter(prefix="/auths", tags=["Authentication"])

# Fix 5: service injected via Depends — not instantiated at module level
def get_auth_services() -> AuthServices:
    return AuthServices()

AuthServicesDep = Annotated[AuthServices, Depends(get_auth_services)]
access_token_bearer = AccessTokenBearer() 




@auth_router.post("/signup", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user_account( 
    data: UserCreate,
    service: AuthServicesDep,
    session: SessionDep,
):
    
    email = data.email
    phone = data.phone_number
    country_code = data.phone_country_code
    country_number = data.phone_country_number
    
    if phone:
        existing_user = await service.find_by_email_or_phone(
            db=session, 
            email=email, 
            phone=phone, 
            country_code=country_code, 
            country_number=country_number
        )
    else:
        existing_user = await service.get_user_by_email(
            db=session, 
            email=email
        )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                'code':  'USER_ALREADY_EXIST',
                "message": "User with this phone number already exist" if phone else "User with this email already exist"
            }
        )
    
    return await service.create_user(
        db=session,
        user_data=data
    )


@auth_router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    login_data: UserLogin,
    service: AuthServicesDep,
    session: SessionDep,
):
    invalid_credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"},
    )
    
    user = await service.get_user_by_email(
        db=session,
        email=login_data.email
    )
    
    if not user:
        raise invalid_credentials_exception
    
    is_valid_password = verify_password(password=login_data.password, hashed_password=user.password)
    
    if not is_valid_password:
        raise invalid_credentials_exception
    
    access_token = create_access_token(
        user_data={
            "id": str(user.id),
            "email": user.email
        },
        expires_delta=timedelta(minutes=30),
        refresh=False
    )
    
    refresh_token = create_access_token(
        user_data={
            "id": str(user.id),
            "email": user.email
        },
        expires_delta=timedelta(days=2),
        refresh=True
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user
    }
    

@auth_router.get("/me", response_model=User, status_code=status.HTTP_200_OK)
async def get_current_user(current_user: CurrentUser):
    return current_user

@auth_router.post("/refresh", response_model=TokenData, status_code=status.HTTP_200_OK)
async def refresh_token(token_data: dict = Depends(RefreshTokenBearer())):
    # Rotation : on révoque l'ancien refresh token (blocklist Redis)
    # puis on émet une nouvelle paire access + refresh.
    # L'expiry est déjà validée par RefreshTokenBearer → pas de check manuel ici.
    await revoke_token(token_data)

    new_access_token = create_access_token(
        user_data=token_data["user"],
        expires_delta=timedelta(minutes=30),
        refresh=False,
    )

    new_refresh_token = create_access_token(
        user_data=token_data["user"],
        expires_delta=timedelta(days=2),
        refresh=True,
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
    }

@auth_router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(token_data: dict = Depends(AccessTokenBearer())):
    # On révoque le token d'accès (blocklist Redis)
    await revoke_token(token_data)
    return JSONResponse(content={"message": "Successfully logged out"})


