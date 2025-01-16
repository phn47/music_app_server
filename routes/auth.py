from typing import Optional
import uuid
import bcrypt
from fastapi import Body, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from database import get_db
from middleware.auth_middleware import auth_middleware
from models.artist import Artist
from models.user import User
from pydantic_schemas.user_create import UserCreate
from fastapi import APIRouter
from sqlalchemy.orm import Session
from pydantic_schemas.user_login import UserLogin
import jwt
from sqlalchemy.orm import joinedload
router = APIRouter()

@router.post('/list')
def list_songs(db: Session = Depends(get_db), auth_details = Depends(auth_middleware)):
    # Lọc những nghệ sĩ có is_approved = False (chưa được duyệt)
    artists = db.query(User).filter(User.is_active == True).all()
    
    return artists

@router.post('/signup', status_code=201)
def signup_user(user: UserCreate, db: Session=Depends(get_db)):
    # check if the user already exists in db
    user_db = db.query(User).filter(User.email == user.email).first()

    if user_db:
        raise HTTPException(400, 'User with the same email already exists!')
    
    hashed_pw = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt())
    user_db = User(id=str(uuid.uuid4()), email=user.email, password=hashed_pw, name=user.name)
    
    # add the user to the db
    db.add(user_db)
    db.commit()
    db.refresh(user_db)

    return user_db



class UserUpDate(BaseModel):
    name: str
    email: str


@router.post("/update")
def approve_artist(
    # song_id: str,
    request:  UserUpDate,
 # Sửa kiểu dữ liệu thành str
    db: Session = Depends(get_db),
    
    auth_details=Depends(auth_middleware),
):  
    
    song = db.query(User).filter(User.id == auth_details['uid']).first()
    # Tìm nghệ sĩ theo ID 
    # song = db.query(User).filter(User.id == song_id).first()
    
   
    
    # Cập nhật trạng thái is_approved thành True
    song.name = request.name
    song.email = request.email
    db.commit()  # Lưu thay đổi vào cơ sở dữ liệu
    db.refresh(song)  # Tải lại dữ liệu từ cơ sở dữ liệu
    
    return  song
@router.post('/login')
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    # Tìm người dùng theo email
    user_db = db.query(User).filter(User.email == user.email).first()

    if not user_db:
        raise HTTPException(400, 'User with this email does not exist!')

    # Kiểm tra mật khẩu
    is_match = bcrypt.checkpw(user.password.encode(), user_db.password)

    if not is_match:
        raise HTTPException(400, 'Incorrect password!')

    # Kiểm tra trạng thái người dùng (bị cấm và vai trò)
    if user_db.is_active == False and user_db.role == "user":
        raise HTTPException(400, 'User has been banned.')

    if user_db.is_active == False and user_db.role == "moderator":
        raise HTTPException(400, 'Moderator has been banned.')

    # Tạo token JWT
    token = jwt.encode({'id': user_db.id}, 'password_key')

    return {'token': token, 'user': user_db}


class UserUnBannedNote(BaseModel):
    email: str
    password: str




@router.post('/yeucauunban')
def login_user(user: UserUnBannedNote, db: Session = Depends(get_db)):
    # Tìm người dùng theo email
    user_db = db.query(User).filter(User.email == user.email).first()

    if not user_db:
        raise HTTPException(400, 'User with this email does not exist!')

    # Kiểm tra mật khẩu
    is_match = bcrypt.checkpw(user.password.encode(), user_db.password)

    if not is_match:
        raise HTTPException(400, 'Incorrect password!')

    # Kiểm tra trạng thái người dùng (có bị cấm hay không)
    user_f = db.query(User).filter(User.email == user.email, User.is_active == True).first()

    # if not user_f:
    #     raise HTTPException(400, 'User has been banned!')

    # Cập nhật trạng thái is_active thành None
    user_db.is_active = None
    db.commit()

    # Tạo token JWT
    token = jwt.encode({'id': user_db.id}, 'password_key')

    return {'token': token, 'user': user_db}



