from pydantic import BaseModel
from typing import List, Optional
from fastapi import UploadFile

class AlbumCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = True

class AlbumResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    thumbnail_url: str
    is_public: bool
    user_id: str
    
    class Config:
        from_attributes = True

class AddSongToAlbum(BaseModel):
    song_id: str