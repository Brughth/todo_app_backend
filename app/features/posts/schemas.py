from pydantic import BaseModel, model_validator, ValidationError
from typing import Self

class PostCreate(BaseModel):
    title: str
    description: str
    create_by: str | None = None
    

class PostUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    create_by: str | None = None
    
    @model_validator(mode='after')
    def validate_field(self)->Self:
        
        fields = [self.title, self.description, self.create_by]
        
        if not any(fields):
            raise ValidationError(
                "At least one field must be provided for the update."
            )
        
        return self