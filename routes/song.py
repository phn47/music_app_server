from datetime import datetime, timedelta
# from http.client import HTTPException
from fastapi import HTTPException
import os
import uuid
from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy import and_, case, desc, func, or_
from sqlalchemy.orm import Session
from database import get_db
from middleware.auth_middleware import auth_middleware
import cloudinary
import cloudinary.uploader
from models.block import Block
from models.favorite import Favorite
from models.follower import Follower
from models.genre import Genre
from models.song import Song
# from models.blocked_group_member import BlockedGroupMember
from models.message_reaction import MessageReaction
from pydantic_schemas.favorite_song import FavoriteSong
from sqlalchemy.orm import joinedload
from models.artist import Artist
from unidecode import unidecode
from typing import List, Optional
from models.song_artist import song_artists
from models.user import User
from sqlalchemy.sql import insert
from models.comment import Comment
# from models.block import Block
from models.group import Group
# from models.message import Message
from models.group_message import GroupMessage
from models.play_count_history import PlayCountHistory
from models.group_member import GroupMember

router = APIRouter()

cloudinary.config( 
    cloud_name = "derzqoidk", 
    api_key = "622479785549768", 
    api_secret = "ZBKYfdGsksqcx0wjvRKtg6v0nn0", 
    secure=True
)

def normalize_artist_name(name: str) -> str:
    return unidecode(name.lower().strip())

@router.post("/listwed")
async def get_song_list(db: Session = Depends(get_db)):
    # Lấy tất cả bài hát từ cơ sở dữ liệu
    songs = db.query(Song).filter(Song.is_hidden==True).all()
    if not songs:
        return {"message": "No songs found"}

    # Trả về danh sách các bài hát với thông tin chi tiết
    return [
        {
            "song": song.song_url,
            "thumbnail": song.thumbnail_url,
            "artist_names": [artist.normalized_name for artist in song.artists],  # Lấy tên nghệ sĩ từ mối quan hệ 'artists'
            "genre_ids": [genre.id for genre in song.genres],  # Lấy id thể loại từ mối quan hệ 'genres'
            "song_name": song.song_name,
            "hex_code": song.hex_code,
            "artist_images": [artist.image_url for artist in song.artists]  # Lấy URL ảnh của nghệ sĩ (nếu có)
        }
        for song in songs
    ]

# @router.get('/list')
# def list_songs(db: Session=Depends(get_db), 
#                auth_details=Depends(auth_middleware)):
#     songs = db.query(Song).options(
#         joinedload(Song.artists)
#     ).all()
#     return songs



@router.get('/list')
def list_songs(db: Session = Depends(get_db), 
               auth_details = Depends(auth_middleware)):
    # Lấy danh sách bài hát kèm thông tin nghệ sĩ và người dùng
    songs = db.query(Song).filter(Song.is_hidden!=False) .options(
        joinedload(Song.artists),  # Load thông tin nghệ sĩ
        joinedload(Song.user)     # Load thông tin người dùng (thêm đoạn này)
    ).all()

    # Map dữ liệu để thêm cột userName
    result = []
    for song in songs:
        result.append({
            "id": song.id,
            "song_url": song.song_url,
            "hex_code": song.hex_code,
            "rejected_reason": song.rejected_reason,
            "song_name": song.song_name,
            "user_id": song.user_id,
         
            "is_hidden": song.is_hidden,
            "album_id": song.album_id,
            "hidden_reason": song.hidden_reason,
            "artist_id": song.artist_id,
            "hidden_by": song.hidden_by,
            "genre_id": song.genre_id,
            "hidden_at": song.hidden_at,
            "userName": song.user.name if song.user else None,  # Thêm userName
            "status": song.status,
            "created_at": song.created_at,
            "approved_by": song.approved_by,
            "updated_at": song.updated_at,
            "thumbnail_url": song.thumbnail_url,
            "approved_at": song.approved_at,
            "artists": [
                {
                    "id": artist.id,
                    "bio": artist.bio,
                    "is_approved": artist.is_approved,
                    "updated_at": artist.updated_at,
                    "approved_by": artist.approved_by,
                    "user_id": artist.user_id,
                    "normalized_name": artist.normalized_name,
                    "image_url": artist.image_url,
                    "created_at": artist.created_at,
                    "approved_at": artist.approved_at,
                }
                for artist in song.artists
            ]
        })

    return result

@router.post('/favorite')
def favorite_song(song: FavoriteSong, 
                  db: Session=Depends(get_db), 
                  auth_details=Depends(auth_middleware)):
    # song is already favorited by the user
    user_id = auth_details['uid']

    fav_song = db.query(Favorite).filter(Favorite.song_id == song.song_id, Favorite.user_id == user_id).first()

    if fav_song:
        db.delete(fav_song)
        db.commit()
        return {'message': False}
    else:
        new_fav = Favorite(id=str(uuid.uuid4()), song_id=song.song_id, user_id=user_id)
        db.add(new_fav)
        db.commit()
        return {'message': True}
    
