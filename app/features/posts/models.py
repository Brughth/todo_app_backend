from sqlmodel import SQLModel, Field, Column
import uuid
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime


class Post(SQLModel, table=True):
    
    __tablename__ = "posts"
    
    id: uuid.UUID  = Field(
        sa_column=Column(
            pg.UUID,
            primary_key=True,
            nullable=False,
            default=uuid.uuid4,
        )
    )
    
    title: str = Field(
        sa_column=Column(
            pg.VARCHAR(400),
            nullable=False,
        )
    )
    
    description: str = Field(
        sa_column=Column(
            pg.VARCHAR(),
            nullable=False
        )
    )
    
    
    create_by: str = Field(
        sa_column=Column(
            pg.VARCHAR(256),
            nullable=True
        )
    )
    
    
    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            default=datetime.now
        )
    )
    
    updated_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            default=datetime.now
        )
    )
    
    