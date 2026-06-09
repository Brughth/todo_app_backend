import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
import sqlalchemy.dialects.postgresql as pg


class Auth(SQLModel, table=True):
    __tablename__ = 'auths'

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
        return f"<Auth(id={self.id})>"