@router.get("/list/favorites")
def list_fav_songs(
    auth_details: dict = Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    try:     
        user_id = auth_details['uid']
               
        favorites = db.query(Favorite).filter(
            Favorite.user_id == user_id
        ).options(
            joinedload(Favorite.song)
        ).all()
        
        # Trả về danh sách các bài hát
        return [fav.song for fav in favorites]
        
    except Exception as e:
        print(f"Error in list_fav_songs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi lấy danh sách bài hát yêu thích"
        )

@router.get('/search')
def search_songs(query: str="", db: Session = Depends(get_db)):
    # Thực hiện truy vấn với điều kiện tìm kiếm
    songs = db.query(Song).join(Song.artists).filter(
        (Song.song_name.ilike(f"%{query}%")) | (Artist.normalized_name.ilike(f"%{query}%"))
    ).all()
    result = []
    for song in songs:
        song_dict = song.as_dict()
        song_dict['userName'] = song.user.name  # Giả sử trong model User có trường username
        result.append(song_dict)
    
    return result


# @router.get('/search/{query}')
# def search_songs(query: str, db: Session = Depends(get_db)):
#     # Thực hiện truy vấn với điều kiện tìm kiếm
#     songs = db.query(Song).join(Song.artists).filter(
#         (Song.song_name.ilike(f"%{query}%")) | (Artist.normalized_name.ilike(f"%{query}%"))
#     ).all()

#     # Chuyển đổi danh sách đối tượng `Song` thành danh sách dictionary
#     results = []
#     for song in songs:
#         song_dict = song.as_dict()
#         song_dict["artists"] = [{"id": artist.id, "normalized_name": artist.normalized_name} for artist in song.artists]
#         results.append(song_dict)

#     return results



# @router.get('/search/{query}')
# def search_songs(query: str, db: Session = Depends(get_db)):
#     # Thực hiện truy vấn với điều kiện tìm kiếm
#     songs = db.query(Song).join(Song.artists).filter(
#         (Song.song_name.ilike(f"%{query}%")) | (Artist.normalized_name.ilike(f"%{query}%"))
#     ).all()

#     # Chuyển đổi danh sách đối tượng `Song` thành danh sách dictionary
#     results = []
#     for song in songs:
#         song_dict = song.as_dict()
#         song_dict["artists"] = [{"id": artist.id, "normalized_name": artist.normalized_name} for artist in song.artists]
#         results.append(song_dict)

#     return results

@router.get('/user/songs')
def get_user_songs(db: Session = Depends(get_db), auth_dict = Depends(auth_middleware)):
    try:
        # Lấy user_id từ token đã xác thực
        user_id = auth_dict['uid']
        
        # Lấy các bài hát của user hiện tại
        songs = db.query(Song).filter(Song.user_id == user_id).all()
        return songs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete('/{song_id}')
async def delete_song(
    song_id: str,
    db: Session = Depends(get_db),
    auth_dict = Depends(auth_middleware)
):
    try:
        # Kiểm tra bài hát tồn tại
        song = db.query(Song).filter(Song.id == song_id).first()
        if not song:
            raise HTTPException(status_code=404, detail="Bài hát không tồn tại")
            
        # Kiểm tra quyền sở hữu
        if song.user_id != auth_dict['uid']:
            raise HTTPException(status_code=403, detail="Không có quyền xóa bài hát này")

        # Xóa tất cả favorites liên quan
        db.query(Favorite).filter(Favorite.song_id == song_id).delete()
        
        # Xóa bài hát
        db.delete(song)
        db.commit()
        
        return {"message": "Đã xóa bài hát thành công"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put('/{song_id}')
async def update_song(
    song_id: str,
    song_name: str = Form(None),
    artist_name: str = Form(None),
    hex_code: str = Form(None),
    thumbnail: UploadFile = File(None),
    db: Session = Depends(get_db),
    auth_dict = Depends(auth_middleware)
):
    try:
        song = db.query(Song).filter(Song.id == song_id).first()
        if not song:
            raise HTTPException(
                status_code=404, 
                detail="Bài hát không tồn tại"
            )
            
        if song.user_id != auth_dict['uid']:
            raise HTTPException(
                status_code=403, 
                detail="Không có quyền sửa bài hát này"
            )

        if song_name:
            song.song_name = song_name
            
        if artist_name:
            normalized_name = normalize_artist_name(artist_name)
            artist = db.query(Artist).filter(Artist.normalized_name == normalized_name).first()
            
            if not artist:
                artist = Artist(
                    id=str(uuid.uuid4()),  # Thêm id cho artist mới
                    name=artist_name,
                    normalized_name=normalized_name
                )
                db.add(artist)
                db.commit()
                db.refresh(artist)
                
            song.artist_id = artist.id
            
        if hex_code:
            song.hex_code = hex_code
            
        if thumbnail:
            # Xóa thumbnail cũ
            old_thumbnail_id = song.thumbnail_url.split('/')[-1].split('.')[0]
            cloudinary.uploader.destroy(old_thumbnail_id)
            
            # Upload thumbnail mới
            thumbnail_res = cloudinary.uploader.upload(
                thumbnail.file,
                folder=f"songs/{song.id}",
                resource_type="image"
            )
            song.thumbnail_url = thumbnail_res['url']

        db.commit()
        db.refresh(song)
        return song
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

class LyricRequest(BaseModel):
    lyrics: str

# Giả sử có một phương thức để đọc lời bài hát từ tệp LRC
def read_lyrics_from_file(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.readlines()

@router.post("/compare-lyrics/")
async def compare_lyrics(request: LyricRequest):
    input_lyrics = request.lyrics  # Lời bài hát nhập vào
    
    # Tách lời bài hát thành câu đầu tiên dựa trên dấu phân cách như ".", ",", "\n", "\r"
    input_lyrics_sentences = [sentence.strip() for sentence in input_lyrics.replace("\r", "\n").split("\n") if sentence.strip()]
    first_sentence = input_lyrics_sentences[0] if input_lyrics_sentences else ""
    
    if not first_sentence:
        raise HTTPException(status_code=400, detail="No lyrics provided or valid sentence found")

    found_files = []  # Danh sách l��u trữ các file mà có dòng trùng khớp
    processed_files = set()  # Tập hợp để lưu các file đã được xử lý

    # Đọc tất cả các file .lrc.tmp trong thư mục
    directory = "C:/Users/phamn/Desktop/musicapp/server/data/lyrics"
    for filename in os.listdir(directory):
        if filename.endswith(".lrc.tmp"):
            file_path = os.path.join(directory, filename)
            lyrics_from_file = read_lyrics_from_file(file_path)

            # Nếu tệp này đã được xử lý rồi thì bỏ qua
            if filename in processed_files:
                continue

            # Duyệt qua từng dòng trong tệp và so sánh với câu đầu tiên
            for file_line in lyrics_from_file:
                if first_sentence.lower() in file_line.lower():  # So sánh không phân biệt chữ hoa chữ thường
                    # Nếu tìm thấy dòng trùng khớp, thêm toàn bộ tệp vào kết quả và đánh dấu là đã xử lý
                    found_files.append({
                        "file": filename,
                        "lyrics": ''.join(lyrics_from_file),  # Trả về dữ liệu LRC gốc
                    })
                    processed_files.add(filename)  # Đánh dấu tệp đã được xử lý
                    break  # Dừng ki��m tra các câu tiếp theo sau khi đã tìm thấy câu trùng khớp

    if not found_files:
        raise HTTPException(status_code=404, detail="No matching lyrics found")
    
    return {"matching_files": found_files}

@router.post("/my-songs")
async def get_my_songs(current_user = Depends(auth_middleware), db: Session = Depends(get_db)):
    try:
        print("Current user:", current_user)
        # Lấy artist_id từ bảng artists dựa vào user_id
        artist = db.query(Artist).filter(Artist.user_id == current_user['id']).first()
        print("Found artist:", artist)
        
        if not artist:
            raise HTTPException(status_code=404, detail="Không tìm thấy nghệ sĩ")

        # Lấy danh sách bài hát thông qua quan hệ song_artists
        songs = (
            db.query(Song)
            .join(song_artists)
            .filter(song_artists.c.artist_id == artist.id)
            .all()
        )
        print("Found songs:", songs)
        
        # Chuyển đổi kết quả thành JSON
        songs_data = []
        for song in songs:
            songs_data.append({
                "id": song.id,
                "song_name": song.song_name,
                "song_url": song.song_url,
                "thumbnail_url": song.thumbnail_url,
                "hex_code": song.hex_code,
                "artist_id": artist.id,
                "album_id": song.album_id,
                "play_count": song.play_count,
                "created_at": song.created_at,
            })
        
        return songs_data
        
    except Exception as e:
        print("Error getting my songs:", str(e))
        raise HTTPException(status_code=500, detail="Lỗi khi lấy danh sách bài hát")

@router.get("/search/by-artist/{artist_name}")
async def search_songs_by_artist(
    artist_name: str,
    db: Session = Depends(get_db)
):
    try:
        # Tìm kiếm không phân biệt hoa thường
        artist = db.query(User).filter(
            User.role == 'artist',
            User.name.ilike(f"%{artist_name}%")
        ).first()
        
        if not artist:
            return []

        # Lấy tất cả bài hát có liên quan đến nghệ sĩ (cả hát solo và hát chung)
        songs = db.query(Song).join(
            song_artists,
            Song.id == song_artists.c.song_id
        ).filter(
            song_artists.c.artist_id == artist.id
        ).all()

        return [{
            "id": song.id,
            "name": song.song_name,
            "thumbnail_url": song.thumbnail_url,
            "song_url": song.song_url,
            "hex_code": song.hex_code,
            "is_main_artist": db.query(song_artists).filter(
                song_artists.c.song_id == song.id,
                song_artists.c.artist_id == artist.id,
                song_artists.c.is_main_artist == True
            ).first() is not None
        } for song in songs]

    except Exception as e:
        print(f"Error searching songs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi tìm kiếm bài hát: {str(e)}"
        )
    
@router.get("/genres")
async def get_all_genres(db: Session = Depends(get_db)):
    try:
        genres = db.query(Genre).all()
        return [
            {
                "id": genre.id,
                "name": genre.name,
                "image_url": genre.image_url,
                "hex_code": genre.hex_code,
                "description": genre.description
            }
            for genre in genres
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))














# phần web 
@router.post("/song/songnone14/{song_id}")
def approve_artist(
    song_id: str,  # Kiểu dữ liệu là str
    # song_request: SongApprovalRequest,  # Nhận hidden_reason từ request body
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm bài hát theo ID
    song = db.query(Song).filter(Song.id == song_id).first()
    
    if not song:
        # Nếu không tìm thấy bài hát, trả về lỗi 404
        raise HTTPException(status_code=404, detail="Bài hát không tồn tại.")
    
    # Tìm người dùng có vai trò "moderator"
    moderator = db.query(User).filter(User.role == "artist").first()
    
    if not moderator:
        # Nếu không tìm thấy người dùng có vai trò moderator, trả về lỗi
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng với vai trò artist.")
    
    # Cập nhật trạng thái và lưu thông tin
    song.is_hidden = None  # Phê duyệt bài hát, không còn bị ẩn
    song.hidden_by = moderator.id  # Lưu ID của moderator phê duyệt
    # song.hidden_reason = song_request.hidden_reason  # Lưu lý do từ request body
    
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
    song = db.query(Song).filter(Song.id == song_id).first()

    if not song:
        raise HTTPException(status_code=404, detail="Song not found or is hidden")
    
    return {
        "id": song.id,
        "song_name": song.song_name,
        "thumbnail_url": song.thumbnail_url,
        "song_url": song.song_url,
        "hex_code": song.hex_code,
        "status": song.status,
        "created_at": song.created_at,
        "updated_at": song.updated_at,
        "artist_names": [artist.normalized_name for artist in song.artists],  # Giả sử bạn có quan hệ với Artist
        # "genre_names": [genre.name for genre in song.genres],  # Giả sử bạn có quan hệ với Genre
    }





@router.post("/songguilai/{song_id}")
async def get_song_by_id(song_id: str, db: Session = Depends(get_db)):
    # Tìm bài hát theo song_id trong cơ sở dữ liệu và lọc các bài hát có is_hidden = false
    song = db.query(Song).filter(Song.id == song_id).first()

    if not song:
        raise HTTPException(status_code=404, detail="Song not found or is hidden")
    
    return {
        "id": song.id,
        "song_name": song.song_name,
        "thumbnail_url": song.thumbnail_url,
        "song_url": song.song_url,
        "hex_code": song.hex_code,
        "status": song.status,
        "created_at": song.created_at,
        "updated_at": song.updated_at,
        "artist_names": [artist.normalized_name for artist in song.artists],  # Giả sử bạn có quan hệ với Artist
        # "genre_names": [genre.name for genre in song.genres],  # Giả sử bạn có quan hệ với Genre
    }


@router.post("/song/duyetsong3/{song_id}")
def approve_artist(
    song_id: str,
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm bài hát theo ID
    song = db.query(Song).filter(Song.id == song_id).first()
    
    if not song:
        raise HTTPException(status_code=404, detail="Bài hát không tồn tại.")
    
    # Lấy thông tin người phê duyệt từ auth_details
    moderator = db.query(User).filter(User.role == "moderator").first()
    
    if not moderator:
        raise HTTPException(status_code=403, detail="Không có quyền từ chối duyệt.")
    
  
    song.status="pending"
    
    
    db.commit()
    db.refresh(song)
    
    return {"message": "Nghệ sĩ đã bị từ chối phê duyệt.", "artist": song}


class ThumbnailRequest(BaseModel):
    thumbnail_url: str

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
    song = db.query(Song).filter(Song.id == song_id).first()
    
    if not song:
        # Nếu không tìm thấy bài hát, trả về lỗi 404
        raise HTTPException(status_code=404, detail="Bài hát không tồn tại.")
    
    # Tìm người dùng có vai trò "moderator"
    moderator = db.query(User).filter(User.role == "moderator").first()
    
    if not moderator:
        # Nếu không tìm thấy người dùng có vai trò moderator, trả về lỗi
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng với vai trò moderator.")
    
    # Cập nhật trạng thái và lưu thông tin
    song.is_hidden = None  # Phê duyệt bài hát, không còn bị ẩn
    song.hidden_by = moderator.id  # Lưu ID của moderator phê duyệt
    song.hidden_reason = song_request.hidden_reason  # Lưu lý do từ request body
    
    # Lưu thay đổi vào cơ sở dữ liệu
    db.commit()
    db.refresh(song)  # Tải lại dữ liệu từ cơ sở dữ liệu để phản hồi dữ liệu cập nhật
    
    return {
        "message": "Bài hát đã được phê duyệt thành công.",
        "song": song
    }

@router.post("/song/songnone1/{song_id}")
def approve_artist(
    song_id: str,  # Kiểu dữ liệu là str
    # song_request: SongApprovalRequest,  # Nhận hidden_reason từ request body
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm bài hát theo ID
    song = db.query(Song).filter(Song.id == song_id).first()
    
    if not song:
        # Nếu không tìm thấy bài hát, trả về lỗi 404
        raise HTTPException(status_code=404, detail="Bài hát không tồn tại.")
    
    # Tìm người dùng có vai trò "moderator"
    moderator = db.query(User).filter(User.role == "artist").first()
    
    if not moderator:
        # Nếu không tìm thấy người dùng có vai trò moderator, trả về lỗi
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng với vai trò moderator.")
    
    # Cập nhật trạng thái và lưu thông tin
    song.is_hidden = None  # Phê duyệt bài hát, không còn bị ẩn
    song.hidden_by = moderator.id  # Lưu ID của moderator phê duyệt
    # song.hidden_reason = song_request.hidden_reason  # Lưu lý do từ request body
    
    # Lưu thay đổi vào cơ sở dữ liệu
    db.commit()
    db.refresh(song)  # Tải lại dữ liệu từ cơ sở dữ liệu để phản hồi dữ liệu cập nhật
    
    return {
        "message": "Bài hát đã được phê duyệt thành công.",
        "song": song
    }

@router.post("/songtrue/{song_id}")
async def get_song_by_id(song_id: str, db: Session = Depends(get_db)):
    # Tìm bài hát theo song_id trong cơ sở dữ liệu và lọc các bài hát có is_hidden = false
    song = db.query(Song).filter(Song.id == song_id, Song.is_hidden == True).first()

    # if not song:
    #     raise HTTPException(status_code=404, detail="Song not found or is hidden")
    
    return {
        "id": song.id,
        "song_name": song.song_name,
        "thumbnail_url": song.thumbnail_url,
        "song_url": song.song_url,
        "hex_code": song.hex_code,
        "status": song.status,
        "created_at": song.created_at,
        "updated_at": song.updated_at,
        "artist_names": [artist.normalized_name for artist in song.artists],  # Giả sử bạn có quan hệ với Artist
        # "genre_names": [genre.name for genre in song.genres],  # Giả sử bạn có quan hệ với Genre
    }


@router.post("/song/songtrue/{song_id}")
def approve_artist(
    song_id: str,  # Sửa kiểu dữ liệu thành str
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm nghệ sĩ theo ID 
    song = db.query(Song).filter(Song.id == song_id).first()
    
    if not song:
        # Nếu không tìm thấy nghệ sĩ, trả về lỗi 404
        raise HTTPException(status_code=404, detail="Nghệ sĩ không tồn tại.")
    
    # Cập nhật trạng thái is_approved thành True
    song.is_hidden = True
    db.commit()  # Lưu thay đổi vào cơ sở dữ liệu
    db.refresh(song)  # Tải lại dữ liệu từ cơ sở dữ liệu
    
    return {"message": "Nghệ sĩ đã được phê duyệt thành công.", "artist": song}

@router.post("/song/duyetsong/{song_id}")
def approve_artist(
    song_id: str,
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm bài hát theo ID
    song = db.query(Song).filter(Song.id == song_id).first()
    
    if not song:
        raise HTTPException(status_code=404, detail="Bài hát không tồn tại.")
    
    # Lấy thông tin người phê duyệt từ auth_details
    moderator = db.query(User).filter(User.role == "moderator").first()
    
    if not moderator:
        raise HTTPException(status_code=403, detail="Không có quyền phê duyệt.")
    
    # Cập nhật trạng thái và thông tin người phê duyệt
    song.is_hidden = True
    song.approved_by = moderator.id  # Gán ID của moderator
    song.approved_at = datetime.utcnow()  # Gán thời gian hiện tại (UTC)
    song.status="approved"
    
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
    song = db.query(Song).filter(Song.id == song_id).first()
    
    if not song:
        raise HTTPException(status_code=404, detail="Bài hát không tồn tại.")
    
    # Lấy thông tin người phê duyệt từ auth_details
    moderator = db.query(User).filter(User.role == "moderator").first()
    
    if not moderator:
        raise HTTPException(status_code=403, detail="Không có quyền từ chối duyệt.")
    
  
    song.status="rejected"
    
    
    db.commit()
    db.refresh(song)
    
    return {"message": "Nghệ sĩ đã bị từ chối phê duyệt.", "artist": song}


@router.post("/song/{song_id}")
async def get_song_by_id(song_id: str, db: Session = Depends(get_db)):
    # Tìm bài hát theo song_id trong cơ sở dữ liệu và lọc các bài hát có is_hidden = false
    song = db.query(Song).filter(Song.id == song_id, Song.is_hidden == False).first()

    if not song:
        raise HTTPException(status_code=404, detail="Song not found or is hidden")
    
    return {
        "id": song.id,
        "song_name": song.song_name,
        "thumbnail_url": song.thumbnail_url,
        "song_url": song.song_url,
        "hex_code": song.hex_code,
        "status": song.status,
        "created_at": song.created_at,
        "updated_at": song.updated_at,
        "artist_names": [artist.normalized_name for artist in song.artists],  # Giả sử bạn có quan hệ với Artist
        # "genre_names": [genre.name for genre in song.genres],  # Giả sử bạn có quan hệ với Genre
    }

class SearchRequest(BaseModel):
    search: Optional[str] = None  # Tham số tìm kiếm (tuỳ chọn)

@router.post("/listwed2")
async def get_visible_songs(request: SearchRequest, db: Session = Depends(get_db)):
    search = request.search  # Lấy tham số search từ JSON body

    # Lọc các bài hát có is_hidden = False và status = "pending"
    query = db.query(Song).filter(Song.is_hidden == False, Song.status == "pending")

    # Nếu có tham số tìm kiếm, tìm theo normalized_name
    if search:
        query = query.filter(Song.song_name.ilike(f"%{search}%"))

    songs = query.all()

    return [
        {
            "id": song.id,
            "song_name": song.song_name,
            "thumbnail_url": song.thumbnail_url,
            "song_url": song.song_url,
            "hex_code": song.hex_code,
            "status": song.status,
            "created_at": song.created_at,
            "updated_at": song.updated_at,
            "artist_names": [artist.normalized_name for artist in song.artists],  # Nếu có quan hệ với Artist
            # "genre_names": [genre.name for genre in song.genres],  # Nếu có quan hệ với Genre
        }
        for song in songs
    ]

# Endpoint cho listwed3 (hidden songs)
@router.post("/listwed3")
async def get_hidden_songs(request: SearchRequest, db: Session = Depends(get_db)):
    search = request.search  # Lấy tham số search từ JSON body

    # Lọc các bài hát có is_hidden = True
    query = db.query(Song).filter(Song.is_hidden == True)

    # Nếu có tham số tìm kiếm, tìm theo normalized_name
    if search:
        query = query.filter(Song.song_name.ilike(f"%{search}%"))

    songs = query.all()

    return [
        {
            "id": song.id,
            "song_name": song.song_name,
            "thumbnail_url": song.thumbnail_url,
            "song_url": song.song_url,
            "hex_code": song.hex_code,
            "status": song.status,
            "created_at": song.created_at,
            "updated_at": song.updated_at,
            "artist_names": [artist.normalized_name for artist in song.artists],  # Nếu có quan hệ với Artist
        }
        for song in songs
    ]

# Endpoint cho listwed4 (songs có is_hidden = None)
@router.post("/listwed4")
async def get_songs_with_no_hidden_status(request: SearchRequest, db: Session = Depends(get_db)):
    search = request.search  # Lấy tham số search từ JSON body

    # Lọc các bài hát có is_hidden là None
    query = db.query(Song).filter(Song.is_hidden == None)

    # Nếu có tham số tìm kiếm, tìm theo normalized_name
    if search:
        query = query.filter(Song.song_name.ilike(f"%{search}%"))

    songs = query.all()

    return [
        {
            "id": song.id,
            "song_name": song.song_name,
            "thumbnail_url": song.thumbnail_url,
            "song_url": song.song_url,
            "hex_code": song.hex_code,
            "status": song.status,
            "created_at": song.created_at,
            "updated_at": song.updated_at,
            "artist_names": [artist.normalized_name for artist in song.artists],  # Nếu có quan hệ với Artist
        }
        for song in songs
    ]

@router.post("/playwed")
async def get_song_by_thumbnail(request: ThumbnailRequest, db: Session = Depends(get_db)):
    thumbnail_url = request.thumbnail_url  # Lấy thumbnail_url từ body

    # Tìm bài hát có thumbnail_url trùng với tham số truyền vào
    song = db.query(Song).filter(Song.thumbnail_url == thumbnail_url).first()

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Trả về song_url của bài hát tìm được
    return {"song_url": song.song_url}

@router.post("/playnextwed")
async def get_next_song_by_url(request: ThumbnailRequest, db: Session = Depends(get_db)):
    song_url = request.thumbnail_url  # Lấy song_url từ body (trong yêu cầu của bạn)

    # Tìm bài hát có song_url trùng với tham số truyền vào
    song = db.query(Song).filter(Song.song_url == song_url).first()

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Lấy tất cả bài hát trong cơ sở dữ liệu (có thể sắp xếp theo ID hoặc theo thời gian phát hành)
    all_songs = db.query(Song).order_by(Song.id).all()  # Sắp xếp theo ID tăng dần

    # Tìm chỉ số của bài hát hiện tại trong danh sách
    current_song_index = next((index for index, s in enumerate(all_songs) if s.song_url == song_url), -1)

    if current_song_index == -1:
        raise HTTPException(status_code=404, detail="Song not found in the list")

    # Tìm bài hát tiếp theo trong danh sách (nếu bài hát cuối, quay lại bài đầu tiên)
    next_song = all_songs[(current_song_index + 1) % len(all_songs)]  # Nếu là bài hát cuối cùng, quay lại bài đầu tiên

    # Trả về song_url của bài hát tiếp theo
    return {"song_url": next_song.song_url}


@router.post("/playbeforewed")
async def get_next_song_by_url(request: ThumbnailRequest, db: Session = Depends(get_db)):
    song_url = request.thumbnail_url  # Lấy song_url từ body (trong yêu cầu của bạn)

    # Tìm bài hát có song_url trùng với tham số truyền vào
    song = db.query(Song).filter(Song.song_url == song_url).first()

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Lấy tất cả bài hát trong cơ sở dữ liệu (có thể sắp xếp theo ID hoặc theo thời gian phát hành)
    all_songs = db.query(Song).order_by(Song.id).all()  # Sắp xếp theo ID tăng dần

    # Tìm chỉ số của bài hát hiện tại trong danh sách
    current_song_index = next((index for index, s in enumerate(all_songs) if s.song_url == song_url), -1)

    if current_song_index == -1:
        raise HTTPException(status_code=404, detail="Song not found in the list")

    # Tìm bài hát tiếp theo trong danh sách (nếu bài hát cuối, quay lại bài đầu tiên)
    next_song = all_songs[(current_song_index + 1) % len(all_songs)]  # Nếu là bài hát cuối cùng, quay lại bài đầu tiên

    # Trả về song_url của bài hát tiếp theo
    return {"song_url": next_song.song_url}

@router.get("/top-artists")
def get_top_followed_artists(db: Session = Depends(get_db)):
   """Lấy 3 nghệ sĩ có nhiều người follow nhất"""
   results = (db.query(
       Artist,
       func.count(Follower.id).label('follower_count')
   )
   .join(Follower, Artist.id == Follower.artist_id)
   .group_by(Artist.id)
   .order_by(func.count(Follower.id).desc())
   .limit(3)  # Giới hạn chỉ lấy 3 nghệ sĩ
   .all())
  
   return [{
       "artist_id": artist.id,
       "artist_name": artist.normalized_name,
       "image_url": artist.image_url,
       "follower_count": count,
       "rank": index + 1  # Thêm thứ hạng cho từng nghệ sĩ
   } for index, (artist, count) in enumerate(results)]

class CommentRequest(BaseModel):
    content: str
    user_id: str

#CMT VÀO BÀI HÁT 
@router.post("/song/{song_id}/comment")
def post_comment(song_id: str, request: CommentRequest, db: Session = Depends(get_db)):
    """
    API để thêm bình luận vào bài hát.
    """
    if not request.content:
        raise HTTPException(status_code=400, detail="Nội dung bình luận không được để trống.")

    comment = Comment(
        id=str(uuid.uuid4()),
        song_id=song_id,
        user_id=request.user_id,
        content=request.content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {"message": "Bình luận đã được thêm.", "comment": comment.as_dict()}



class EditCommentRequest1(BaseModel):
    content: str


#CHỈNH SỬA BÌNH LUẬN VÀO BÀI HÁT(KHÔNG ẢNH HƯỞNG ĐẾN REALTIME)
@router.post("/song/{song_id}/chinhsuacmt/{comment_id}")
def edit_comment(song_id: str, comment_id: str, request: EditCommentRequest1, db: Session = Depends(get_db),user_info: dict = Depends(auth_middleware)):
    """
    API để chỉnh sửa bình luận của người dùng trên bài hát.
    """
    user_id = user_info.get("uid")  # Lấy uid từ middleware
    # Kiểm tra xem bình luận có tồn tại không
    comment = db.query(Comment).filter(Comment.id == comment_id, Comment.song_id == song_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Bình luận không tồn tại.")

    # Kiểm tra xem người dùng có quyền chỉnh sửa bình luận này không
    if comment.user_id != user_id:
        raise HTTPException(status_code=404, detail="Bạn chỉ có thể chỉnh sửa bình luận của chính mình.")

    # Cập nhật nội dung bình luận
    comment.content = request.content
    db.commit()
    db.refresh(comment)

    return {"message": "Bình luận đã được chỉnh sửa.", "comment": comment.as_dict()}

#XÓA CMT VÀO BÀI HÁT
@router.post("/song/{song_id}/xoacmt/{comment_id}")
def delete_comment(song_id: str, comment_id: str, db: Session = Depends(get_db), user_info: dict = Depends(auth_middleware)):
    """
    API để xóa bình luận của người dùng trên bài hát.
    """
    user_id = user_info.get("uid")  # Lấy uid từ middleware
    
    # Kiểm tra xem bình luận có tồn tại không
    comment = db.query(Comment).filter(Comment.id == comment_id, Comment.song_id == song_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Bình luận không tồn tại.")
    
    # Kiểm tra xem người dùng có quyền xóa bình luận này không
    if comment.user_id != user_id:
        raise HTTPException(status_code=403, detail="Bạn chỉ có thể xóa bình luận của chính mình.")
    
    # Xóa bình luận
    db.delete(comment)
    db.commit()

    return {"message": "Bình luận đã được xóa."}




#LẤY TẤT CẢ BÌNH LUẬN CỦA BÀI HAT ĐÓ
@router.get("/song/{song_id}/comments")
def get_comments(song_id: str, db: Session = Depends(get_db)):
    """
    API để lấy tất cả bình luận của một bài hát, bao gồm cả thông tin người dùng.
    """
    comments = db.query(Comment).filter(Comment.song_id == song_id).all()
    
    # Lấy thông tin người dùng tương ứng với mỗi bình luận
    result = []
    for comment in comments:
        user = db.query(User).filter(User.id == comment.user_id).first()  # Lấy user theo user_id trong comment
        if user:
            # Thêm thông tin user_name vào bình luận
            comment_data = comment.as_dict()
            comment_data['user_name'] = user.name  # Giả sử bạn có trường `username` trong bảng User
            result.append(comment_data)
    
    return {"comments": result}






# @router.get("/song/{song_id}/comments")
# def get_comments(song_id: str, db: Session = Depends(get_db)):
#     """
#     API để lấy tất cả bình luận của một bài hát.
#     """
#     comments = db.query(Comment).filter(Comment.song_id == song_id).all()
#     return {"comments": [comment.as_dict() for comment in comments]}



# class GroupMessageCreate(BaseModel):
#     group_id: int
#     sender_id: int
#     content: str

#     class Config:
#         orm_mode = True

# class GroupMessageCreate(BaseModel):
#     group_id: int
#     content: 


# #CẤM HẾT TẤT CẢ
# @router.post("/groups/{group_id}/block-all-members")
# def block_all_members(
#     group_id: int,
#     user_info: dict = Depends(auth_middleware),
#     db: Session = Depends(get_db)
# ):
#     """
#     API để creator_id block tất cả thành viên trong nhóm.
#     """
#     user_id = user_info.get("uid")
#     if not user_id:
#         raise HTTPException(status_code=401, detail="Người dùng không xác thực.")

#     # Kiểm tra nhóm
#     group = db.query(Group).filter(Group.id == group_id).first()
#     if not group:
#         raise HTTPException(status_code=404, detail="Nhóm không tồn tại.")

#     # Kiểm tra nếu user là creator của nhóm
#     if group.creator_id != user_id:
#         raise HTTPException(status_code=403, detail="Bạn không có quyền thực hiện hành động này.")

#     # Lấy danh sách các thành viên trong nhóm (trừ creator)
#     members = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id != user_id).all()
#     if not members:
#         return {"message": "Không có thành viên nào khác trong nhóm để block."}

#     # Thêm các thành viên này vào bảng BlockedGroupMember
#     for member in members:
#         if not db.query(BlockedGroupMember).filter(BlockedGroupMember.group_id == group_id, BlockedGroupMember.user_id == member.user_id).first():
#             blocked_member = BlockedGroupMember(group_id=group_id, user_id=member.user_id)
#             db.add(blocked_member)

#     db.commit()

#     return {"message": "Tất cả thành viên đã bị block."}




# #BỎ CẤM HẾT TẤT CẢ
# @router.post("/groups/{group_id}/unblock-all-members")
# def unblock_all_members(
#     group_id: int,
#     user_info: dict = Depends(auth_middleware),
#     db: Session = Depends(get_db)
# ):
#     """
#     API để creator_id gỡ block tất cả thành viên trong nhóm.
#     """
#     user_id = user_info.get("uid")
#     if not user_id:
#         raise HTTPException(status_code=401, detail="Người dùng không xác thực.")

#     # Kiểm tra nhóm
#     group = db.query(Group).filter(Group.id == group_id).first()
#     if not group:
#         raise HTTPException(status_code=404, detail="Nhóm không tồn tại.")

#     # Kiểm tra nếu user là creator của nhóm
#     if group.creator_id != user_id:
#         raise HTTPException(status_code=403, detail="Bạn không có quyền thực hiện hành động này.")

#     # Xóa tất cả các thành viên bị block
#     db.query(BlockedGroupMember).filter(BlockedGroupMember.group_id == group_id).delete()
#     db.commit()

#     return {"message": "Tất cả thành viên đã được gỡ block."}


class MessageCreate(BaseModel):
    receiver_id: str
    content: str

# API gửi tin nhắn giữa các user, với kiểm tra chặn.
@router.post("/message/send")
def send_message(message: MessageCreate, user_info: dict = Depends(auth_middleware), db: Session = Depends(get_db)):
    """
    API gửi tin nhắn giữa các user, với kiểm tra chặn.
    """
    sender_id = user_info.get('uid')  # Lấy sender_id từ thông tin người dùng từ middleware

    # Kiểm tra nếu sender_id không tồn tại trong user_info
    if not sender_id:
        raise HTTPException(status_code=401, detail="Người dùng chưa đăng nhập")

    # Kiểm tra nội dung tin nhắn không được để trống
    if not message.content.strip():
        raise HTTPException(status_code=400, detail="Nội dung tin nhắn không được để trống.")

    # Kiểm tra xem người gửi hoặc người nhận có bị chặn hay không
    block_check = db.query(Block).filter(
        ((Block.blocker_id == sender_id) & (Block.blocked_id == message.receiver_id)) |
        ((Block.blocker_id == message.receiver_id) & (Block.blocked_id == sender_id))
    ).first()
    
    if block_check:
        return {
            "message": "Tin nhắn không được gửi vì bạn đã bị chặn!"
        }

    # Tạo tin nhắn mới
    new_message = GroupMessage()
    new_message.group_id = None  # Chưa sử dụng nhóm
    new_message.sender_id = sender_id  # Đặt sender_id từ user_info
    new_message.receiver_id = message.receiver_id
    new_message.content = message.content

    # Lưu tin nhắn vào database
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    # Trả về kết quả
    return {
        "message": "Tin nhắn đã được gửi.",
        "sent_message": new_message.as_dict()  # Chuyển đối tượng thành dict
    }


#XÓA TIN NHẮN
@router.post("/messagexoa/{message_id}")
def delete_message(message_id: int, db: Session = Depends(get_db), user_info: dict = Depends(auth_middleware)):
    """
    API để xóa tin nhắn giữa hai người dùng.
    """
    user_id = user_info.get("uid")  # Lấy ID người dùng từ middleware

    # Tìm tin nhắn
    message = db.query(GroupMessage).filter(GroupMessage.id == message_id).first()
    if not message:
        return {"status": "not_found", "message": "Tin nhắn không tồn tại."}

    # Kiểm tra quyền xóa tin nhắn
    if message.sender_id != user_id and message.receiver_id != user_id:
        return {"status": "forbidden", "message": "Bạn không có quyền xóa tin nhắn này."}

    # Xóa tin nhắn
    db.delete(message)
    db.commit()

    return {"status": "success", "message": "Tin nhắn đã được xóa thành công."}




class EditMessageRequest(BaseModel):
    new_content: str
#CHỈNH SỬA TIN NHẮN
@router.post("/messagechinhsua/{message_id}")
def edit_message(
    message_id: int, 
    request: EditMessageRequest, 
    db: Session = Depends(get_db), 
    user_info: dict = Depends(auth_middleware)
):
    """
    API để chỉnh sửa tin nhắn giữa hai người dùng.
    """
    user_id = user_info.get("uid")  # Lấy ID người dùng từ middleware

    # Tìm tin nhắn
    message = db.query(GroupMessage).filter(GroupMessage.id == message_id).first()
    if not message:
        return {"status": "not_found", "message": "Tin nhắn không tồn tại."}

    # Kiểm tra quyền chỉnh sửa tin nhắn
    if message.sender_id != user_id:
        return {"status": "forbidden", "message": "Bạn chỉ có thể chỉnh sửa tin nhắn của chính mình."}

    # Cập nhật nội dung tin nhắn
    if not request.new_content.strip():
        return {"status": "invalid_request", "message": "Nội dung tin nhắn không được để trống."}

    message.content = request.new_content
    db.commit()
    db.refresh(message)

    return {"status": "success", "message": "Tin nhắn đã được chỉnh sửa.", "updated_message": message.as_dict()}


class ConversationRequest(BaseModel):
    user2_id: str

@router.post("/message/conversation")
def get_conversation(
    request: ConversationRequest,
    user_info: dict = Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    """
    API để lấy toàn bộ tin nhắn giữa user hiện tại và user khác.
    """
    # Lấy user1_id từ middleware
    user1_id = user_info.get("uid")
    if not user1_id:
        raise HTTPException(status_code=401, detail="Người dùng không xác thực.")

    # Truy vấn tin nhắn giữa user1_id và user2_id
    messages = db.query(GroupMessage).filter(
        ((GroupMessage.sender_id == user1_id) & (GroupMessage.receiver_id == request.user2_id)) |
        ((GroupMessage.sender_id == request.user2_id) & (GroupMessage.receiver_id == user1_id))
    ).order_by(GroupMessage.sent_at).all()

    # Trả về tin nhắn dưới dạng JSON
    return {"conversation": [message.as_dict() for message in messages]}



class SendMessageRequest(BaseModel):
    group_id: int
    content: str
#GỬI TIN NHẮN VÀO GROUP
@router.post("/groups/messages")
def send_message(
    request: SendMessageRequest, 
    db: Session = Depends(get_db), 
    user_info: dict = Depends(auth_middleware)
):
    user_id = user_info.get("uid")  # Lấy UID từ middleware

    # Kiểm tra nếu nhóm tồn tại
    group = db.query(Group).filter(Group.id == request.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Kiểm tra nếu người gửi là thành viên của nhóm và không bị cấm
    member = db.query(GroupMember).filter(
        GroupMember.group_id == request.group_id,
        GroupMember.user_id == user_id,
        GroupMember.is_banned == False
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="User is not an active member of the group or is banned")
    
    # Tạo tin nhắn mới
    new_message = GroupMessage(
        group_id=request.group_id,
        sender_id=user_id,
        content=request.content,
        # receiver_id= "null",
        receiver_id=None, 
        sent_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    # Trả về kết quả
    return {
        "message": "Message sent successfully",
        "message_id": new_message.id,
        "group_id": new_message.group_id,
        "sender_id": new_message.sender_id,
        "content": new_message.content,
        "sent_at": new_message.sent_at,
    }





#LẤY NHỮNG NHÓM CÓ USER LÀ MEMBER
@router.post("/user/groups/membership")
def get_user_groups(user_info: dict = Depends(auth_middleware), db: Session = Depends(get_db)):
    """
    API để lấy danh sách các nhóm mà người dùng hiện tại là thành viên.
    """
    user_id = user_info.get("uid")
    if not user_id:
        raise HTTPException(status_code=401, detail="Người dùng không xác thực.")

    # Join bảng groups để lấy thông tin chi tiết của nhóm
    user_groups = (
        db.query(Group)
        .join(GroupMember)
        .filter(GroupMember.user_id == user_id)
        .all()
    )

    # Trả về thông tin chi tiết của các nhóm
    groups_data = [{
        "id": group.id,
        "name": group.name,
        "thumbnail_url": group.thumbnail_url,
        "creator_id": group.creator_id
    } for group in user_groups]

    return {
        "user_id": user_id,
        "groups": groups_data
    }




#LẤY NHỮNG NGƯỜI DÙNG MÀ USER NHẮN TIN
@router.post("/user/messages/receivers")
def get_receivers_from_sender(
    user_info: dict = Depends(auth_middleware), 
    db: Session = Depends(get_db)
):
    """
    API để lấy danh sách receiver_id mà sender_id đã nhắn tin.
    """
    # Lấy sender_id từ middleware
    sender_id = user_info.get("uid")
    if not sender_id:
        raise HTTPException(status_code=401, detail="Người dùng không xác thực.")

    # Truy vấn danh sách receiver_id mà sender_id đã gửi tin nhắn
    receivers = (
        db.query(GroupMessage.receiver_id)
        .filter(GroupMessage.sender_id == sender_id, GroupMessage.receiver_id != None)
        .distinct()
        .all()
    )

    # Chuyển kết quả từ list các tuple sang list đơn
    receiver_ids = [receiver[0] for receiver in receivers]

    return {
        "sender_id": sender_id,
        "receiver_ids": receiver_ids
    }




@router.post("/user/messages/receivers1")
def get_receivers_from_sender(
    user_info: dict = Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    """
    API để lấy danh sách receiver_id và receiver_name mà sender_id đã nhắn tin.
    """
    # Lấy sender_id từ middleware
    sender_id = user_info.get("uid")
    if not sender_id:
        raise HTTPException(status_code=401, detail="Người dùng không xác thực.")

    # Truy vấn thông tin receiver_id và receiver_name
    receivers = (
        db.query(GroupMessage.receiver_id, User.name.label("receiver_name"))
        .join(User, GroupMessage.receiver_id == User.id)  # Join với bảng User để lấy tên
        .filter(GroupMessage.sender_id == sender_id, GroupMessage.receiver_id != None)
        .distinct()
        .all()
    )

    # Chuyển kết quả sang danh sách dictionary
    receiver_data = [
        {"receiver_id": receiver.receiver_id, "receiver_name": receiver.receiver_name}
        for receiver in receivers
    ]

    return {
        "sender_id": sender_id,
        "receivers": receiver_data
    }

class CreateGroupRequest(BaseModel):
    group_name: str
    thumbnail_url: str

# TẠO NHÓM (AI TẠO LƯU LÀ TRƯỞNG NHÓM)
@router.post("/groups")
async def create_group(
    group_name: str = Form(...),
    thumbnail: UploadFile = File(...),
    user_info: dict = Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    """
    API tạo nhóm với upload ảnh. Người tạo được lấy từ thông tin xác thực của middleware.
    """
    # Lấy creator_id từ thông tin user
    creator_id = user_info.get("uid")
    if not creator_id:
        raise HTTPException(status_code=401, detail="Người dùng không xác thực.")

    # Kiểm tra user (người tạo group) có tồn tại không
    creator = db.query(User).filter(User.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    # Upload ảnh lên Cloudinary
    try:
        result = cloudinary.uploader.upload(
            thumbnail.file,
            folder="groups",  # Lưu trong thư mục groups
            resource_type="auto"
        )
        thumbnail_url = result.get("secure_url")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể upload ảnh: {str(e)}")

    # Tạo group mới với URL ảnh từ Cloudinary
    new_group = Group(
        name=group_name,
        creator_id=creator_id,
        thumbnail_url=thumbnail_url
    )
    db.add(new_group)
    db.commit()
    db.refresh(new_group)

    return {
        "message": "Group created successfully",
        "group_id": new_group.id,
        "group_name": new_group.name,
        "creator_id": new_group.creator_id,
        "thumbnail_url": thumbnail_url,
    }


class AddMemberRequest(BaseModel):
    group_id: str
    user_id: str

#THÊM THÀNH VIÊN VÀO NHÓM VÀ CÓ NGƯỜI TẠO NHÓM MỚI CÓ THỂ THÊM VÀO NHÓM
@router.post("/groups/add-member")
def add_member_to_group(
    request: AddMemberRequest,  # Lấy thông tin group_id và user_id
    current_user: dict = Depends(auth_middleware),  # Lấy thông tin người dùng từ JWT
    db: Session = Depends(get_db),  # Kết nối đến database
):
    # Xác định user_id từ JWT
    user_id = current_user.get("uid")

    # Kiểm tra nhóm có tồn tại không
    group = db.query(Group).filter(Group.id == request.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Nhóm không tồn tại.")

    # Xác minh người dùng hiện tại là người tạo nhóm
    if group.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Chỉ người tạo nhóm mới có quyền thêm thành viên.")

    # Kiểm tra nếu người dùng đã là thành viên của nhóm
    existing_member = db.query(GroupMember).filter(
        GroupMember.group_id == request.group_id,
        GroupMember.user_id == request.user_id
    ).first()
    if existing_member:
        raise HTTPException(status_code=400, detail="Người dùng đã là thành viên của nhóm.")

    # Thêm thành viên mới vào nhóm, mặc định `is_banned` là `False`
    new_member = GroupMember(
        group_id=request.group_id,
        user_id=request.user_id,
        is_banned=False  # Mặc định thành viên không bị block
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    return {"message": "Thành viên đã được thêm vào nhóm thành công.", "member_id": new_member.id}




class GroupActionRequest(BaseModel):
    group_id: int

#CẤM TẤT CẢ TRONG NHÓM
@router.post("/groups/ban-all")
def ban_all_except_creator(
    request: GroupActionRequest,  # Nhận group_id từ body
    current_user: dict = Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    # Lấy user_id của người dùng hiện tại từ JWT
    user_id = current_user.get("uid")

    # Tìm nhóm theo ID
    group = db.query(Group).filter(Group.id == request.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Nhóm không tồn tại.")

    # Kiểm tra người dùng hiện tại có phải là creator của nhóm không
    if group.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Chỉ người tạo nhóm mới có quyền thực hiện thao tác này.")

    # Cập nhật tất cả thành viên thành bị cấm, trừ creator
    db.query(GroupMember).filter(
        GroupMember.group_id == request.group_id,
        GroupMember.user_id != user_id
    ).update({"is_banned": True}, synchronize_session="fetch")
    db.commit()

    return {"message": "Tất cả thành viên trừ người tạo nhóm đã bị cấm."}



class GroupActionRequest(BaseModel):
    group_id: int
#GỠ CẤM CHO TẤT CẢ
@router.post("/groups/unban-all")
def unban_all_members(
    request: GroupActionRequest,  # Nhận group_id từ body
    current_user: dict = Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    # Lấy user_id của người dùng hiện tại từ JWT
    user_id = current_user.get("uid")

    # Tìm nhóm theo ID
    group = db.query(Group).filter(Group.id == request.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Nhóm không tồn tại.")

    # Kiểm tra người dùng hiện tại có phải là creator của nhóm không
    if group.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Chỉ người tạo nhóm mới có quyền thực hiện thao tác này.")

    # Cập nhật tất cả thành viên thành không bị cấm
    db.query(GroupMember).filter(GroupMember.group_id == request.group_id).update({"is_banned": False}, synchronize_session="fetch")
    db.commit()

    return {"message": "Tất cả thành viên đã được gỡ cấm."}



class SendMessageRequest(BaseModel):
    group_id: int
    content: str
#GỬI TIN NHẮN VÀO GROUP
@router.post("/groups/messages")
def send_message(
    request: SendMessageRequest, 
    db: Session = Depends(get_db), 
    user_info: dict = Depends(auth_middleware)
):
    user_id = user_info.get("uid")  # Lấy UID từ middleware

    # Kiểm tra nếu nhóm tồn tại
    group = db.query(Group).filter(Group.id == request.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Kiểm tra nếu người gửi là thành viên của nhóm và không bị cấm
    member = db.query(GroupMember).filter(
        GroupMember.group_id == request.group_id,
        GroupMember.user_id == user_id,
        GroupMember.is_banned == False
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="User is not an active member of the group or is banned")
    
    # Tạo tin nhắn mới
    new_message = GroupMessage(
        group_id=request.group_id,
        sender_id=user_id,
        content=request.content,
        # receiver_id= "null",
        receiver_id=None, 
        sent_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    # Trả về kết quả
    return {
        "message": "Message sent successfully",
        "message_id": new_message.id,
        "group_id": new_message.group_id,
        "sender_id": new_message.sender_id,
        "content": new_message.content,
        "sent_at": new_message.sent_at,
    }

class GroupMessageResponse(BaseModel):
    id: int
    group_id: int
    sender_id: int
    content: str
    sent_at: datetime

    class Config:
        orm_mode = True
#LẤY TẤT CẢ TIN NHẮN TRONG NHÓM 
@router.get("/groups/{group_id}/messages")
def get_group_messages(
    group_id: int, 
    db: Session = Depends(get_db), 
    ds: dict = Depends(auth_middleware)  # Đảm bảo người dùng được xác thực
):  
    current_user = ds.get('uid') if isinstance(ds, dict) else ds
    current_name=GroupMessage.sender_id.name  
    try:
       
        # Kiểm tra xem nhóm có tồn tại không
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Lấy tất cả tin nhắn của nhóm
        messages = db.query(GroupMessage).filter(GroupMessage.group_id == group_id).all()

        # Thêm thông tin phân biệt giữa tin nhắn của người dùng hiện tại và người khác
        for message in messages:
            message.is_user_message = message.sender_id == current_user
            # message.user_name=message.sender_id =current_name# Gắn flag cho tin nhắn của người dùng hiện tại

        return messages
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#NGƯỜI DÙNG RỜI KHỎI NHÓM
@router.post("/groups/{group_id}/members")
def leave_group(group_id: int, user_id: dict = Depends(auth_middleware), db: Session = Depends(get_db)):
    # Trích xuất user_id từ dict nếu cần
    user_id = user_id.get('uid') if isinstance(user_id, dict) else user_id

    # Kiểm tra nếu nhóm tồn tại
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Kiểm tra nếu người dùng là thành viên của nhóm
    member = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id).first()
    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of the group")
    
    # Xóa người dùng khỏi nhóm
    db.delete(member)
    db.commit()
    
    # Trả về kết quả
    return {"message": "User has successfully left the group"}


#DÙNG ĐỂ XÓA TIN NHẮN
@router.post("/groups/{group_id}/xoatn/{message_id}")
def delete_message(group_id: int, message_id: int, user_info: dict = Depends(auth_middleware), db: Session = Depends(get_db)):
    user_id = user_info.get("uid")  # Lấy uid từ middleware
    
    # Kiểm tra nếu nhóm tồn tại
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Kiểm tra nếu người dùng là thành viên của nhóm
    member = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="User is not a member of the group")
    
    # Lấy tin nhắn cần xóa
    message = db.query(GroupMessage).filter(GroupMessage.id == message_id, GroupMessage.group_id == group_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Kiểm tra xem người yêu cầu có phải là người gửi tin nhắn không
    if message.sender_id != user_id:
        raise HTTPException(status_code=404, detail="You can only delete your own messages")
    
    # Xóa tin nhắn
    db.delete(message)
    db.commit()
    
    return {"message": "Message successfully deleted"}


class EditMessageRequest(BaseModel):
    new_content: str


#CHỈNH SỬA TIN NHẮN CỦA NHÓM CHỈ NGƯỜI TRONG NHÓM ĐƯỢC SỬA CHÍNH MÌNH
@router.post("/messagechinhsua/{message_id}")
def edit_message(
    message_id: int, 
    request: EditMessageRequest, 
    db: Session = Depends(get_db), 
    user_info: dict = Depends(auth_middleware)
):
    """
    API để chỉnh sửa tin nhắn giữa hai người dùng.
    """
    user_id = user_info.get("uid")  # Lấy ID người dùng từ middleware

    # Tìm tin nhắn
    message = db.query(GroupMessage).filter(GroupMessage.id == message_id).first()
    if not message:
        return {"status": "not_found", "message": "Tin nhắn không tồn tại."}

    # Kiểm tra quyền chỉnh sửa tin nhắn
    if message.sender_id != user_id:
        return {"status": "forbidden", "message": "Bạn chỉ có thể chỉnh sửa tin nhắn của chính mình."}

    # Cập nhật nội dung tin nhắn
    if not request.new_content.strip():
        return {"status": "invalid_request", "message": "Nội dung tin nhắn không được để trống."}

    message.content = request.new_content
    db.commit()
    db.refresh(message)

    return {"status": "success", "message": "Tin nhắn đã được chỉnh sửa.", "updated_message": message.as_dict()}

#BLOCK GIỮA 2 NGƯỜI DÙNG
@router.post("/users/{user_id}/block/{blocked_user_id}")
def block_user(user_id: str, blocked_user_id: str, db: Session = Depends(get_db)):
    """
    API để chặn người dùng.
    """
    # Kiểm tra nếu người dùng có tồn tại
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại.")

    # Kiểm tra nếu người bị chặn có tồn tại
    blocked_user = db.query(User).filter(User.id == blocked_user_id).first()
    if not blocked_user:
        raise HTTPException(status_code=404, detail="Người bị chặn không tồn tại.")

    # Kiểm tra nếu người dùng đã chặn người này rồi
    existing_block = db.query(Block).filter(Block.blocker_id == user_id, Block.blocked_id == blocked_user_id).first()
    if existing_block:
        raise HTTPException(status_code=400, detail="Người dùng đã chặn người này rồi.")

    # Tạo mối quan hệ chặn
    block = Block(blocker_id=user_id, blocked_id=blocked_user_id)
    db.add(block)
    db.commit()

    return {"message": "Đã chặn người dùng thành công."}

class BlockRequest(BaseModel):
    blocker_id: str
    blocked_id: str


#GỠ BLOCK
@router.post("/unblock")
def unblock_user(block_request: BlockRequest, db: Session = Depends(get_db)):
    """
    API gỡ chặn giữa hai người dùng.
    """
    # Tìm dòng chặn trong bảng Block
    block_entry = db.query(Block).filter(
        Block.blocker_id == block_request.blocker_id,
        Block.blocked_id == block_request.blocked_id
    ).first()

    if not block_entry:
        return {
            "status": "not_found",
            "message": "Người dùng này chưa bị chặn."
        }

    # Xóa dòng chặn
    db.delete(block_entry)
    db.commit()

    return {
        "status": "success",
        "message": "Gỡ chặn thành công."
    }


class ReactionRequest(BaseModel):
    emoji: str
    message_id:int  # Cảm xúc mà người dùng chọn
    
#THẢ CẢM XÚC
@router.post("/messages/react")
def react_to_message(
     request: ReactionRequest, db: Session = Depends(get_db), user_info: str = Depends(auth_middleware)
):  
    user_id = user_info.get("uid")
    
    # Kiểm tra xem tin nhắn có tồn tại không
    message = db.query(GroupMessage).filter(GroupMessage.id == request.message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Kiểm tra nếu người gửi là thành viên của nhóm
    # group_id = message.group_id
    # member = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id).first()
    # if not member:
    #     raise HTTPException(status_code=403, detail="User is not a member of the group")
    
    # Kiểm tra nếu người dùng đã thả cảm xúc vào tin nhắn này rồi
    existing_reaction = db.query(MessageReaction).filter(
        MessageReaction.message_id == request.message_id, MessageReaction.user_id == user_id
    ).first()

    if existing_reaction:
        # Nếu có rồi, có thể update cảm xúc nếu muốn
        existing_reaction.emoji = request.emoji
    else:
        # Nếu chưa có, thêm mới một cảm xúc
        new_reaction = MessageReaction(
            message_id=request.message_id,
            user_id=user_id,
            emoji=request.emoji
        )
        db.add(new_reaction)
    
    db.commit()

    # Trả về kết quả
    return {
        "message": "Reaction added successfully",
        "message_id": request.message_id,  # Dùng message_id từ tham số URL
        "emoji": request.emoji,
    }













class ReactionRequest11(BaseModel):
    emoji: str
    message_id: int  # ID của tin nhắn
    recipient_id: str  # ID của người nhận (người thứ 2)

# Thêm phương thức để thả cảm xúc tin nhắn
@router.post("/messages/react3")
def react_to_message(
    request: ReactionRequest11, db: Session = Depends(get_db), user_info: str = Depends(auth_middleware)
):  
    user_id = user_info.get("uid")
    
    # Kiểm tra xem tin nhắn có tồn tại không
    message = db.query(GroupMessage).filter(GroupMessage.id == request.message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Kiểm tra nếu người dùng đã thả cảm xúc vào tin nhắn này rồi
    existing_reaction = db.query(MessageReaction).filter(
        MessageReaction.message_id == request.message_id, MessageReaction.user_id == user_id
    ).first()

    if existing_reaction:
        # Nếu có rồi, có thể update cảm xúc nếu muốn
        existing_reaction.emoji = request.emoji
    else:
        # Nếu chưa có, thêm mới một cảm xúc
        new_reaction = MessageReaction(
            message_id=request.message_id,
            user_id=user_id,
            emoji=request.emoji,
            group_id=message.group_id  # Lưu group_id từ message nếu cần thiết
        )
        db.add(new_reaction)
    
    db.commit()

    # Trả về kết quả
    return {
        "message": "Reaction added successfully",
        "message_id": request.message_id,  # Dùng message_id từ tham số URL
        "emoji": request.emoji,
    }




#2 người nhán tin với nhau
@router.post("/messages/react2")
def react_to_message(
    request: ReactionRequest11, 
    db: Session = Depends(get_db), 
    user_info: dict = Depends(auth_middleware)
):  
    user_id = user_info.get("uid")  # Lấy ID người dùng từ token thông qua middleware
    
    # Kiểm tra tin nhắn có tồn tại hay không
    message = db.query(GroupMessage).filter(
        GroupMessage.id == request.message_id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # # Kiểm tra người gửi và người nhận của tin nhắn
    # if not ((message.sender_id == user_id and message.recipient_id == request.recipient_id) or 
    #         (message.sender_id == request.recipient_id and message.recipient_id == user_id)):
    #     raise HTTPException(status_code=403, detail="You are not allowed to react to this message")
    
    # Kiểm tra xem người dùng đã thả cảm xúc vào tin nhắn này chưa
    existing_reaction = db.query(MessageReaction).filter(
        MessageReaction.message_id == request.message_id, 
        MessageReaction.user_id == user_id
    ).first()

    if existing_reaction:
        # Nếu đã thả cảm xúc, cập nhật cảm xúc
        existing_reaction.emoji = request.emoji
    else:
        # Nếu chưa thả cảm xúc, tạo mới
        new_reaction = MessageReaction(
            message_id=request.message_id,
            user_id=user_id,
            emoji=request.emoji
        )
        db.add(new_reaction)
    
    db.commit()

    # Trả về kết quả thành công
    return {
        "message": "Reaction added successfully",
        "message_id": request.message_id,
        "emoji": request.emoji,
        "user_id": user_id,
        "recipient_id": request.recipient_id,
    }



class ReactionRequest1(BaseModel):
 
    message_id:int 
#LẤY TẤT CẢ BIỂU CẢM
@router.get("/messages/reactions")
def get_reactions(On: ReactionRequest1, db: Session = Depends(get_db)):
    # user_info = user_id.get("uid")
    # Lấy thông tin cảm xúc của một tin nhắn
    message = db.query(GroupMessage).filter(GroupMessage.id == On.message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    reactions = db.query(MessageReaction).filter(MessageReaction.message_id == On.message_id).all()

    # Trả về danh sách cảm xúc của tin nhắn
    return {"message_id": On.message_id, "reactions": [{"user_id": reaction.user_id, "emoji": reaction.emoji} for reaction in reactions]}

#TÌM KIẾM NGƯỜI DÙNG
@router.get('/users/search')
async def search_users(
    query: str="",
    db: Session = Depends(get_db),
    user_info: dict = Depends(auth_middleware)
):
    try:
        current_user_id = user_info.get('uid')
        
        users = db.query(User).filter(
            User.name.ilike(f"%{query}%"),
            User.id != current_user_id,
            User.is_active == True
        ).all()
        
        return [
            {
                'id': str(user.id),
                'name': user.name,
                'token': '',
                'favorites': [],
                'imageUrl': '',  # Có thể thêm avatar URL nếu có
            }
            for user in users
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching users: {str(e)}"
        )
    









#TÌM KIẾM NGƯỜI DÙNG
@router.get('/artist/search')
async def search_users(
    query: str="",
    db: Session = Depends(get_db),
    user_info: dict = Depends(auth_middleware)
):
    try:
        current_user_id = user_info.get('uid')
        
        users = db.query(User).filter(
            User.name.ilike(f"%{query}%"),
            User.id != current_user_id,
            User.is_active == True,
            User.role=="artist"
        ).all()
        
        return [
            {
                'id': str(user.id),
                'name': user.name,
                'token': '',
                'favorites': [],
                'imageUrl': '',  # Có thể thêm avatar URL nếu có
            }
            for user in users
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching users: {str(e)}"
        )
    
    

class CreateDirectChatRequest(BaseModel):
    receiver_id: str

#Tạo cuộc trò chuyện trực tiếp
@router.post("/messages/create-direct-chat")
def create_direct_chat(
    request: CreateDirectChatRequest,
    db: Session = Depends(get_db),
    user_info: dict = Depends(auth_middleware)
):
    """
    API để tạo hoặc lấy cuộc trò chuyện trực tiếp giữa hai người dùng.
    """
    sender_id = user_info.get("uid")
    
    # Kiểm tra xem người nhận có tồn tại không
    receiver = db.query(User).filter(User.id == request.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Người nhận không tồn tại")

    # Kiểm tra block
    block_check = db.query(Block).filter(
        ((Block.blocker_id == sender_id) & (Block.blocked_id == request.receiver_id)) |
        ((Block.blocker_id == request.receiver_id) & (Block.blocked_id == sender_id))
    ).first()
    
    if block_check:
        raise HTTPException(status_code=403, detail="Không thể tạo cuộc trò chuyện do đã bị chặn")

    # Trả về thông tin cơ bản để bắt đầu cuộc trò chuyện
    return {
        "sender_id": sender_id,
        "receiver_id": request.receiver_id,
        "receiver_name": receiver.name,
        "receiver_image": receiver.imageUrl if hasattr(receiver, 'imageUrl') else ""
    }

# Lấy danh sách cuộc trò chuyện trực tiếp
@router.get("/messages/direct-chats")
def get_direct_chats(
    db: Session = Depends(get_db),
    user_info: dict = Depends(auth_middleware)
):
    """
    API để lấy danh sách các cuộc trò chuyện trực tiếp của người dùng
    """
    user_id = user_info.get("uid")
    
    # Lấy các cuộc trò chuyện có tin nhắn gần nhất
    chats = db.query(
        GroupMessage,
        func.max(GroupMessage.sent_at).label('last_message_time')
    ).filter(
        or_(
            GroupMessage.sender_id == user_id,
            GroupMessage.receiver_id == user_id
        ),
        GroupMessage.group_id.is_(None)  # Chỉ lấy tin nhắn trực tiếp
    ).group_by(
        case(
            [
                (GroupMessage.sender_id == user_id, GroupMessage.receiver_id),
                (GroupMessage.receiver_id == user_id, GroupMessage.sender_id)
            ]
        )
    ).order_by(desc('last_message_time')).all()

    result = []
    for chat in chats:
        other_user_id = chat.receiver_id if chat.sender_id == user_id else chat.sender_id
        other_user = db.query(User).filter(User.id == other_user_id).first()
        
        result.append({
            "other_user": {
                "id": other_user.id,
                "name": other_user.name,
                "imageUrl": other_user.imageUrl if hasattr(other_user, 'imageUrl') else ""
            },
            "last_message": chat.content,
            "last_message_time": chat.sent_at.isoformat()
        })

    return result

# Lấy danh sách nhóm chat
@router.get("/groups/my-groups")
def get_my_groups(
    db: Session = Depends(get_db),
    user_info: dict = Depends(auth_middleware)
):
    """
    API để lấy danh sách các nhóm chat của người dùng
    """
    user_id = user_info.get("uid")
    
    # Lấy các nhóm mà user là thành viên và không bị cấm
    groups = db.query(Group).join(
        GroupMember,
        and_(
            GroupMember.group_id == Group.id,
            GroupMember.user_id == user_id,
            GroupMember.is_banned == False
        )
    ).all()

    result = []
    for group in groups:
        # Lấy tin nhắn cuối cùng của nhóm
        last_message = db.query(GroupMessage).filter(
            GroupMessage.group_id == group.id
        ).order_by(desc(GroupMessage.sent_at)).first()

        result.append({
            "id": group.id,
            "name": group.name,
            "imageUrl": group.image_url if hasattr(group, 'image_url') else "",
            "last_message": last_message.content if last_message else None,
            "last_message_time": last_message.sent_at.isoformat() if last_message else None
        })

    return result



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