@router.post('/goband')
def login_user(user: UserUnBannedNote, db: Session = Depends(get_db)):
    # Tìm người dùng theo email
    user_db = db.query(User).filter(User.email == user.email).first()

    if not user_db:
        raise HTTPException(400, 'User with this email does not exist!')

    # Kiểm tra mật khẩu
    is_match = bcrypt.checkpw(user.password.encode(), user_db.password)

    if not is_match:
        raise HTTPException(400, 'Incorrect password!')

    # Kiểm tra trạng thái người dùng (có bị cấm hay không)
    user_f = db.query(User).filter(User.email == user.email, User.is_active == True).first()

    # if not user_f:
    #     raise HTTPException(400, 'User has been banned!')

    # Cập nhật trạng thái is_active thành None
    user_db.is_active = True
    db.commit()

    # Tạo token JWT
    token = jwt.encode({'id': user_db.id}, 'password_key')

    return {'token': token, 'user': user_db}



@router.post('/ban')
def login_user(user: UserUnBannedNote, db: Session = Depends(get_db)):
    # Tìm người dùng theo email
    user_db = db.query(User).filter(User.email == user.email).first()

    if not user_db:
        raise HTTPException(400, 'User with this email does not exist!')

    # Kiểm tra mật khẩu
    is_match = bcrypt.checkpw(user.password.encode(), user_db.password)

    if not is_match:
        raise HTTPException(400, 'Incorrect password!')

    # Kiểm tra trạng thái người dùng (có bị cấm hay không)
    user_f = db.query(User).filter(User.email == user.email, User.is_active == True).first()

    # if not user_f:
    #     raise HTTPException(400, 'User has been banned!')

    # Cập nhật trạng thái is_active thành None
    user_db.is_active = False
    db.commit()

    # Tạo token JWT
    token = jwt.encode({'id': user_db.id}, 'password_key')

    return {'token': token, 'user': user_db}













#--------------------------------------------------------------------------------


@router.post('/yeucauunbannv')
def login_user(user: UserUnBannedNote, db: Session = Depends(get_db)):
    # Tìm người dùng theo email
    user_db = db.query(User).filter(User.email == user.email).first()

    if not user_db:
        raise HTTPException(400, 'User with this email does not exist!')

    # Kiểm tra mật khẩu
    is_match = bcrypt.checkpw(user.password.encode(), user_db.password)

    if not is_match:
        raise HTTPException(400, 'Incorrect password!')

    # Kiểm tra trạng thái người dùng (có bị cấm hay không)
    user_f = db.query(User).filter(User.email == user.email, User.is_active == True).first()

    # if not user_f:
    #     raise HTTPException(400, 'User has been banned!')

    # Cập nhật trạng thái is_active thành None
    user_db.is_active = None
    db.commit()

    # Tạo token JWT
    token = jwt.encode({'id': user_db.id}, 'password_key')

    return {'token': token, 'user': user_db}



@router.post('/gobandnv')
def login_user(user: UserUnBannedNote, db: Session = Depends(get_db)):
    # Tìm người dùng theo email
    user_db = db.query(User).filter(User.email == user.email).first()

    if not user_db:
        raise HTTPException(400, 'User with this email does not exist!')

    # Kiểm tra mật khẩu
    is_match = bcrypt.checkpw(user.password.encode(), user_db.password)

    if not is_match:
        raise HTTPException(400, 'Incorrect password!')

    # Kiểm tra trạng thái người dùng (có bị cấm hay không)
    user_f = db.query(User).filter(User.email == user.email, User.is_active == True).first()

    # if not user_f:
    #     raise HTTPException(400, 'User has been banned!')

    # Cập nhật trạng thái is_active thành None
    user_db.is_active = True
    db.commit()

    # Tạo token JWT
    token = jwt.encode({'id': user_db.id}, 'password_key')

    return {'token': token, 'user': user_db}



@router.post('/bannv')
def login_user(user: UserUnBannedNote, db: Session = Depends(get_db)):
    # Tìm người dùng theo email
    user_db = db.query(User).filter(User.email == user.email).first()

    if not user_db:
        raise HTTPException(400, 'User with this email does not exist!')

    # Kiểm tra mật khẩu
    is_match = bcrypt.checkpw(user.password.encode(), user_db.password)

    if not is_match:
        raise HTTPException(400, 'Incorrect password!')

    # Kiểm tra trạng thái người dùng (có bị cấm hay không)
    user_f = db.query(User).filter(User.email == user.email, User.is_active == True).first()

    # if not user_f:
    #     raise HTTPException(400, 'User has been banned!')

    # Cập nhật trạng thái is_active thành None
    user_db.is_active = False
    db.commit()

    # Tạo token JWT
    token = jwt.encode({'id': user_db.id}, 'password_key')

    return {'token': token, 'user': user_db}


