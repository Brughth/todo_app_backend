from typing import Self
from datetime import datetime
from pydantic import BaseModel, Field, model_validator, EmailStr
from app.core.utils import validate_phone_fields
from .models import User



class UserCreate(BaseModel):
    first_name: str
    last_name: str 
    email: EmailStr 
    phone_country_code: str | None = None
    phone_country_number: str | None = None
    phone_number: str | None = None
    password: str = Field(...,min_length=8)
    
    @model_validator(mode='after')
    def validate_phone_number(self) -> Self:
        validate_phone_fields(
            self.phone_country_code,
            self.phone_country_number,
            self.phone_number
        )
        return self
    

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: User

class TokenData(BaseModel):
    access_token: str
    refresh_token: str
    
class UserLogin(BaseModel):
    email: str
    password: str

        
