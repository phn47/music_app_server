from typing import List
import cloudinary
import cloudinary.api
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from database import get_db
from middleware.auth_middleware import auth_middleware
from models.album import Album
from models.favorite import Favorite
from models.genre import Genre
from models.play_count_history import PlayCountHistory
from models.song import Song
from models.artist import Artist
from pydantic_schemas.album import AlbumCreate, AlbumResponse
import uuid
from routes.artist import normalize_artist_name
from datetime import datetime, timedelta
from typing import Optional
import os
from models.user import User

router = APIRouter()

@router.get("/")
async def get_albums(
    x_auth_token: Optional[str] = Header(None),
    auth_dict: dict = Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    try:
        user_id = auth_dict['uid']

        # Thực hiện join giữa Album và User để lấy thông tin userName
        albums = (
            db.query(
                Album,
                User.name.label("userName")  # Lấy thông tin userName từ bảng User
            )
            .join(User, Album.user_id == User.id, isouter=True)  # Thực hiện join bảng User
            .filter(
                (Album.is_hidden != True) 
            )
            .all()
        )

        # Chuyển đổi kết quả thành danh sách JSON với thông tin userName
        album_list = []
        for album, userName in albums:
            album_list.append({
                "id": album.id,
                "name": album.name,
                "description": album.description,
                "thumbnail_url": album.thumbnail_url,
                "user_id": album.user_id,
                "is_public": album.is_public,
                "created_at": album.created_at,
                "status": album.status,
                "userName": userName  # Thêm thông tin userName vào kết quả
            })
        
        return album_list

    except Exception as e:
        print(f"Error in get_albums: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create", status_code=201)
async def create_album(
    name: str = Form(...),
    is_public: bool = Form(...),
    thumbnail: UploadFile = File(...),
    x_auth_token: Optional[str] = Header(None),
    auth_dict: dict = Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    try:
        user_id = auth_dict['uid']
        
        # Kiểm tra user tồn tại
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy thông tin người dùng"
            )
            
        # Validate thumbnail
        if not thumbnail.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="File phải là hình ảnh"
            )
            
        # Upload thumbnail lên Cloudinary
        try:
            thumbnail_res = cloudinary.uploader.upload(
                thumbnail.file,
                folder="albums",
                resource_type="image"
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail="Không thể upload ảnh thumbnail"
            )
            
        # Tạo album mới
        new_album = Album(
            id=str(uuid.uuid4()),
            name=name,
            thumbnail_url=thumbnail_res['url'],
            user_id=user_id,
            is_public=is_public,
            status='pending',
            is_hidden=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(new_album)
        db.commit()
        db.refresh(new_album)
        
        return {
            "message": "Tạo album thành công",
            "data": {
                "id": new_album.id,
                "name": new_album.name,
                "thumbnail_url": new_album.thumbnail_url,
                "is_public": new_album.is_public,
                "user_id": new_album.user_id
            }
        }
        
    except HTTPException as he:
        db.rollback()
        print(f"HTTP Exception: {he.detail}")
        raise he
    except Exception as e:
        db.rollback()
        print(f"Error in create_album: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi tạo album"
        )

@router.post("/{album_id}/upload-song")
async def upload_song_to_album(
    album_id: str,
    song: UploadFile = File(...),
    thumbnail: UploadFile = File(...),
    song_name: str = Form(...),
    artist: str = Form(...),
    hex_code: str = Form(...),
    artist_image: UploadFile = File(None),
    db: Session = Depends(get_db),
    auth_dict = Depends(auth_middleware)
):
    try:
        # Kiểm tra album tồn tại
        album = db.query(Album).filter(Album.id == album_id).first()
        if not album:
            raise HTTPException(status_code=404, detail="Album không tồn tại")
            
        # Kiểm tra quyền sở hữu sử dụng uid
        if album.user_id != auth_dict['uid']:
            raise HTTPException(status_code=403, detail="Không có quyền thêm bài hát vào album này")

        # Xử lý nghệ sĩ
        normalized_name = normalize_artist_name(artist)
        artist_obj = db.query(Artist).filter(Artist.normalized_name == normalized_name).first()
        
        if not artist_obj:
            # Upload ảnh nghệ sĩ nếu có
            image_url = None
            if artist_image:
                image_res = cloudinary.uploader.upload(
                    artist_image.file,
                    folder="artists",
                    resource_type="image"
                )
                image_url = image_res['url']
                
            artist_obj = Artist(
                id=str(uuid.uuid4()),
                name=artist,
                normalized_name=normalized_name,
                image_url=image_url
            )
            db.add(artist_obj)
            
        # Upload bài hát và thumbnail
        song_res = cloudinary.uploader.upload(
            song.file,
            folder="songs",
            resource_type="auto"
        )
        
        thumbnail_res = cloudinary.uploader.upload(
            thumbnail.file,
            folder="thumbnails",
            resource_type="image"
        )
        
        # Tạo bài hát mới
        new_song = Song(
            id=str(uuid.uuid4()),
            song_name=song_name,
            url=song_res['url'],
            thumbnail_url=thumbnail_res['url'],
            album_id=album_id,
            hex_code=hex_code,
            artist_id=artist_obj.id
        )
        
        db.add(new_song)
        db.commit()
        
        return {
            "message": "Đã thêm bài hát vào album thành công",
            "artist": {
                "id": artist_obj.id,
                "name": artist_obj.name,
                "image_url": artist_obj.image_url
            }
        }
        
    except HTTPException as he:
        db.rollback()
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Có lỗi xảy ra: {str(e)}")

@router.put("/{album_id}")
async def update_album(
    album_id: str,
    name: str = Form(None),
    description: str = Form(None),
    is_public: bool = Form(None),
    thumbnail: UploadFile = File(None),
    db: Session = Depends(get_db),
    auth_dict = Depends(auth_middleware)
):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album không tồn tại")
    # Sử dụng uid để kiểm tra quyền
    if album.user_id != auth_dict['uid']:
        raise HTTPException(status_code=403, detail="Không có quyền chỉnh sửa album này")

    if name:
        album.name = name
    if description:
        album.description = description
    if is_public is not None:
        album.is_public = is_public
    if thumbnail:
        thumbnail_res = cloudinary.uploader.upload(
            thumbnail.file,
            folder="albums",
            resource_type="image"
        )
        album.thumbnail_url = thumbnail_res['url']

    db.commit()
    return {"message": "Cập nhật album thành công"}

@router.get("/{album_id}/songs")
async def get_album_songs(
    album_id: str,
    db: Session = Depends(get_db),
    auth_dict = Depends(auth_middleware)
):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album không tồn tại")
        
    # Kiểm tra quyền truy cập sử dụng uid
    if not album.is_public and album.user_id != auth_dict['uid']:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập album này")
    
    # Lấy thông tin bài hát kèm nghệ sĩ
    songs = db.query(Song).join(Artist).filter(Song.album_id == album_id).all()
    return songs

@router.delete("/{album_id}")
async def delete_album(
    album_id: str,
    db: Session = Depends(get_db),
    auth_dict = Depends(auth_middleware)
):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album không tồn tại")
    # Sử dụng uid để kiểm tra quyền
    if album.user_id != auth_dict['uid']:
        raise HTTPException(status_code=403, detail="Không có quyền xóa album này")

    try:
        # Xóa tất cả tài nguyên liên quan trên Cloudinary
        if album.thumbnail_url:
            # Lấy public_id từ URL
            public_id = album.thumbnail_url.split('/')[-1].split('.')[0]
            cloudinary.uploader.destroy(public_id)
        
        # Xóa album trong database
        db.delete(album)
        db.commit()
        
        return {"message": "Đã xóa album thành công"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa album: {str(e)}")

@router.post("/auth/artist/albums", response_model=AlbumResponse)
async def create_album(
    name: str = Form(...),
    description: str = Form(None),
    is_public: bool = Form(True),
    thumbnail: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth_dict = Depends(auth_middleware)
):
    try:
        user_id = auth_dict["uid"]
        
        # Upload thumbnail to Cloudinary trước
        result = cloudinary.uploader.upload(
            thumbnail.file,
            folder=f"albums/thumbnails/{user_id}",
            resource_type="image"
        )
        
        # Kiểm tra kết quả upload
        thumbnail_url = result.get("secure_url")
        if not thumbnail_url:
            raise HTTPException(
                status_code=500, 
                detail="Lỗi khi tải lên ảnh thumbnail"
            )

        # Tạo album mới sau khi đã có thumbnail_url
        new_album = Album(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            thumbnail_url=thumbnail_url,  # Sử dụng thumbnail_url từ kết quả upload
            is_public=is_public,
            user_id=user_id
        )
        
        db.add(new_album)
        db.commit()
        db.refresh(new_album)
        
        return new_album
        
    except Exception as e:
        print("Error creating album:", str(e))
        raise HTTPException(
            status_code=500, 
            detail=f"Lỗi khi tạo album: {str(e)}"
        )























class SearchRequest(BaseModel):
    search: Optional[str] = None  # Tham số tìm kiếm (tuỳ chọn)


class SearchRequest(BaseModel):
    search: Optional[str] = None  # Tham số tìm kiếm (tuỳ chọn)

@router.post('/listdoiduyet')
def list_songs(request: SearchRequest, db: Session = Depends(get_db), auth_details = Depends(auth_middleware)):
    songs = db.query(Album).filter(Album.is_hidden == False).all()
    return songs

@router.post('/listdaduyet')
def list_songs(request: SearchRequest, db: Session = Depends(get_db), auth_details = Depends(auth_middleware)):
    songs = db.query(Album).filter(Album.status == "approved").all()
    return songs


@router.post('/listtuchoi')
def list_songs(db: Session=Depends(get_db), 
               auth_details=Depends(auth_middleware)):
    songs = db.query(Album).filter(Album.status == "rejected").all()
    return songs

@router.post('/listbian')
def list_songs(request: SearchRequest, db: Session = Depends(get_db), auth_details = Depends(auth_middleware)):
    songs = db.query(Album).filter(Album.is_hidden == True).all()
    return songs

# Định nghĩa lớp yêu cầu WeekDetailRequest

# Định nghĩa lớp yêu cầu WeekDetailRequest
class WeekDetailRequest(BaseModel):
    date: datetime  # Ngày bất kỳ trong tuần

@router.post("/songs/top-like-week-detail")
def get_top_played_songs_with_details(
    request: WeekDetailRequest,
    db: Session = Depends(get_db)
):
    # Sử dụng ngày được gửi trong yêu cầu
    input_date = request.date
    
    # Xác định ngày thứ Hai của tuần đó
    days_to_monday = (input_date.weekday() - 0) % 7  # 0 là thứ Hai trong Python's weekday()
    monday_date = input_date - timedelta(days=days_to_monday)

    # Tính ngày kết thúc tuần (Chủ Nhật)
    week_start = monday_date.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    print(f"Week start: {week_start}, Week end: {week_end}")

    # Truy vấn dữ liệu chi tiết lượt nghe trong tuần này
    song_details = db.query(
        Favorite.song_id,
        Song.song_name,
        Album.name.label("album_name"),
        Song.user_id,
        Favorite.created_at  
    ).join(Song, Favorite.song_id == Song.id) \
     .join(Album, Song.album_id == Album.id) \
     .filter(
        Favorite.created_at >= week_start,
        Favorite.created_at < week_end
    ).order_by(Favorite.song_id, Favorite.created_at.asc())  # Sắp xếp theo bài hát và thời gian

    # Kiểm tra nếu không có dữ liệu
    if not song_details:
        return {"message": "Không có bài hát nào trong tuần này."}

    # Chuẩn bị cấu trúc dữ liệu để gom nhóm theo bài hát và từng ngày trong tuần
    grouped_songs = {}
    for detail in song_details:
        if detail.song_id not in grouped_songs:
            grouped_songs[detail.song_id] = {
                "song_name": detail.song_name,
                "album_name": detail.album_name,
                "user_id": detail.user_id,
                "daily_plays": {day: 0 for day in range(7)}  # Tạo dictionary cho từng ngày trong tuần
            }

        # Tính toán ngày trong tuần (0: Thứ Hai, 6: Chủ Nhật)
        day_of_week = (detail.created_at - week_start).days
        grouped_songs[detail.song_id]["daily_plays"][day_of_week] += 1  # Mỗi lần có favorite thì cộng thêm 1

    # Chuyển đổi dữ liệu sang dạng danh sách và cấu trúc chính xác
    result = [
        {
            "song_id": str(song_id),  # Đảm bảo song_id là string
            "song_name": data["song_name"],
            "album_name": data["album_name"],
            "user_id": str(data["user_id"]),  # Đảm bảo user_id là string
            "daily_plays": [
                {"day": day, "play_count": count}
                for day, count in sorted(data["daily_plays"].items())
            ]
        }
        for song_id, data in grouped_songs.items()
    ]

    # Giới hạn số bài hát trả về nếu cần
    limit = 10  # Ví dụ giới hạn kết quả
    result = result[:limit]

    return {
        "message": "Lấy danh sách chi tiết bài hát thành công.",
        "songs": result
    }
@router.post("/songs/top-plays-week-detail1")
def get_top_played_songs_with_details(
    request: WeekDetailRequest,
    db: Session = Depends(get_db)
):
    # Sử dụng ngày được gửi trong yêu cầu
    input_date = request.date
    
    # Xác định ngày thứ Hai của tuần đó
    days_to_monday = (input_date.weekday() - 0) % 7  # 0 là thứ Hai trong Python's weekday()
    monday_date = input_date - timedelta(days=days_to_monday)

    # Tính ngày kết thúc tuần (Chủ Nhật)
    week_start = monday_date.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    print(f"Week start: {week_start}, Week end: {week_end}")

    # Truy vấn dữ liệu chi tiết lượt nghe trong tuần này
    song_details = db.query(
        PlayCountHistory.song_id,
        PlayCountHistory.play_count,
        PlayCountHistory.week_start_date,
        Song.song_name,
        Album.name.label("album_name"),
        Song.user_id
    ).join(Song, PlayCountHistory.song_id == Song.id) \
     .join(Album, Song.album_id == Album.id) \
     .filter(
        PlayCountHistory.week_start_date >= week_start,
        PlayCountHistory.week_start_date < week_end
    ) \
     .order_by(PlayCountHistory.song_id, PlayCountHistory.week_start_date.asc())  # Sắp xếp theo bài hát và thời gian

    # Kiểm tra nếu không có dữ liệu
    if not song_details:
        return {"message": "Không có bài hát nào trong tuần này."}

    # Chuẩn bị cấu trúc dữ liệu để gom nhóm theo bài hát và từng ngày trong tuần
    grouped_songs = {}
    for detail in song_details:
        if detail.song_id not in grouped_songs:
            grouped_songs[detail.song_id] = {
                "song_name": detail.song_name,
                "album_name": detail.album_name,
                "user_id": detail.user_id,
                "daily_plays": {day: 0 for day in range(7)}  # Tạo dictionary cho từng ngày trong tuần
            }

        # Tính toán ngày trong tuần (0: Thứ Hai, 6: Chủ Nhật)
        day_of_week = (detail.week_start_date - week_start).days
        grouped_songs[detail.song_id]["daily_plays"][day_of_week] += detail.play_count

    # Chuyển đổi dữ liệu sang dạng danh sách và cấu trúc chính xác
    result = [
        {
            "song_id": str(song_id),  # Đảm bảo song_id là string
            "song_name": data["song_name"],
            "album_name": data["album_name"],
            "user_id": str(data["user_id"]),  # Đảm bảo user_id là string
            "daily_plays": [
                {"day": day, "play_count": count}
                for day, count in sorted(data["daily_plays"].items())
            ]
        }
        for song_id, data in grouped_songs.items()
    ]

    # Giới hạn số bài hát trả về nếu cần
    limit = 10  # Ví dụ giới hạn kết quả
    result = result[:limit]

    return {
"message": "Lấy danh sách chi tiết bài hát thành công.",
        "songs": result
    }

@router.post("/songs/top-favorites")
def get_top_favorite_songs(
    db: Session = Depends(get_db),
    limit: int = 10,  # Số lượng bài hát top, mặc định là 10
):
    # Lấy danh sách bài hát có tổng lượt yêu thích cao nhất từ bảng Favorite
    top_songs = db.query(
        Favorite.song_id,
        func.count(Favorite.id).label('total_favorite_count'),  # Tính tổng lượt yêu thích
        Song.song_name,
        Song.album_id,
        Song.user_id,
        Album.name,
        User.name  # Lấy tên người dùng (thay vì artist)
    ).join(Song, Favorite.song_id == Song.id) \
    .join(Album, Song.album_id == Album.id) \
    .join(User, Song.user_id == User.id)  # Kết nối với bảng User

    # Nhóm kết quả và sắp xếp theo tổng lượt yêu thích giảm dần
    top_songs = top_songs.group_by(
        Favorite.song_id, Song.song_name, Song.album_id, Song.user_id, Album.name, User.name
    ).order_by(func.count(Favorite.id).desc()).limit(limit)

    # Kiểm tra nếu không có bài hát nào
    if not top_songs:
        return {"message": "Không có bài hát nào."}

    # Trả về danh sách bài hát với tổng lượt yêu thích và tên album
    return {
        "message": "Lấy danh sách bài hát thành công.",
        "top_songs": [
            {
                "id": song.song_id,  # Lấy ID bài hát từ bảng Favorite
                "song_name": song.song_name,
                "album_name": song.name,  # Thêm tên album
                "album_id": song.album_id,
                "user_id": song.user_id,
                "user_name": song.name,  # Thêm tên người dùng
                "favorite_count": song.total_favorite_count,  # Tổng lượt yêu thích
            }
            for song in top_songs
        ],
    }

@router.get("/genres/percentage")
def get_genre_percentage(db: Session = Depends(get_db)):
    """
    API tính tỷ lệ phần trăm các bài hát theo từng thể loại trên toàn bộ dữ liệu.
    """
    # Truy vấn tổng số bài hát
    total_songs_query = db.query(func.count(Song.id)).scalar()

    # Nếu không có bài hát nào, trả về kết quả rỗng
    if total_songs_query == 0:
        return {
            "message": "Không có bài hát nào trong hệ thống.",
            "data": []
        }

    # Truy vấn số lượng bài hát cho từng thể loại
    genre_counts = (
        db.query(Genre.id, Genre.name, func.count(Song.id).label("song_count"))
        .join(Song, Song.genre_id == Genre.id)
        .group_by(Genre.id, Genre.name)
        .all()
    )

    # Tính tỷ lệ phần trăm
    genre_percentages = [
        {
            "genre_id": genre.id,
            "genre_name": genre.name,
            "song_count": genre.song_count,
            "percentage": round((genre.song_count / total_songs_query) * 100, 2)
        }
        for genre in genre_counts
    ]

    return {
        "message": "Tính toán tỷ lệ thể loại thành công.",
        "data": genre_percentages
    }


@router.get('/user_role_counts')
def get_user_role_counts(db: Session = Depends(get_db)):
    """
    API tính tổng số người dùng theo từng role: user, moderator, artist
    và tổng số lượt nghe trong PlayCountHistory, tổng số lượt yêu thích trong Favorite
    """
    try:
        # Tính tổng số người dùng có role là 'user'
        user_count = db.query(User).filter(User.role == 'user').count()

        # Tính tổng số người dùng có role là 'moderator'
        moderator_count = db.query(User).filter(User.role == 'moderator').count()

        # Tính tổng số người dùng có role là 'artist'
        artist_count = db.query(User).filter(User.role == 'artist').count()

        # Tính tổng số lượt nghe trong PlayCountHistory
        total_play_count = db.query(func.sum(PlayCountHistory.play_count)).scalar() or 0

  

        return {
            "user_count": user_count,
            "moderator_count": moderator_count,
            "artist_count": artist_count,
            "total_play_count": total_play_count,
          
        }

    except Exception as e:
        return {"error": str(e)}

@router.post("/song/{song_id}")
async def get_song_by_id(song_id: str, db: Session = Depends(get_db)):
    # Tìm bài hát theo song_id trong cơ sở dữ liệu và lọc các bài hát có is_hidden = false
    song = db.query(Album).filter(Album.id == song_id, Album.status == "pending").first()

    if not song:
        raise HTTPException(status_code=404, detail="Song not found or is hidden")
    
    return song


@router.post("/song/duyetsong/{song_id}")
def approve_artist(
    song_id: str,
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm bài hát theo ID
    song = db.query(Album).filter(Album.id == song_id).first()
    
    if not song:
        raise HTTPException(status_code=404, detail="Bài hát không tồn tại.")
    
    # Lấy thông tin người phê duyệt từ auth_details
    moderator = db.query(User).filter(User.role == "moderator").first()
    
    if not moderator:
        raise HTTPException(status_code=403, detail="Không có quyền phê duyệt.")
    
    # Cập nhật trạng thái và thông tin người phê duyệt
    song.is_hidden = False
    song.approved_by = moderator.id  # Gán ID của moderator
    song.status="approved"
    song.approved_at = datetime.utcnow()  # Gán thời gian hiện tại (UTC)
    
    db.commit()
    db.refresh(song)
    
    return {"message": "Nghệ sĩ đã được phê duyệt thành công.", "artist": song}




@router.post("/song/duyetsong2/{song_id}")
def approve_artist(
    song_id: str,
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm bài hát theo ID
    song = db.query(Album).filter(Album.id == song_id).first()
    
    if not song:
        raise HTTPException(status_code=404, detail="Bài hát không tồn tại.")
    
    # Lấy thông tin người phê duyệt từ auth_details
    # moderator = db.query(User).filter(User.role == "moderator").first()
    
    # if not moderator:
    #     raise HTTPException(status_code=403, detail="Không có quyền phê duyệt.")
    
    # Cập nhật trạng thái và thông tin người phê duyệt
    # song.is_hidden = False
    # song.approved_by = moderator.id  # Gán ID của moderator
    song.status="rejected"
    # song.approved_at = datetime.utcnow()  # Gán thời gian hiện tại (UTC)
    
    db.commit()
    db.refresh(song)
    
    return {"message": "Nghệ sĩ đã bị từ chối phê duyệt thành công.", "artist": song}







@router.post("/song/songtrue/{song_id}")
def approve_artist(
    song_id: str,  # Sửa kiểu dữ liệu thành str
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm nghệ sĩ theo ID 
    song = db.query(Album).filter(Album.id == song_id).first()
    
    if not song:
        # Nếu không tìm thấy nghệ sĩ, trả về lỗi 404
        raise HTTPException(status_code=404, detail="Nghệ sĩ không tồn tại.")
    
    # Cập nhật trạng thái is_approved thành True
    song.is_hidden = True
    db.commit()  # Lưu thay đổi vào cơ sở dữ liệu
    db.refresh(song)  # Tải lại dữ liệu từ cơ sở dữ liệu
    
    return {"message": "Nghệ sĩ đã được phê duyệt thành công.", "artist": song}



class SongApprovalRequest(BaseModel):
    hidden_reason: str

@router.post("/song/songnone/{song_id}")
def approve_artist(
    song_id: str,  # Kiểu dữ liệu là str
    song_request: SongApprovalRequest,  # Nhận hidden_reason từ request body
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm bài hát theo ID
    song = db.query(Album).filter(Album.id == song_id).first()
    
    if not song:
        # Nếu không tìm thấy bài hát, trả về lỗi 404
        raise HTTPException(status_code=404, detail="Bài hát không tồn tại.")
    
    # Tìm người dùng có vai trò "moderator"
    moderator = db.query(User).filter(User.role == "moderator").first()
    
    if not moderator:
        # Nếu không tìm thấy người dùng có vai trò moderator, trả về lỗi
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng với vai trò moderator.")
    
    # Cập nhật trạng thái và lưu thông tin
    song.is_hidden = True  # Phê duyệt bài hát, không còn bị ẩn
    song.hidden_by = moderator.id  # Lưu ID của moderator phê duyệt
    song.hidden_reason = song_request.hidden_reason  # Lưu lý do từ request body
    
    # Lưu thay đổi vào cơ sở dữ liệu
    db.commit()
    db.refresh(song)  # Tải lại dữ liệu từ cơ sở dữ liệu để phản hồi dữ liệu cập nhật
    
    return {
        "message": "Bài hát đã được phê duyệt thành công.",
        "song": song
    }




@router.post("/songnone/{song_id}")
async def get_song_by_id(song_id: str, db: Session = Depends(get_db)):
    # Tìm bài hát theo song_id trong cơ sở dữ liệu và lọc các bài hát có is_hidden = false
    song = db.query(Album).filter(Album.id == song_id, Song.is_hidden == False).first()

    if not song:
        raise HTTPException(status_code=404, detail="Song not found or is hidden")
    
    return song




@router.post("/song/songtrue1/{song_id}")
def approve_artist(
    song_id: str,  # Sửa kiểu dữ liệu thành str
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm nghệ sĩ theo ID 
    song = db.query(Album).filter(Album.id == song_id).first()
    
    if not song:
        # Nếu không tìm thấy nghệ sĩ, trả về lỗi 404
        raise HTTPException(status_code=404, detail="Nghệ sĩ không tồn tại.")
    
    # Cập nhật trạng thái is_approved thành True
    song.is_hidden = False
    db.commit()  # Lưu thay đổi vào cơ sở dữ liệu
    db.refresh(song)  # Tải lại dữ liệu từ cơ sở dữ liệu
    
    return {"message": "Nghệ sĩ đã được phê duyệt thành công.", "artist": song}




#TẤT CẢ LƯỢT TIM CỦA CỦA TỪNG BÀI HÁT TRONG DATA
@router.post("/songs/top-liked-week", tags=["Songs"])
def get_top_liked_songs_week(
    limit: int = 10,
    db: Session = Depends(get_db),
    date: str = None  # Nhận tham số 'date' kiểu chuỗi, mặc định là None
):
    """
    API trả về danh sách các bài hát được thích nhiều nhất trong tuần này.
    Nếu có 'date' thì lấy tuần của ngày đó.
    """
    try:
        # Nếu không truyền 'date', sử dụng ngày hiện tại
        if date:
            try:
                # Chuyển đổi 'date' từ chuỗi thành đối tượng datetime
                date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                return {
                    "error": "Invalid date format. Use 'YYYY-MM-DD HH:MM:SS.ffffff'",
                    "example_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                }
        else:
            # Nếu không có 'date', sử dụng ngày hiện tại
            date = datetime.now()

        # Tính thời gian bắt đầu và kết thúc của tuần
        start_of_week = date - timedelta(days=date.weekday())  # Tính thứ Hai của tuần
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=7)  # Chủ nhật cuối tuần

        # Log tuần được tính toán
        print(f"Start of week: {start_of_week}, End of week: {end_of_week}")

        # Query để tính số lượt thích theo tuần
        top_songs = (
            db.query(
                Song.id.label("song_id"),
                Song.song_name.label("song_name"),
                func.count(Favorite.id).label("like_count")
            )
            .join(Favorite, Song.id == Favorite.song_id, isouter=True)
            .filter(Favorite.created_at >= start_of_week, Favorite.created_at < end_of_week)  # Lọc lượt thích trong tuần này
            .group_by(Song.id, Song.song_name)
            .order_by(desc("like_count"))  # Sắp xếp theo số lượt thích giảm dần
            .limit(limit)  # Giới hạn số kết quả trả về
            .all()
        )

        # Trả về danh sách bài hát hoặc thông báo không có dữ liệu
        if not top_songs:
            return {
                "message": "No liked songs found for the given week.",
                "week": {
                    "start_of_week": start_of_week.isoformat(),
                    "end_of_week": end_of_week.isoformat()
                }
            }

        return {
            "message": "Top liked songs retrieved successfully.",
            "week": {
                "start_of_week": start_of_week.isoformat(),
                "end_of_week": end_of_week.isoformat()
            },
            "top_songs": [
                {
                    "song_id": song.song_id,
                    "song_name": song.song_name,
                    "like_count": song.like_count
                }
                for song in top_songs
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving top liked songs: {str(e)}")
# @router.post("/songs/top-liked-week", tags=["Songs"])
# def get_top_liked_songs_week(limit: int = 10, db: Session = Depends(get_db)):
#     """
#     API trả về danh sách các bài hát được thích nhiều nhất trong tuần này.

#     - `limit`: Số lượng bài hát top cần trả về (mặc định là 10).
#     """
#     try:
#         # Tính thời gian bắt đầu của tuần này
#         start_of_week = datetime.now() - timedelta(days=datetime.now().weekday())
#         start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

#         # Query để tính số lượt thích theo tuần
#         top_songs = (
#             db.query(
#                 Song.id.label("song_id"),
#                 Song.song_name.label("song_name"),
#                 func.count(Favorite.id).label("like_count")
#             )
#             .join(Favorite, Song.id == Favorite.song_id, isouter=True)
#             .filter(Favorite.created_at >= start_of_week)  # Lọc lượt thích trong tuần này
#             .group_by(Song.id, Song.song_name)
#             .order_by(desc("like_count"))  # Sắp xếp theo số lượt thích giảm dần
#             .limit(limit)  # Giới hạn số kết quả trả về
#             .all()
#         )

#         # Chuyển đổi kết quả thành danh sách JSON
#         return {
#             "top_songs": [
#                 {
#                     "song_id": song.song_id,
#                     "song_name": song.song_name,
#                     "like_count": song.like_count
#                 }
#                 for song in top_songs
#             ]
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error retrieving top liked songs: {str(e)}")

#LẤY LƯỢT TIM CỦA BÀI HÁT ĐÓ 
@router.post("/song/likes/{song_id}")
def get_song_likes(
    song_id: str,
    db: Session = Depends(get_db),
):
    # Tìm tất cả lượt thích của bài hát dựa trên song_id
    likes = db.query(Favorite).filter(Favorite.song_id == song_id).all()

    if not likes:
        # Nếu không có lượt thích nào, trả về thông báo
        return {"message": "Bài hát không có lượt thích nào.", "total_likes": 0}

    # Tính tổng số lượt thích
    total_likes = len(likes)

    # Trả về số lượt thích cùng danh sách thông tin
    return {
        "message": "Lấy số lượt thích thành công.",
        "total_likes": total_likes,
        "details": [
            {
                "user_id": like.user_id,
                "liked_at": like.created_at,
            }
            for like in likes
        ],
    }

#CÀI MỌI NƠI ĐỂ TĂNG LƯỢT NGHE CHO BÀI HÁT
@router.post("/song/play/{song_id}")
def increment_play_count(
    song_id: str,
    db: Session = Depends(get_db),
):
    # Tìm bài hát theo ID
    song = db.query(Song).filter(Song.id == song_id).first()

    if not song:
        raise HTTPException(status_code=404, detail="Bài hát không tồn tại.")

    # Tính ngày bắt đầu của tuần (7 ngày trước)
    week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())

    # Kiểm tra xem đã có bản ghi cho tuần này chưa
    play_history = db.query(PlayCountHistory).filter(
        PlayCountHistory.song_id == song.id,
        PlayCountHistory.week_start_date == week_start
    ).first()

    if play_history:
        # Nếu có bản ghi, tăng số lượt nghe
        play_history.play_count += 1
    else:
        # Nếu không có, tạo bản ghi mới cho tuần này
        new_play_history = PlayCountHistory(
            song_id=song.id,
            week_start_date=week_start,
            play_count=1
        )
        db.add(new_play_history)

    db.commit()  # Lưu thay đổi vào cơ sở dữ liệu
    db.refresh(song)  # Làm mới dữ liệu từ cơ sở dữ liệu

    return {
        "message": "Cập nhật lượt nghe thành công.",
        "song_id": song_id,
   
    }


#LƯỢT NGHE TẤT CẢ BÀI HÁT
@router.post("/songs/top-plays")
def get_top_played_songs(
    db: Session = Depends(get_db),
    limit: int = 10,  # Số lượng bài hát top, mặc định là 10
):
    # Lấy danh sách bài hát có số lượt nghe cao nhất từ bảng PlayCountHistory
    top_songs = db.query(
        PlayCountHistory.song_id,
        func.sum(PlayCountHistory.play_count).label('total_play_count'),  # Tính tổng lượt nghe
        Song.song_name,
        Song.album_id,
        Song.user_id,
        Album.name,
        User.name  # Thêm tên người dùng từ bảng User
    ).join(Song, PlayCountHistory.song_id == Song.id) \
    .join(Album, Song.album_id == Album.id) \
    .join(User, Song.user_id == User.id)  # Kết nối với bảng User

    # Nhóm kết quả và sắp xếp theo tổng lượt nghe giảm dần
    top_songs = top_songs.group_by(
        PlayCountHistory.song_id, Song.song_name, Song.album_id, Song.user_id, Album.name, User.name
    ).order_by(func.sum(PlayCountHistory.play_count).desc()).limit(limit)

    # Kiểm tra nếu không có bài hát nào
    if not top_songs:
        return {"message": "Không có bài hát nào."}

    # Trả về danh sách bài hát với tổng lượt nghe và tên album
    return {
        "message": "Lấy danh sách bài hát thành công.",
        "top_songs": [
            {
                "id": song.song_id,  # Lấy ID bài hát từ bảng PlayCountHistory
                "song_name": song.song_name,
                "album_name": song.name,  # Thêm tên album
                "album_id": song.album_id,
                "user_id": song.user_id,
                "user_name": song.name,  # Thêm tên người dùng
                "play_count": song.total_play_count,  # Tổng lượt nghe
            }
            for song in top_songs
        ],
    }


#LẤY DANH CÁI HÁT CÓ LƯỢT XEM CAO NHẤT TUẦN
@router.post("/songs/top-plays-week")
def get_top_played_songs_this_week(
    db: Session = Depends(get_db),
    limit: int = 100,  # Giới hạn số lượng bài hát trả về
    date: datetime = None,  # Thêm tham số ngày nếu người dùng muốn truyền vào
):
    # Nếu người dùng không truyền vào ngày, lấy tuần hiện tại
    if date is None:
        date = datetime.utcnow()

    # Tính ngày bắt đầu tuần (Thứ Hai)
    week_start = date - timedelta(days=date.weekday())  # Thứ Hai
    week_end = week_start + timedelta(days=7)  # Chủ Nhật

    # Loại bỏ phần thời gian (chỉ so sánh ngày)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_end.replace(hour=0, minute=0, second=0, microsecond=0)

    print(f"Week start: {week_start}, Week end: {week_end}")

    # Truy vấn bài hát trong tuần này và tính tổng lượt nghe
    top_songs = db.query(
        PlayCountHistory.song_id,
        func.sum(PlayCountHistory.play_count).label('total_play_count'),
        Song.song_name,
        Song.album_id,
        Song.user_id,
        Album.name  # Thêm tên album từ bảng Album
    ).join(Song, PlayCountHistory.song_id == Song.id) \
     .join(Album, Song.album_id == Album.id)  \
     .filter(
        PlayCountHistory.week_start_date >= week_start,
        PlayCountHistory.week_start_date < week_end
    ) \
     .group_by(PlayCountHistory.song_id, Song.song_name, Song.album_id, Song.user_id, Album.name) \
     .order_by(func.sum(PlayCountHistory.play_count).desc()) \
     .limit(limit).all()  # Giới hạn số lượng bài hát trả về và sắp xếp theo lượt nghe giảm dần

    if not top_songs:
        return {"message": "Không có bài hát nào trong tuần này."}

    # Trả về danh sách bài hát với tổng lượt nghe và tên album
    return {
        "message": "Lấy danh sách bài hát thành công.",
        "top_songs": [
            {
                "id": song.song_id,  # Lấy ID bài hát từ bảng PlayCountHistory
                "song_name": song.song_name,
                "album_name": song.name,  # Thêm tên album
                "album_id": song.album_id,
                "user_id": song.user_id,
                "total_play_count": song.total_play_count,  # Tổng lượt nghe
            }
            for song in top_songs
        ],
    }



@router.post("/album/banned/{album_id}")
def ban_album(
    album_id: str,  # ID của album
    song_request: SongApprovalRequest,  # Nhận hidden_reason từ request body
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm album theo ID
    album = db.query(Album).filter(Album.id == album_id).first()

    if not album:
        # Nếu không tìm thấy album, trả về lỗi 404
        raise HTTPException(status_code=404, detail="Album không tồn tại.")
    
    # Tìm người dùng có vai trò "moderator"
    moderator = db.query(User).filter(User.role == "moderator").first()

    if not moderator:
        # Nếu không tìm thấy người dùng có vai trò moderator, trả về lỗi
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng với vai trò moderator.")
    
    # Cập nhật trạng thái của album
    album.is_hidden = False  # Đánh dấu album bị ẩn
    album.hidden_by = moderator.id  # Lưu ID của moderator thực hiện hành động
    album.hidden_reason = song_request.hidden_reason  # Lưu lý do từ request body

    # Cập nhật trạng thái của tất cả bài hát trong album
    songs = db.query(Song).filter(
        Song.album_id == album_id,
       # Loại trừ các bài hát có is_hidden = False và status = "pending"
    ).all()

    for song in songs:
        song.is_hidden = False  # Ẩn các bài hát
        song.hidden_reason = song_request.hidden_reason
        song.hidden_by = moderator.id

    # Lưu thay đổi vào cơ sở dữ liệu
    db.commit()

    # Trả về thông báo thành công và danh sách các bài hát bị ẩn
    return {
        "message": "Album và các bài hát đủ điều kiện trong album đã bị ẩn thành công.",
        "album": album,
        "hidden_songs": songs
    }



@router.post("/album/unbanned/{album_id}")
def unban_album(
    album_id: str,  # ID của album
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm album theo ID
    album = db.query(Album).filter(Album.id == album_id).first()

    if not album:
        # Nếu không tìm thấy album, trả về lỗi 404
        raise HTTPException(status_code=404, detail="Album không tồn tại.")
    
    # Tìm người dùng có vai trò "moderator"
    moderator = db.query(User).filter(User.role == "moderator").first()

    if not moderator:
        # Nếu không tìm thấy người dùng có vai trò moderator, trả về lỗi
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng với vai trò moderator.")
    
    # Cập nhật trạng thái của album
    album.is_hidden = False  # Đặt trạng thái album là None (gỡ ẩn)
    album.hidden_by = None  # Xóa thông tin người thực hiện ẩn
    album.hidden_reason = ""  # Xóa lý do ẩn
    # db.commit()  # Lưu thay đổi của album trước
    
    # Cập nhật trạng thái của tất cả bài hát trong album
    # Loại trừ bài hát có is_hidden = False và status = "pending"
    songs = db.query(Song).filter(Song.album_id == album_id).all()
    for song in songs:
        if song.status != "pending":  # Kiểm tra nếu không ở trạng thái "pending"
            song.is_hidden = True
            song.hidden_reason = ""
            song.hidden_by = moderator.id 
    db.commit()  # Lưu thay đổi của bài hát

    # Trả về thông báo thành công
    return {
        "message": "Album đã được gỡ ẩn, và các bài hát đủ điều kiện trong album đã bị ẩn.",
        "album": album,
        "updated_songs": songs
    }
