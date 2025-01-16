from typing import List, Optional
import warnings

from fastapi.responses import JSONResponse

from middleware.auth_middleware import auth_middleware
from models.genre import Genre
from models.play_count_history import PlayCountHistory
from pydantic_schemas.user_create import UserCreate
from pydantic_schemas.user_login import UserLogin
warnings.filterwarnings("ignore", category=UserWarning, module="passlib")

from fastapi import APIRouter, Depends, HTTPException, File, Form, Request, UploadFile
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.artist import Artist
import jwt
from datetime import datetime, timedelta
import uuid
from pydantic import BaseModel
import re
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from models.follower import Follower
from models.song import Song
from models.song_artist import song_artists
from models.album import Album
from pydantic_schemas.album import AlbumResponse
import cloudinary
import cloudinary.uploader
import json
from sqlalchemy import func, insert
from sqlalchemy.orm import joinedload

router = APIRouter()

# Tạo pwd_context để mã hóa mật khẩu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Tạo OAuth2PasswordBearer để lấy token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Hàm để xác thực token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, "password_key", algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token đã hết hạn"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=401,
            detail="Token không hợp lệ"
        )

# Thêm hàm normalize_artist_name
def normalize_artist_name(name: str) -> str:
    """
    Chuẩn hóa tên nghệ sĩ:
    - Chuyển về chữ thường
    - Loại bỏ dấu câu và ký tự đặc biệt
    - Thay thế khoảng trắng bằng dấu gạch ngang
    """
    # Chuyển về chữ thường
    name = name.lower()
    # Loại bỏ dấu câu và ký tự đặc biệt
    name = re.sub(r'[^\w\s-]', '', name)
    # Thay thế khoảng trắng bằng dấu gạch ngang
    name = re.sub(r'[-\s]+', '-', name)
    return name.strip('-')

class SongResponse(BaseModel):
    id: str
    song_name: str
    song_url: str
    thumbnail_url: str
    hex_code: str
    album_id: Optional[str] = None
    artist_id: Optional[str] = None
    play_count: Optional[int] = None

    class Config:
        from_attributes = True

# Định nghĩa models cho request body
class ArtistRegister(BaseModel):
    email: str
    password: str 
    name: str

class ArtistLogin(BaseModel):
    email: str
    password: str