#----------------------------------------------------------------------_______________________


@router.post('/listbanneduserbannednv')
def list_songs(db: Session = Depends(get_db), auth_details = Depends(auth_middleware)):
    # Lọc những nghệ sĩ có is_approved = False (chưa được duyệt)
    artists = db.query(User).filter(User.is_active == False,User.role=="moderator").all()
    
    return artists
@router.post('/listwaittobeunbannednv')
def list_songs(db: Session = Depends(get_db), auth_details = Depends(auth_middleware)):
    # Lọc những nghệ sĩ có is_approved = False (chưa được duyệt)
    artists = db.query(User).filter(User.is_active == None,User.role=="moderator").all()
    
    return artists
@router.post('/listnv')
def list_songs(db: Session = Depends(get_db), auth_details = Depends(auth_middleware)):
    # Lọc những nghệ sĩ có is_approved = False (chưa được duyệt)
    artists = db.query(User).filter(User.is_active == True,User.role=="moderator").all()
    
    return artists









@router.get('/')
def current_user_data(db: Session=Depends(get_db), 
                      user_dict = Depends(auth_middleware)):
    try:
        user = db.query(User).filter(User.id == user_dict['uid']).options(
            joinedload(User.favorites),
            joinedload(User.albums),
            joinedload(User.songs)
        ).first()
        # Thay đổi từ 'uid' thành 'id' để khớp với payload từ token
        # user = db.query(User).filter(User.id == user_dict['id']).options(
        #     joinedload(User.favorites),
        #     joinedload(User.albums),
        #     joinedload(User.songs)
        # ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
            
        return user
    except Exception as e:
        print(f"Error in current_user_data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

# @router.post("/change-password2")
# def change_password(
#     data: ChangePasswordRequest,
#     db: Session = Depends(get_db),
#     x_auth_token: str = Header(...),  # Lấy token từ header
#     user_dict: dict = Depends(auth_middleware)  # Middleware để xác thực token
# ):
#     # So sánh token trong header với token đã xác thực
#     if x_auth_token != user_dict['token']:
#         raise HTTPException(status_code=401, detail="Token mismatch, authorization failed!")

#     # Xác thực token và tìm người dùng
#     user = db.query(User).filter(User.id == user_dict['uid']).first()

#     if not user:
#         raise HTTPException(status_code=404, detail="User not found.")

#     # Kiểm tra mật khẩu hiện tại
#     if not data.current_password:
#         raise HTTPException(status_code=400, detail="Current password is required.")

#     # Lấy mật khẩu đã lưu trong cơ sở dữ liệu
#     stored_password_hash = user.password

#     # So sánh mật khẩu hiện tại với mật khẩu đã lưu
#     if not bcrypt.checkpw(data.current_password.encode(), stored_password_hash):  
#         raise HTTPException(status_code=400, detail="Current password is incorrect.")

#     # Băm mật khẩu mới và lưu lại trong cơ sở dữ liệu
#     hashed_new_password = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt())
#     user.password = hashed_new_password
#     db.commit()

#     return JSONResponse(
#         content={"detail": "Password changed successfully."},
#         status_code=200
#     )

@router.post('/loginadmin')
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    # Tìm người dùng theo email
    user_db = db.query(User).filter(User.email == user.email).first()

    if not user_db:
        raise HTTPException(400, 'User with this email does not exist!')

    # Kiểm tra mật khẩu
    is_match = bcrypt.checkpw(user.password.encode(), user_db.password)

    if not is_match:
        raise HTTPException(400, 'Incorrect password!')

    # Kiểm tra trạng thái người dùng (bị cấm và vai trò)
    if user_db.is_active == True and user_db.role == "user":
        raise HTTPException(400, 'Đây là tài khoản người dùng')

    if user_db.is_active == False and user_db.role == "moderator":
        raise HTTPException(400, 'Đây là tài khoản nhân viên')
    
    if user_db.is_active == True and user_db.role == "artist":
        raise HTTPException(400, 'Đây là tài khoản nghệ sĩ')
    # Tạo token JWT
    token = jwt.encode({'id': user_db.id}, 'password_key')

    return {'token': token, 'user': user_db}


@router.post('/change-password')
def change_password(
    name: str = Body(...),  # Sử dụng Body để nhận từ body của request
    current_password: str = Body(...),  # Tương tự
    new_password: str = Body(...),
    db: Session = Depends(get_db),
    user_dict=Depends(auth_middleware)
):
    user = db.query(User).filter(User.name == name).first()  # Sử dụng 'name' để tìm kiếm

    if not user:
        raise HTTPException(status_code=404, detail="User not found!")

    # Kiểm tra mật khẩu hiện tại
    if not bcrypt.checkpw(current_password.encode(), user.password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    # Băm mật khẩu mới và cập nhật vào cơ sở dữ liệu
    hashed_new_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
    user.password = hashed_new_password
    db.commit()

    return JSONResponse(
        content={"detail": "Password changed successfully."},
        status_code=200
    )



















# phần web

class ArtLogin(BaseModel):
    name: str
    password: str

class ArtistCreate(BaseModel):
    name: str
    password: str
    bio: Optional[str] = None
    image_url: Optional[str] = None

@router.post('/signupnv', status_code=201)
def signup_moderator(user: UserCreate, db: Session = Depends(get_db)):
    # Kiểm tra xem email đã tồn tại trong cơ sở dữ liệu hay chưa
    user_db = db.query(User).filter(User.email == user.email).first()
    if user_db:
        raise HTTPException(status_code=400, detail='User with the same email already exists!')

    # Hash mật khẩu
    hashed_pw = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt())
    
    # Tạo người dùng mới với vai trò là moderator
    user_db = User(
        id=str(uuid.uuid4()),
        email=user.email,
        password=hashed_pw,
        name=user.name,
        role="moderator",
        # created_by="admin"  # Gán vai trò là moderator
    )

    # Lưu người dùng vào cơ sở dữ liệu
    db.add(user_db)
    db.commit()

    # Chỉ trả về thông báo thành công
    return {"message": "Signup successful"}

@router.post('/loginart')
def login_user(artist: ArtLogin, db: Session = Depends(get_db)):
    # check if a user with same email already exist
    user_db = db.query(Artist).filter(Artist.name == artist.name).first()

    if not user_db:
        raise HTTPException(400, 'User with this name does not exist!')
    
    # password matching or not
    is_match = bcrypt.checkpw(artist.password.encode(), user_db.password)
    
    if not is_match:
        raise HTTPException(400, 'Incorrect password!')
    

    token = jwt.encode({'id': user_db.id}, 'password_key')
    
    return {'token': token, 'user': user_db}

@router.post("/approve/{artist_id}")
def approve_artist(
    artist_id: str,  # Sửa kiểu dữ liệu thành str
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm nghệ sĩ theo ID
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    
    if not artist:
        # Nếu không tìm thấy nghệ sĩ, trả về lỗi 404
        raise HTTPException(status_code=404, detail="Nghệ sĩ không tồn tại.")
    
    # Cập nhật trạng thái is_approved thành True
    artist.is_approved = True
    db.commit()  # Lưu thay đổi vào cơ sở dữ liệu
    db.refresh(artist)  # Tải lại dữ liệu từ cơ sở dữ liệu
    
    return {"message": "Nghệ sĩ đã được phê duyệt thành công.", "artist": artist}

@router.post("/approvenull/{artist_id}")
def approve_artist(
    artist_id: str,  # Sửa kiểu dữ liệu thành str
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm nghệ sĩ theo ID
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    
    if not artist:
        # Nếu không tìm thấy nghệ sĩ, trả về lỗi 404
        raise HTTPException(status_code=404, detail="Nghệ sĩ không tồn tại.")
    
    # Cập nhật trạng thái is_approved thành NULL
    artist.is_approved = None
    db.commit()  # Lưu thay đổi vào cơ sở dữ liệu
    db.refresh(artist)  # Tải lại dữ liệu từ cơ sở dữ liệu
    
    return {"message": "Nghệ sĩ đã được cập nhật trạng thái ẩn.", "artist": artist}

@router.post('/listartfail')
def list_songs(db: Session = Depends(get_db), auth_details = Depends(auth_middleware)):
    # Lọc những nghệ sĩ có is_approved = False (chưa được duyệt)
    artists = db.query(Artist).filter(Artist.is_approved == False).options(
        joinedload(Artist.songs)  # Nếu bạn muốn load các bài hát của nghệ sĩ
    ).all()
    
    return artists

class SearchRequest(BaseModel):
    search: Optional[str] = None  # Tham số tìm kiếm (tuỳ chọn)


@router.post('/listartfail')
def list_songs_fail(request: SearchRequest, db: Session = Depends(get_db), auth_details = Depends(auth_middleware)):
    search = request.search  # Lấy tham số tìm kiếm từ JSON body

    # Lọc nghệ sĩ có is_approved = False
    query = db.query(Artist).filter(Artist.is_approved == False)

    # Nếu có tham số tìm kiếm, tìm theo normalized_name của nghệ sĩ
    if search:
        query = query.filter(Artist.normalized_name.ilike(f"%{search}%"))

    # Lấy danh sách nghệ sĩ
    artists = query.options(joinedload(Artist.user)).all()

    # Trả về dữ liệu
    return [
        {
            "user_id": artist.user_id,
            "id": artist.id,
            "bio": artist.bio,
            "is_approved": artist.is_approved,
            "updated_at": artist.updated_at,
            "approved_at": artist.approved_at,
            "normalized_name": artist.normalized_name,
            "image_url": artist.image_url,
            "created_at": artist.created_at,
            "approved_by": artist.approved_by,
            "songs": artist.songs,
            "email": artist.user.email if artist.user else None  # Thêm email từ user liên kết
        }
        for artist in artists
    ]

# Endpoint cho listarttrue (nghệ sĩ đã được duyệt)
@router.post('/listarttrue')
def list_songs_true(request: SearchRequest, db: Session = Depends(get_db), auth_details = Depends(auth_middleware)):
    search = request.search  # Lấy tham số tìm kiếm từ JSON body

    # Lọc nghệ sĩ có is_approved = True
    query = db.query(Artist).filter(Artist.is_approved == True)

    # Nếu có tham số tìm kiếm, tìm theo normalized_name của nghệ sĩ
    if search:
        query = query.filter(Artist.normalized_name.ilike(f"%{search}%"))

    # Lấy danh sách nghệ sĩ
    artists = query.options(joinedload(Artist.user)).all()

    # Trả về dữ liệu
    return [
        {
            "user_id": artist.user_id,
            "id": artist.id,
            "bio": artist.bio,
            "is_approved": artist.is_approved,
            "updated_at": artist.updated_at,
            "approved_at": artist.approved_at,
            "normalized_name": artist.normalized_name,
            "image_url": artist.image_url,
            "created_at": artist.created_at,
            "approved_by": artist.approved_by,
            "songs": artist.songs,
            "email": artist.user.email if artist.user else None  # Thêm email từ user liên kết
        }
        for artist in artists
    ]
# Endpoint cho listartnull (nghệ sĩ chưa có trạng thái duyệt)
@router.post('/listartnull')
def list_songs_null(request: SearchRequest, db: Session = Depends(get_db), auth_details = Depends(auth_middleware)):
    search = request.search  # Lấy tham số tìm kiếm từ JSON body
# Lọc nghệ sĩ có is_approved = None
    query = db.query(Artist).filter(Artist.is_approved == None)

    # Nếu có tham số tìm kiếm, tìm theo normalized_name của nghệ sĩ
    if search:
        query = query.filter(Artist.normalized_name.ilike(f"%{search}%"))

    # Lấy danh sách nghệ sĩ
    artists = query.options(joinedload(Artist.user)).all()

    # Trả về dữ liệu
    return [
        {
            "user_id": artist.user_id,
            "id": artist.id,
            "bio": artist.bio,
            "is_approved": artist.is_approved,
            "updated_at": artist.updated_at,
            "approved_at": artist.approved_at,
            "normalized_name": artist.normalized_name,
            "image_url": artist.image_url,
            "created_at": artist.created_at,
            "approved_by": artist.approved_by,
            "songs": artist.songs,
            "email": artist.user.email if artist.user else None  # Thêm email từ user liên kết
        }
        for artist in artists
    ]

@router.post('/signupart', status_code=201)
def signup_artist(artist: ArtistCreate, db: Session = Depends(get_db)):
    # Kiểm tra xem nghệ sĩ đã tồn tại trong cơ sở dữ liệu chưa
    artist_db = db.query(Artist).filter(Artist.name == artist.name).first()

    if artist_db:
        raise HTTPException(status_code=400, detail="Artist with the same name already exists!")

    # Mã hóa mật khẩu trước khi lưu vào cơ sở dữ liệu
    hashed_pw = bcrypt.hashpw(artist.password.encode(), bcrypt.gensalt())

    artist_db = Artist(id=str(uuid.uuid4()),password=hashed_pw, name=artist.name, bio=artist.bio,image_url=artist.image_url)
    

    # Tạo mới nghệ sĩ, với `is_approved = False`
    # new_artist = Artist(
    #     id=str(uuid.uuid4()),
    #     name=artist.name,
    #     password=hashed_pw,
    #     normalized_name=artist.name.lower(),
    #     bio=artist.bio,
    #     image_url=artist.image_url,
    #     is_approved=False  # Đặt `is_approved` là False khi đăng ký
    # )

    # Thêm nghệ sĩ vào cơ sở dữ liệu
    db.add(artist_db)
    db.commit()
    db.refresh(artist_db)

    return artist_db




















#__________________________________________________________




class SearchRequest(BaseModel):
    search: Optional[str] = None  # Tham số tìm kiếm (tuỳ chọn)

@router.post('/listartfailuser')
def list_songs_fail(request: SearchRequest, db: Session = Depends(get_db), auth_details = Depends(auth_middleware)):
    search = request.search  # Lấy tham số tìm kiếm từ JSON body

    # Lọc nghệ sĩ có is_approved = False
    query = db.query(User).filter(User.is_active == False)

    # Nếu có tham số tìm kiếm, tìm theo normalized_name của nghệ sĩ
    if search:
        query = query.filter(User.name.ilike(f"%{search}%"))

    artists = query.options(joinedload(User.songs)).all()

    return artists

# Endpoint cho listarttrue (nghệ sĩ đã được duyệt)
@router.post('/listarttrueuser')
def list_songs_true(request: SearchRequest, db: Session = Depends(get_db), auth_details = Depends(auth_middleware)):
    search = request.search  # Lấy tham số tìm kiếm từ JSON body

    # Lọc nghệ sĩ có is_approved = True
    query = db.query(User).filter(User.is_active == True,User.role=="user")

    # Nếu có tham số tìm kiếm, tìm theo normalized_name của nghệ sĩ
    if search:
        query = query.filter(User.name.ilike(f"%{search}%"))

    artists = query.options(joinedload(User.songs)).all()

    return artists

# Endpoint cho listartnull (nghệ sĩ chưa có trạng thái duyệt)
@router.post('/listartnulluser')
def list_songs_null(request: SearchRequest, db: Session = Depends(get_db), auth_details = Depends(auth_middleware)):
    search = request.search  # Lấy tham số tìm kiếm từ JSON body

    # Lọc nghệ sĩ có is_approved = None
    query = db.query(User).filter(User.is_active == None)

    # Nếu có tham số tìm kiếm, tìm theo normalized_name của nghệ sĩ
    if search:
        query = query.filter(User.name.ilike(f"%{search}%"))

    artists = query.options(joinedload(User.songs)).all()

    return artists




@router.post('/listartfailuser1')
def list_songs_fail(request: SearchRequest, db: Session = Depends(get_db)):
    search = request.search  # Lấy tham số tìm kiếm từ JSON body

    # Lọc nghệ sĩ có is_approved = False
    query = db.query(User).filter(User.is_active == False,User.role=="moderator")

    # Nếu có tham số tìm kiếm, tìm theo normalized_name của nghệ sĩ
    if search:
        query = query.filter(User.name.ilike(f"%{search}%"))

    artists = query.options(joinedload(User.songs)).all()

    return artists

# Endpoint cho listarttrue (nghệ sĩ đã được duyệt)
@router.post('/listarttrueuser1')
def list_songs_true(request: SearchRequest, db: Session = Depends(get_db)):
    search = request.search  # Lấy tham số tìm kiếm từ JSON body

    # Lọc nghệ sĩ có is_approved = True
    query = db.query(User).filter(User.is_active == True,User.role=="moderator")

    # Nếu có tham số tìm kiếm, tìm theo normalized_name của nghệ sĩ
    if search:
        query = query.filter(User.name.ilike(f"%{search}%"))

    artists = query.options(joinedload(User.songs)).all()

    return artists

# Endpoint cho listartnull (nghệ sĩ chưa có trạng thái duyệt)
@router.post('/listartnulluser1')
def list_songs_null(request: SearchRequest, db: Session = Depends(get_db)):
    search = request.search  # Lấy tham số tìm kiếm từ JSON body

    # Lọc nghệ sĩ có is_approved = None
    query = db.query(User).filter(User.is_active == None,User.role=="moderator")

    # Nếu có tham số tìm kiếm, tìm theo normalized_name của nghệ sĩ
    if search:
        query = query.filter(User.name.ilike(f"%{search}%"))

    artists = query.options(joinedload(User.songs)).all()

    return artists



#GỌI TRONG TRANG BAN USER
@router.post("/songtrue2/{song_id}")
async def get_song_by_id(song_id: str, db: Session = Depends(get_db)):
    # Tìm bài hát theo song_id trong cơ sở dữ liệu và lọc các bài hát có is_hidden = false
    song = db.query(User).filter(User.id == song_id, User.is_active == True).first()

    if not song:
        raise HTTPException(status_code=404, detail="Song not found or is hidden")
    
    return song

#NÚT TRONG TRANG BAN USER
@router.post("/song/songnone2/{song_id}")
def approve_artist(
    song_id: str,  # Kiểu dữ liệu là str
    # Nhận hidden_reason từ request body
    db: Session = Depends(get_db),
    # auth_details=Depends(auth_middleware),
):
    # Tìm bài hát theo ID
    song = db.query(User).filter(User.id == song_id).first()
    
    if not song:
        # Nếu không tìm thấy bài hát, trả về lỗi 404
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại.")
    
    # Tìm người dùng có vai trò "moderator"
    moderator = db.query(User).filter(User.role == "moderator").first()
    
    if not moderator:
        # Nếu không tìm thấy người dùng có vai trò moderator, trả về lỗi
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng với vai trò moderator.")
    
    # Cập nhật trạng thái và lưu thông tin
    song.is_active = None  # Phê duyệt bài hát, không còn bị ẩn
    # song.hidden_by = moderator.id  # Lưu ID của moderator phê duyệt
    # song.hidden_reason = song_request.hidden_reason  # Lưu lý do từ request body
    
    # Lưu thay đổi vào cơ sở dữ liệu
    db.commit()
    db.refresh(song)  # Tải lại dữ liệu từ cơ sở dữ liệu để phản hồi dữ liệu cập nhật
    
    return {
        "message": "Bài hát đã được phê duyệt thành công.",
        "song": song
    }



@router.post("/songnone3/{song_id}")
async def get_song_by_id(song_id: str, db: Session = Depends(get_db)):
    # Tìm bài hát theo song_id trong cơ sở dữ liệu và lọc các bài hát có is_hidden = false
    song = db.query(User).filter(User.id == song_id, User.is_active == None).first()

    if not song:
        raise HTTPException(status_code=404, detail="Song not found or is hidden")
    
    return song



@router.post("/song/songtrue3/{song_id}")
def approve_artist(
    song_id: str,  # Sửa kiểu dữ liệu thành str
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm nghệ sĩ theo ID 
    song = db.query(User).filter(User.id == song_id).first()
    
   
    
    # Cập nhật trạng thái is_approved thành True
    song.is_active = True
    db.commit()  # Lưu thay đổi vào cơ sở dữ liệu
    db.refresh(song)  # Tải lại dữ liệu từ cơ sở dữ liệu
    
    return {"message": "Nghệ sĩ đã được phê duyệt thành công.", "artist": song}



#GỌI TRONG TRANG BAN USER
@router.post("/songtrue/{song_id}")
async def get_song_by_id(song_id: str, db: Session = Depends(get_db)):
    # Tìm bài hát theo song_id trong cơ sở dữ liệu và lọc các bài hát có is_hidden = false
    song = db.query(User).filter(User.id == song_id, User.is_active == True).first()

    if not song:
        raise HTTPException(status_code=404, detail="Song not found or is hidden")
    
    return song

#NÚT TRONG TRANG BAN USER
@router.post("/song/songnone/{song_id}")
def approve_artist(
    song_id: str,  # Kiểu dữ liệu là str
    # Nhận hidden_reason từ request body
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):
    # Tìm bài hát theo ID
    song = db.query(User).filter(User.id == song_id).first()
    
    if not song:
        # Nếu không tìm thấy bài hát, trả về lỗi 404
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại.")
    
    # Tìm người dùng có vai trò "moderator"
    moderator = db.query(User).filter(User.role == "moderator").first()
    
    if not moderator:
        # Nếu không tìm thấy người dùng có vai trò moderator, trả về lỗi
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng với vai trò moderator.")
    
    # Cập nhật trạng thái và lưu thông tin
    song.is_active = None  # Phê duyệt bài hát, không còn bị ẩn
    # song.hidden_by = moderator.id  # Lưu ID của moderator phê duyệt
    # song.hidden_reason = song_request.hidden_reason  # Lưu lý do từ request body
    
    # Lưu thay đổi vào cơ sở dữ liệu
    db.commit()
    db.refresh(song)  # Tải lại dữ liệu từ cơ sở dữ liệu để phản hồi dữ liệu cập nhật
    
    return {
        "message": "Bài hát đã được phê duyệt thành công.",
        "song": song
    }

@router.post("/songnone1/{song_id}")
async def get_song_by_id(song_id: str, db: Session = Depends(get_db)):
    # Tìm bài hát theo song_id trong cơ sở dữ liệu và lọc các bài hát có is_hidden = false
    song = db.query(User).filter(User.id == song_id, User.is_active == None).first()

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
    song = db.query(User).filter(User.id == song_id).first()
    
   
    
    # Cập nhật trạng thái is_approved thành True
    song.is_active = True
    db.commit()  # Lưu thay đổi vào cơ sở dữ liệu
    db.refresh(song)  # Tải lại dữ liệu từ cơ sở dữ liệu
    
    return {"message": "Nghệ sĩ đã được phê duyệt thành công.", "artist": song}











@router.post("/nhanvien")
def approve_artist(
    # song_id: str,  # Sửa kiểu dữ liệu thành str
    db: Session = Depends(get_db),
    auth_details=Depends(auth_middleware),
):

    print("Auth Details:", auth_details)
    user = db.query(User).filter(User.id == auth_details['uid']).first()

  
    
    return user





@router.post("/change-password2")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),

    user_dict: dict = Depends(auth_middleware)  # Middleware để xác thực token
):


    # Xác thực token và tìm người dùng
    user = db.query(User).filter(User.id == user_dict['uid']).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Kiểm tra mật khẩu hiện tại
    if not data.current_password:
        raise HTTPException(status_code=400, detail="Current password is required.")

    # Lấy mật khẩu đã lưu trong cơ sở dữ liệu
    stored_password_hash = user.password

    # So sánh mật khẩu hiện tại với mật khẩu đã lưu
    if not bcrypt.checkpw(data.current_password.encode(), stored_password_hash):  
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    # Băm mật khẩu mới và lưu lại trong cơ sở dữ liệu
    hashed_new_password = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt())
    user.password = hashed_new_password
    db.commit()

    return JSONResponse(
        content={"detail": "Password changed successfully."},
        status_code=200
    )



@router.post('/loginadmin')
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    # Tìm người dùng theo email
    user_db = db.query(User).filter(User.email == user.email).first()

    if not user_db:
        raise HTTPException(400, 'User with this email does not exist!')

    # Kiểm tra mật khẩu
    is_match = bcrypt.checkpw(user.password.encode(), user_db.password)

    if not is_match:
        raise HTTPException(400, 'Incorrect password!')

    # Kiểm tra trạng thái người dùng (bị cấm và vai trò)
    if user_db.is_active == True and user_db.role == "user":
        raise HTTPException(400, 'Đây là tài khoản người dùng')

    if user_db.is_active == False and user_db.role == "moderator":
        raise HTTPException(400, 'Đây là tài khoản nhân viên')
    
    if user_db.is_active == True and user_db.role == "artist":
        raise HTTPException(400, 'Đây là tài khoản nghệ sĩ')
    # Tạo token JWT
    token = jwt.encode({'id': user_db.id}, 'password_key')

    return {'token': token, 'user': user_db}
