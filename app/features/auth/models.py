import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, UniqueConstraint
import sqlalchemy.dialects.postgresql as pg


class User(SQLModel, table=True):
    __tablename__ = 'users'
    
    __table_args__ = (
        UniqueConstraint(
            'phone_country_code',
            'phone_country_number', 
            'phone_number',
            name='uq_users_full_phone_number'
        ),
    )


    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    first_name: str = Field(
        sa_column=Column(
              pg.VARCHAR(255), 
              nullable=False
            )
    )
    
    last_name: str = Field(
        sa_column=Column(
              pg.VARCHAR(255), 
              nullable=False
            )
    )
    
    email: str = Field(
        sa_column=Column(
              pg.VARCHAR(255), 
              nullable=False, 
              unique=True
            )
    )
    
    phone_country_code: str = Field(
        sa_column=Column(
              pg.VARCHAR(10), 
              nullable=True
            )
    )
    
    phone_country_number: str = Field(
        sa_column=Column(
              pg.VARCHAR(20), 
              nullable=True
            )
    )
    
    phone_number: str = Field(
        sa_column=Column(
              pg.VARCHAR(20), 
              nullable=True
            )
    )
    
    password: str = Field(
        sa_column=Column(
              pg.VARCHAR(255),
              nullable=False
            ),
        exclude=True
    )
    
    email_verified: bool = Field(
        sa_column=Column(
              pg.BOOLEAN, 
              nullable=False, 
              default=False
            )
    )
    
    email_verifiled_at: datetime = Field(
        sa_column=Column(
              pg.TIMESTAMP(timezone=True),
              nullable=True
            )
    )
    

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
        return f"<Auth(id={self.id})>"