@router.post('/signup')
def signup_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        # Kiểm tra email đã tồn tại
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(400, 'Email đã được sử dụng!')

        if not user.name:
            raise HTTPException(400, 'Tên không được để trống!')

        # Tạo user_id trước
        user_id = str(uuid.uuid4())
        
        # Mã hóa mật khẩu
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
        
        # Tạo user mới
        new_user = User(
            id=user_id,
            email=user.email,
            password=hashed_password,
            name=user.name,
            role='artist'
        )
        
        db.add(new_user)
        db.commit()
        
        # Tạo artist profile
        artist_id = str(uuid.uuid4())
        new_artist = Artist(
            id=artist_id,
            user_id=user_id,
            normalized_name=user.name
        )
        
        db.add(new_artist)
        db.commit()

        # Tạo token với user_id thay vì artist_id
        token = jwt.encode({'id': user_id}, 'password_key')

        return {
            'token': token,
            'user': {
                'id': user_id,
                'email': user.email,
                'name': user.name,
                'role': 'artist',
                'artist_id': artist_id
            }
        }
        
    except Exception as e:
        db.rollback()
        print(f"Signup error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/login')
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    # check if a user with same email already exist
    user_db = db.query(User).filter(User.email == user.email).first()

    if not user_db:
        raise HTTPException(400, 'User with this email does not exist!')
    
    # password matching or not
    is_match = bcrypt.checkpw(user.password.encode(), user_db.password)
    
    if not is_match:
        raise HTTPException(400, 'Incorrect password!')
    
    # Lấy thông tin artist_id từ bảng Artist
    artist = db.query(Artist).filter(Artist.user_id == user_db.id).first()
    if not artist:
        raise HTTPException(400, 'Không tìm thấy thông tin nghệ sĩ')
    
    # artist1 = db.query(Artist).filter(Artist.is_approved == False).first()
    # if  artist1:
    #     raise HTTPException(400, 'Chưa duyệt')

    token = jwt.encode({'id': user_db.id}, 'password_key')
    
    # Tạo dict chứa thông tin user để trả về
    user_data = {
        'id': user_db.id,
        'email': user_db.email,
        'name': user_db.name,
        'role': user_db.role,
        'artist_id': artist.id  # Thêm artist_id vào response
    }
    
    return {'token': token, 'user': user_data}

@router.get("/profile")
async def get_artist_profile(payload = Depends(auth_middleware), db: Session = Depends(get_db)):
    artist = db.query(Artist).filter(Artist.user_id == payload["uid"]).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    
    user = db.query(User).filter(User.id == payload["uid"]).first()
    
    # Đếm số lượng follower
    follower_count = db.query(Follower).filter(Follower.artist_id == artist.id).count()
    
    response_data = {
        "id": artist.id,
        "user_id": artist.user_id,
        "normalized_name": artist.normalized_name,
        "bio": artist.bio,
        "image_url": artist.image_url,
        "is_approved": artist.is_approved,
        "created_at": artist.created_at,
        "updated_at": artist.updated_at,
        "name": user.name,
        "email": user.email,
        "follower_count": follower_count  # Thêm số lượng follower vào response
    }
    
    return response_data

class ArtistUpdateRequest(BaseModel):
    normalized_name: str | None = None
    bio: str | None = None
    image_url: str | None = None

@router.post("/profile/update")
async def update_artist_profile(
    request: ArtistUpdateRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(auth_middleware)
):
    try:
        # Lấy artist_id từ user_id
        artist = db.query(Artist).filter(Artist.user_id == user_data["uid"]).first()
        if not artist:
            raise HTTPException(status_code=404, detail="Không tìm thấy thông tin nghệ sĩ")

        # Cập nhật thông tin
        if request.normalized_name is not None:
            artist.normalized_name = request.normalized_name
        if request.bio is not None:
            artist.bio = request.bio
        if request.image_url is not None:
            artist.image_url = request.image_url

        db.commit()
        return {"message": "Cập nhật thông tin thành công"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-songs")
async def get_my_songs(payload: dict = Depends(auth_middleware), db: Session = Depends(get_db)):
    try:
        user_id = payload.get("uid")
        print(f"Getting songs for user_id: {user_id}")
        
        # Lấy thông tin artist từ user_id
        artist = db.query(Artist).filter(Artist.user_id == user_id).first()
        
        if not artist:
            print(f"No artist found for user_id: {user_id}")
            raise HTTPException(status_code=404, detail="Bạn chưa được đăng ký là nghệ sĩ")
        
        print(f"Found artist: {artist.id}")
        
        # Lấy danh sách bài hát của artist và user
        songs = (
            db.query(Song)
            .outerjoin(song_artists)
            .filter(
                (song_artists.c.artist_id == artist.id) |
                (Song.user_id == user_id)
            )
            .all()
        )
        
        print(f"Found {len(songs)} songs")
        
        # Chuyển đổi kết quả thành JSON và tính tổng play_count
        songs_data = []
        for song in songs:
            total_play_count = (
                db.query(func.sum(PlayCountHistory.play_count))
                .filter(PlayCountHistory.song_id == song.id)
                .scalar() or 0
            )
            
            songs_data.append({
                "id": song.id,
                "song_name": song.song_name,
                "song_url": song.song_url,
                "thumbnail_url": song.thumbnail_url,
                "hex_code": song.hex_code,
                "play_count": total_play_count,  # Tổng số lượt nghe
                "created_at": song.created_at,
                "status": song.status,
            })
        
        return songs_data

    except HTTPException as he:
        raise he
    except Exception as e:
        print("Error getting my songs:", str(e))
        raise HTTPException(status_code=500, detail="Lỗi khi lấy danh sách bài hát")






@router.get("/albums", response_model=List[AlbumResponse])
async def get_my_albums(
    db: Session = Depends(get_db),
    auth_dict = Depends(auth_middleware)
):
    try:
        # Lấy user_id từ token xác thực
        user_id = auth_dict["uid"]
        
        # Tìm artist dựa trên user_id
        artist = db.query(Artist).filter(Artist.user_id == user_id).first()
        if not artist:
            raise HTTPException(status_code=404, detail="Không tìm thấy thông tin nghệ sĩ")
            
        # Lấy danh sách album của nghệ sĩ
        albums = db.query(Album).filter(
            Album.user_id == user_id
        ).order_by(Album.created_at.desc()).all()
        
        return albums
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print("Error getting albums:", str(e))
        raise HTTPException(status_code=500, detail="Lỗi khi lấy danh sách album")
    

# @router.get("/albums")
# async def get_my_albums(
#     db: Session = Depends(get_db),
#     auth_dict = Depends(auth_middleware)
# ):
#     try:
#         # Lấy user_id từ token xác thực
#         user_id = auth_dict["uid"]
        
#         # Tìm artist dựa trên user_id
#         artist = db.query(Artist).filter(Artist.user_id == user_id).first()
#         if not artist:
#             raise HTTPException(status_code=404, detail="Không tìm thấy thông tin nghệ sĩ")
            
#         # Lấy danh sách album của nghệ sĩ
#         albums = db.query(Song).filter(
#             Song.user_id == user_id
#         ).order_by(Song.created_at.desc()).all()
        
#         return albums
        
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         print("Error getting albums:", str(e))
#         raise HTTPException(status_code=500, detail="Lỗi khi lấy danh sách album")




@router.get("/albums/{album_id}/songs", response_model=List[SongResponse])
async def get_album_songs(
    album_id: str,
    db: Session = Depends(get_db),
    auth_dict = Depends(auth_middleware)
):
    try:
        user_id = auth_dict["uid"]
        
        # Kiểm tra album tồn tại và thuộc về user
        album = db.query(Album).filter(
            Album.id == album_id,
            Album.user_id == user_id
        ).first()
        
        if not album:
            raise HTTPException(status_code=404, detail="Không tìm thấy album")

        # Lấy danh sách bài hát của album và join với bảng artists
        songs = db.query(Song).filter(
            Song.album_id == album_id
        ).all()
        
        # In ra để debug
        print("Songs found:", len(songs))
        for song in songs:
            print(f"Song ID: {song.id}, Name: {song.song_name}, Artist ID: {song.artist_id}")
        
        return songs
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print("Error getting album songs:", str(e))
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách bài hát: {str(e)}")

async def upload_file_to_album(file: UploadFile, album_id: str, file_type: str) -> str:
    try:
        # Tạo đường dẫn folder trên Cloudinary: albums/{album_id}/{file_type}
        folder_path = f"albums/{album_id}/{file_type}"
        
        # Upload file lên Cloudinary với folder path đã chỉ định
        result = cloudinary.uploader.upload(
            file.file,
            folder=folder_path,
            resource_type="auto"
        )
        return result['secure_url']
    except Exception as e:
        print(f"Error uploading file to Cloudinary: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi tải file lên cloud storage")

@router.post("/albums/{album_id}/songs", response_model=SongResponse)
async def create_song_in_album(
    album_id: str,
    song: UploadFile = File(...),
    thumbnail: UploadFile = File(...),
    song_name: str = Form(...),
    hex_code: str = Form(...),
    genreIds: str = Form(...),  # Thêm trường genreIds
    featuringArtistIds: str = Form(default="[]"),  # Thêm trường featuringArtistIds
    db: Session = Depends(get_db),
    auth_dict = Depends(auth_middleware)
):
    try:
        user_id = auth_dict["uid"]
        genre_ids = json.loads(genreIds)
        featuring_artist_ids = json.loads(featuringArtistIds)
        
        # Kiểm tra album và lấy artist_id
        artist = db.query(Artist).filter(Artist.user_id == user_id).first()
        if not artist:
            raise HTTPException(status_code=404, detail="Không tìm thấy thông tin nghệ sĩ")
            
        album = db.query(Album).filter(
            Album.id == album_id,
            Album.user_id == user_id
        ).first()
        
        if not album:
            raise HTTPException(status_code=404, detail="Không tìm thấy album")

        # Upload files vào thư mục của album
        song_url = await upload_file_to_album(song, album_id, "songs")
        thumbnail_url = await upload_file_to_album(thumbnail, album_id, "thumbnails")
        
        # Tạo bài hát mới với artist_id
        song_id = str(uuid.uuid4())
        new_song = Song(
            id=song_id,
            song_name=song_name,
            song_url=song_url,
            thumbnail_url=thumbnail_url,
            hex_code=hex_code,
            user_id=user_id,
            album_id=album_id,
            artist_id=artist.id,  # Thêm artist_id
            genre_id=genre_ids[0] if genre_ids else None,  # Lấy genre đầu tiên
            status='pending'
        )
        
        try:
            # Lưu bài hát mới vào database
            db.add(new_song)
            db.commit()

            # Thêm thể loại cho bài hát
            # for genre_id in genre_ids:
            #     db.execute(
            #         song_genres.insert().values(
            #             song_id=song_id,
            #             genre_id=genre_id
            #         )
            #     )
            
            # Thêm nghệ sĩ hát cùng (không bao gồm nghệ sĩ chính)
            if featuring_artist_ids:
                for featuring_id in featuring_artist_ids:
                    db.execute(
                        song_artists.insert().values(
                            song_id=song_id,
                            artist_id=featuring_id
                        )
                    )

            db.commit()
            db.refresh(new_song)
            
            return new_song

        except Exception as e:
            db.rollback()
            print(f"Database error: {str(e)}")
            raise HTTPException(status_code=500, detail="Lỗi khi lưu vào database")

    except HTTPException as he:
        raise he
    except Exception as e:
        print("Error creating song:", str(e))
        raise HTTPException(status_code=500, detail="Lỗi khi tạo bài hát")
        
# @router.get("/listartists") 
# async def list_artists(db: Session = Depends(get_db)):
#     try:
#         # Join bảng User và Artist để lấy thông tin đầy đủ
#         artists = db.query(User, Artist)\
#             .join(Artist, User.id == Artist.user_id)\
#             .filter(User.role == 'artist')\
#             .all()
        
#         return [{
#             "id": artist.Artist.id,
#             "user_id": artist.User.id,
#             "normalized_name": artist.Artist.normalized_name, # Giữ lại normalized_name
#             "name": artist.User.name, # Thêm name từ User
#             "email": artist.User.email,
#             "image_url": artist.Artist.image_url if artist.Artist.image_url else None
#         } for artist in artists]
#     except Exception as e:
#         print(f"Error listing artists: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Lỗi khi lấy danh sách nghệ sĩ: {str(e)}"
#         )


@router.get("/listartists")
async def list_artists(query: str = "", db: Session = Depends(get_db)):
    try:
        # Join bảng User và Artist để lấy thông tin đầy đủ, lọc theo query
        artists = db.query(User, Artist)\
            .join(Artist, User.id == Artist.user_id)\
            .filter(User.role == 'artist')

        # Nếu có query, lọc thêm theo tên nghệ sĩ hoặc tên người dùng
        if query:
            artists = artists.filter(
                Artist.normalized_name.ilike(f"%{query}%") |  # Tìm theo tên nghệ sĩ
                User.name.ilike(f"%{query}%")                 # Tìm theo tên người dùng
            )

        # Thực hiện truy vấn và trả về kết quả
        artists = artists.all()
        
        return [{
            "id": artist.Artist.id,
            "user_id": artist.User.id,
            "normalized_name": artist.Artist.normalized_name,  # Giữ lại normalized_name
            "name": artist.User.name,                           # Thêm name từ User
            "email": artist.User.email,
            "image_url": artist.Artist.image_url if artist.Artist.image_url else None
        } for artist in artists]

    except Exception as e:
        print(f"Error listing artists: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy danh sách nghệ sĩ: {str(e)}"
        )

async def upload_file_to_cloudinary(file, folder):
    try:
        # Đọc nội dung file
        contents = await file.read()
        
        # Upload lên Cloudinary
        result = cloudinary.uploader.upload(
            contents,
            folder=folder,
            resource_type="auto"
        )
        
        return result['secure_url']
    except Exception as e:
        print(f"Cloudinary upload error: {str(e)}")
        raise Exception(f"Lỗi khi upload file lên Cloudinary: {str(e)}")

@router.post("/upload")
async def upload_song(
    song: UploadFile,
    thumbnail: UploadFile,
    songName: str = Form(...),
    hexCode: str = Form(...),
    genreIds: str = Form(...),
    featuringArtistIds: str = Form(default="[]"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
):
    try:
        # Parse IDs
        genre_ids = json.loads(genreIds)
        featuring_artist_ids = json.loads(featuringArtistIds)
        
        print(f"Received featuring artists: {featuring_artist_ids}")
        
        # Upload files to Cloudinary
        song_url = await upload_file_to_cloudinary(song, "songs")
        thumbnail_url = await upload_file_to_cloudinary(thumbnail, "thumbnails")
        
        # Get artist ID for current user
        main_artist = db.query(Artist).filter(Artist.user_id == current_user["uid"]).first()
        if not main_artist:
            raise HTTPException(status_code=404, detail="Không tìm thấy thông tin nghệ sĩ")
            
        # Create new song
        song_id = str(uuid.uuid4())
        new_song = Song(
            id=song_id,
            song_name=songName,
            thumbnail_url=thumbnail_url,
            song_url=song_url,
            hex_code=hexCode,
            user_id=current_user["uid"],
            artist_id=main_artist.id,  # Lưu artist_id của nghệ sĩ chính vào bảng songs
            genre_id=genre_ids[0] if genre_ids else None,  # Lấy genre đầu tiên
            status='approved'
        )
        
        try:
            # Add and commit song first
            db.add(new_song)
            db.commit()
            
            # Add genre relationships
            # for genre_id in genre_ids:
            #     db.execute(
            #         song_genres.insert().values(
            #             song_id=song_id,
            #             genre_id=genre_id
            #         )
            #     )
            
            # Chỉ thêm featuring artists vào song_artists (không thêm nghệ sĩ chính)
            if featuring_artist_ids:
                for featuring_id in featuring_artist_ids:
                    print(f"Adding featuring artist ID to song_artists: {featuring_id}")
                    db.execute(
                        song_artists.insert().values(
                            song_id=song_id,
                            artist_id=featuring_id  # Đây là Artist.id của nghệ sĩ hát cùng
                        )
                    )
            
            # Commit all relationships
            db.commit()
            
            return {
                "message": "Tải lên bài hát thành công", 
                "song_id": song_id,
                "featuring_artists": featuring_artist_ids
            }
            
        except Exception as e:
            db.rollback()
            print(f"Database error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Lỗi khi lưu vào database: {str(e)}")
            
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi tải lên: {str(e)}")

# @router.get("/{artist_id}/songs")
# async def get_artist_songs(artist_id: str, db: Session = Depends(get_db)):
#     artist = db.query(Artist).filter(Artist.id == artist_id).first()
#     if not artist:
#         raise HTTPException(status_code=404, detail="Nghệ sĩ không tồn tại")
        
#     songs = db.query(Song).join(Song.artists).filter(Artist.id == artist_id).all()
#     return songs

@router.get("/{artist_id}/songs")
async def get_artist_songs(artist_id: str, db: Session = Depends(get_db)):
    # Lấy thông tin của nghệ sĩ theo artist_id
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Nghệ sĩ không tồn tại")
    
    # Truy vấn bài hát mà nghệ sĩ này có mặt từ bảng song_artists (nối giữa Song và Artist)
    songs_from_artists = db.query(Song).join(song_artists).filter(song_artists.c.artist_id == artist_id).all()

    # Truy vấn những bài hát trong bảng Song mà artist_id là một phần trong bài hát đó
    songs_in_song = db.query(Song).filter(Song.artist_id == artist_id).all()
    
    # Kết hợp hai danh sách bài hát
    all_songs = set(songs_from_artists + songs_in_song)

    return all_songs





@router.get("/{artist_id}/albums") 
async def get_artist_albums(artist_id: str, db: Session = Depends(get_db)):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Nghệ sĩ không tồn tại")
        
    albums = db.query(Album).filter(Album.user_id == artist.user_id).all()
    return albums

@router.post("/{artist_id}/follow")
async def follow_artist(
    artist_id: str,
    user_data: dict = Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    user_id = user_data["uid"]
    
    # Kiểm tra xem đã follow chưa
    existing_follow = db.query(Follower).filter(
        Follower.user_id == user_id,
        Follower.artist_id == artist_id
    ).first()
    
    if existing_follow:
        # Nếu đã follow thì unfollow
        db.delete(existing_follow)
        db.commit()
        return {"message": "Unfollowed successfully"}
    
    # Nếu chưa follow thì tạo mới
    new_follow = Follower(
        id=str(uuid.uuid4()),
        user_id=user_id,
        artist_id=artist_id
    )
    db.add(new_follow)
    db.commit()
    
    return {"message": "Followed successfully"}

@router.get("/{artist_id}/is_following")
async def check_following(
    artist_id: str,
    user_data: dict = Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    user_id = user_data["uid"]
    
    is_following = db.query(Follower).filter(
        Follower.user_id == user_id,
        Follower.artist_id == artist_id
    ).first() is not None
    
    return {"is_following": is_following}

@router.get("/followed")
async def get_followed_artists(
    user_data: dict = Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    try:
        user_id = user_data["uid"]
        
        followed_artists = db.query(Artist).join(
            Follower, 
            Follower.artist_id == Artist.id
        ).filter(
            Follower.user_id == user_id
        ).options(
            joinedload(Artist.user)
        ).all()
        
        result = []
        for artist in followed_artists:
            result.append({
                "id": artist.id,
                "normalizedName": artist.normalized_name,
                "bio": artist.bio,
                "imageUrl": artist.image_url,
                "isApproved": artist.is_approved,
                "createdAt": artist.created_at.isoformat() if artist.created_at else None,
                "updatedAt": artist.updated_at.isoformat() if artist.updated_at else None,
                "user": {
                    "id": artist.user.id,
                    "name": artist.user.name,
                    "email": artist.user.email,
                } if artist.user else None
            })
            
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting followed artists: {str(e)}"
        )
















class SongRequest(BaseModel):
    song_ids: list[str]

# @router.post("/songs/artist/{artist_id}")
# def get_songs_by_artist(artist_id: str, db: Session = Depends(get_db)):
#     # Lấy các song_id từ bảng song_artists có liên kết với artist_id
#     song_ids = db.query(song_artists.c.song_id).filter(song_artists.c.artist_id == artist_id).all()

#     if not song_ids:
#         raise HTTPException(status_code=404, detail="No songs found for this artist")

#     # Chuyển đổi kết quả từ tuple thành list đơn giản
#     song_ids = [song_id[0] for song_id in song_ids]
    
#     return {"song_ids": song_ids}



# @router.post("/songs/user/{user_id}")
# def get_songs_by_user(user_id: str, db: Session = Depends(get_db)):
#     # Bước 1: Tìm artist_id liên kết với user_id trong bảng artist
#     artist = db.query(Artist).filter(Artist.user_id == user_id).first()
    
#     if not artist:
#         raise HTTPException(status_code=404, detail="Artist not found for this user")

#     # Lấy artist_id
#     artist_id = artist.id

#     # Bước 2: Tìm danh sách song_id từ bảng song_artists liên kết với artist_id
#     song_ids = db.query(song_artists.c.song_id).filter(song_artists.c.artist_id == artist_id).all()

#     if not song_ids:
#         raise HTTPException(status_code=404, detail="No songs found for this artist")

#     # Chuyển đổi kết quả từ tuple thành danh sách đơn giản
#     song_ids = [song_id[0] for song_id in song_ids]

#     return {"artist_id": artist_id, "song_ids": song_ids}


# @router.post("/songs/details")
# def get_songs_details(request: SongRequest, db: Session = Depends(get_db)):
#     # Fetch songs matching the provided song_ids
#     songs = db.query(Song).filter(Song.id.in_(request.song_ids)).all()

#     if not songs:
#         raise HTTPException(status_code=404, detail="No songs found with the provided song_ids")

#     # Lấy danh sách các ID người dùng bị ẩn bài hát và xác định xem họ có phải là moderator không
#     user_ids = [song.hidden_by for song in songs if song.hidden_by is not None]
#     users = db.query(User).filter(User.id.in_(user_ids)).all()

#     # Chuyển đổi người dùng thành dictionary với ID và role
#     user_roles = {user.id: user.role for user in users}

#     # Kiểm tra nếu người ẩn bài hát là moderator
#     for song in songs:
#         if song.hidden_by:
#             hidden_by_user_role = user_roles.get(song.hidden_by)
#             if hidden_by_user_role == "moderator":
#                 song.hidden_by_user_role = "Hidden by Moderator"
#             else:
#                 song.hidden_by_user_role = "Hidden by User"

#     # Return detailed information for the songs
#     return {"songs": [song.as_dict() for song in songs]}














class SongRequest(BaseModel):
    song_ids: list[str]

# @router.post("/songs/artist/{artist_id}")
# def get_songs_by_artist(artist_id: str, db: Session = Depends(get_db)):
#     # Lấy các song_id từ bảng song_artists có liên kết với artist_id
#     song_ids = db.query(song_artists.c.song_id).filter(song_artists.c.artist_id == artist_id).all()

#     if not song_ids:
#         raise HTTPException(status_code=404, detail="No songs found for this artist")

#     # Chuyển đổi kết quả từ tuple thành list đơn giản
#     song_ids = [song_id[0] for song_id in song_ids]
    
#     return {"song_ids": song_ids}



@router.post("/songs/user/{user_id}")
def get_songs_by_user(user_id: str, db: Session = Depends(get_db)):
    # Bước 1: Tìm artist_id liên kết với user_id trong bảng artist
    artist = db.query(Artist).filter(Artist.user_id == user_id).first()
    
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found for this user")

    # Lấy artist_id
    artist_id = artist.id

    # Bước 2: Tìm danh sách song_id từ bảng song_artists liên kết với artist_id
    # song_ids = db.query(song_artists.c.song_id).filter(song_artists.c.artist_id == artist_id).all()
    song_ids = db.query(song_artists.c.song_id).filter(Song.artist_id == artist_id).all()
    if not song_ids:
        raise HTTPException(status_code=404, detail="No songs found for this artist")

    # Chuyển đổi kết quả từ tuple thành danh sách đơn giản
    song_ids = [song_id[0] for song_id in song_ids]

    return {"artist_id": artist_id, "song_ids": song_ids}



@router.post("/songs/details")
def get_songs_details(request: SongRequest, db: Session = Depends(get_db)):
    # Fetch songs matching the provided song_ids
    songs = db.query(Song).filter(Song.id.in_(request.song_ids)).all()

    if not songs:
        raise HTTPException(status_code=404, detail="No songs found with the provided song_ids")

    # Lấy danh sách các ID người dùng bị ẩn bài hát và xác định xem họ có phải là moderator không
    user_ids = [song.hidden_by for song in songs if song.hidden_by is not None]
    users = db.query(User).filter(User.id.in_(user_ids)).all()

    # Chuyển đổi người dùng thành dictionary với ID và role
    user_roles = {user.id: user.role for user in users}

    # Kiểm tra nếu người ẩn bài hát là moderator
    for song in songs:
        if song.hidden_by:
            hidden_by_user_role = user_roles.get(song.hidden_by)
            if hidden_by_user_role == "moderator":
                song.hidden_by_user_role = "Hidden by Moderator"
            else:
                song.hidden_by_user_role = "Hidden by User"

    # Return detailed information for the songs
    return {"songs": [song.as_dict() for song in songs]}
