import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models.genre import Genre
from models.user import User
from utils import get_current_user
from pydantic_schemas.genre import GenreCreate
from models.song import Song

router = APIRouter()

@router.post("/create_genre/")
def create_genre(genre: GenreCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ['admin', 'moderator']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    new_genre = Genre(name=genre.name, description=genre.description)
    db.add(new_genre)
    db.commit()
    db.refresh(new_genre)
    return new_genre

@router.get("/list")
async def get_genres(db: Session = Depends(get_db)):
    try:
        genres = db.query(Genre).all()
        return [{
            "id": genre.id,
            "name": genre.name,
            "description": genre.description
        } for genre in genres]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


class CreateGenre(BaseModel):
    description: str = None
    image_url: str
    name: str


@router.post("/create")
async def create_genre(request: CreateGenre, db: Session = Depends(get_db)):
    new_genre = Genre(
        id=str(uuid.uuid4()),
        name=request.name,
        description=request.description,
        image_url=request.image_url
    )
    db.add(new_genre)
    db.commit()
    db.refresh(new_genre)
    return new_genre


@router.get("/{genre_id}")
async def get_genre(genre_id: str, db: Session = Depends(get_db)):
    genre = db.query(Genre).filter(Genre.id == genre_id).first()
    if not genre:
        raise HTTPException(status_code=404, detail="Thể loại không tồn tại")
    return genre 

# @router.get("/{genre_id}/songs")
# async def get_genre_songs(genre_id: str, db: Session = Depends(get_db)):
#     # Lấy danh sách bài hát theo thể loại
#     songs = db.query(Song).filter(Song.genre_id == genre_id).all()

#     # Chuyển đổi danh sách bài hát sang định dạng JSON
#     return [
#         {
#             "id": song.id,
#             "song_name": song.song_name,
#             "thumbnail_url": song.thumbnail_url,
#             "song_url": song.song_url,
#             "hex_code": song.hex_code,
#             "album_id": song.album.name if song.album else None,
#             "genre_id": song.genre_id,
#             "status": song.status,
#             "created_at": song.created_at,
#             "updated_at": song.updated_at,
#             "userName": db.query(User).filter(User.id == song.user_id).first().name if song.user_id else None,
#             "artists": [
#                 {
#                     "id": artist.id,
#                     "name": artist.name,
#                     "normalizedName": db.query(User).filter(User.id == song.user_id).first().name if song.user_id else None,
#                     "imageUrl": artist.image_url
#                 }
#                 for artist in song.artists
#             ]
#         }
#         for song in songs
#     ]

@router.get("/{genre_id}/songs")
async def get_genre_songs(genre_id: str, db: Session = Depends(get_db)):
    # Kiểm tra xem thể loại có tồn tại không
    genre = db.query(Genre).filter(Genre.id == genre_id).first()
    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thể loại này"
        )

    # Lấy danh sách bài hát theo thể loại
    songs = db.query(Song).filter(Song.genre_id == genre_id).all()

    # Nếu không có bài hát nào, trả về mảng rỗng
    if not songs:
        return []

    # Chuyển đổi danh sách bài hát sang định dạng JSON
    return [
        {
            "id": song.id,
            "song_name": song.song_name,
            "thumbnail_url": song.thumbnail_url,
            "song_url": song.song_url,
            "hex_code": song.hex_code,
            "album_id": song.album.name if song.album else None,
            "genre_id": song.genre_id,
            "status": song.status,
            "created_at": song.created_at,
            "updated_at": song.updated_at,
            "userName": db.query(User).filter(User.id == song.user_id).first().name if song.user_id else None,
            "artists": [
                {
                    "id": artist.id,
                    "name": artist.name,
                    "normalizedName": db.query(User).filter(User.id == song.user_id).first().name if song.user_id else None,
                    "imageUrl": artist.image_url
                }
                for artist in song.artists
            ]
        }
        for song in songs
    ]









@router.post("/create")
async def create_genre(name: str, description: str = None, db: Session = Depends(get_db)):
    new_genre = Genre(
        id=str(uuid.uuid4()),
        name=name,
        description=description
    )
    db.add(new_genre)
    db.commit()
    db.refresh(new_genre)
    return new_genre