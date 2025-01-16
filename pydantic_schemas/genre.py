from pydantic import BaseModel

class GenreCreate(BaseModel):
    name: str
    description: str
