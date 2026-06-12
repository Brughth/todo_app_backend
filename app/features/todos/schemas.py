
from pydantic import BaseModel




class TodosCreate(BaseModel):
    title: str
    is_completed: bool = False


class TodosUpdate(BaseModel):
    title: str
    is_completed: bool = False
