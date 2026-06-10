import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.main import get_session
from app.core.dependencies import AccessTokenBearer, SessionDep
from .schemas import UserCreate
from .models import User
from .services import AuthServices


auth_router = APIRouter(prefix="/auths", tags=["Authentication"])

# Fix 5: service injected via Depends — not instantiated at module level
def get_auth_services() -> AuthServices:
    return AuthServices()

AuthServicesDep = Annotated[AuthServices, Depends(get_auth_services)]
# access_token_bearer = AccessTokenBearer() 




@auth_router.post("/signup", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user_account( 
    data: UserCreate,
    service: AuthServicesDep,
    session: SessionDep,
):
    
    email = data.email
    existing_user = await service.get_user_by_email(session, email)
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                'code': 'USER_ALREADY_EXIST',
                "message": "User with this email already exist"
            }
        )
    
    return await service.create_user(
        db=session,
        user_data=data
    )





@auth_router.delete("/{item_id}", response_model=User, status_code=status.HTTP_200_OK)
async def delete_auth(
    item_id: uuid.UUID,
    service: AuthServicesDep,
    session: SessionDep,
    # current_user=Depends(access_token_bearer),
):
    item = await service.delete(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth not found")
    return item
