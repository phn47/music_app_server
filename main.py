import os
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from model import AudioToLRCModel
from models.base import Base
from models.artist import Artist
from models.follower import Follower
from models.song import Song
from models.genre import Genre
from models.album import Album
from models.favorite import Favorite
from models.song_artist import song_artists
from models.comment import Comment
# from models.message import Message
from routes import auth, song, albums, artist, genre
from database import engine
from fastapi.middleware.cors import CORSMiddleware
import cloudinary
import json

app = FastAPI()

# Cấu hình JSON encoder để xử lý UTF-8
class UnicodeJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sử dụng UnicodeJSONResponse làm default response class
app.default_response_class = UnicodeJSONResponse

# Cấu hình Cloudinary
cloudinary.config( 
    cloud_name = "derzqoidk", 
    api_key = "622479785549768", 
    api_secret = "ZBKYfdGsksqcx0wjvRKtg6v0nn0", 
    secure=True
)

app.include_router(auth.router, prefix='/auth', tags=["auth"])
app.include_router(song.router, prefix='/songs', tags=["songs"])
app.include_router(albums.router, prefix='/albums', tags=["albums"])
app.include_router(artist.router, prefix='/auth/artist', tags=["artist"])
app.include_router(genre.router, prefix='/genre')

# Tạo bảng nếu chưa tồn tại
Base.metadata.create_all(bind=engine)

audio_to_lrc_model = AudioToLRCModel()

@app.post("/train/")
async def train_model(audio: UploadFile = File(...), lrc: UploadFile = File(...)):
    # Define the directories for storing files
    audio_dir = "data/audio"
    lrc_dir = "data/lyrics"

    # Create directories if they don't exist
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(lrc_dir, exist_ok=True)

    # Preserve the original filenames
    audio_path = os.path.join(audio_dir, audio.filename)
    lrc_path = os.path.join(lrc_dir, lrc.filename)

    # Log filenames to verify they're correct
    print("Audio filename:", audio.filename)
    print("LRC filename:", lrc.filename)

    # Save the audio file
    with open(audio_path, "wb") as audio_file:
        audio_file.write(await audio.read())

    # Save the LRC file
    with open(lrc_path, "wb") as lrc_file:
        lrc_file.write(await lrc.read())

    # Call the training method (assuming it’s defined)
    audio_to_lrc_model.train(audio_path, lrc_path)

    return JSONResponse(content={"message": "Model trained successfully!"})

# Thêm middleware để xử lý encoding
@app.middleware("http")
async def add_encoding_header(request, call_next):
    try:
        response = await call_next(request)
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        return response
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
            headers={"Content-Type": "application/json; charset=utf-8"}
        )


