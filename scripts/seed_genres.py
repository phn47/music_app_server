import sys
import os

# Thêm thư mục gốc vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Sssion
from database import SessionLocal, engine
from models.base import Base
from models.genre import Genre
import uuid

# Tạo bảng nếu chưa tồn tại
Base.metadata.create_all(bind=engine)

def seed_genres():
    db = SessionLocal()
    
    # Danh sách genres mẫu
    sample_genres = [
        {
            "name": "Nhạc",
            "description": "Các bài hát phổ biến và được yêu thích",
            "hex_code": "#E91E63",
            "image_url": "https://res.cloudinary.com/derzqoidk/image/upload/v1733332655/genres/be21w5ap2tjhy9vdcwur.jpg"
        },
        {
            "name": "Podcasts", 
            "description": "Nội dung podcast đa dạng",
            "hex_code": "#006D5B",
            "image_url": "https://res.cloudinary.com/derzqoidk/image/upload/v1733332819/genres/se2gvpbmh4eeg9xnhlih.jpg"
        },
        {
            "name": "Sự kiện trực tiếp",
            "description": "Các sự kiện âm nhạc trực tiếp",
            "hex_code": "#8B2CFF", 
            "image_url": "https://res.cloudinary.com/derzqoidk/image/upload/v1733332891/genres/prutuweisphiqim9nfeu.jpg"
        },
        {
            "name": "Nhạc trong năm 2024",
            "description": "Tổng hợp nhạc hot 2024",
            "hex_code": "#1DB954",
            "image_url": "https://res.cloudinary.com/derzqoidk/image/upload/v1733332978/genres/zvh4cuibnpbhofhxbg63.jpg"
        },
        {
            "name": "Pop",
            "description": "Nhạc pop thịnh hành",
            "hex_code": "#4F9BFF",
            "image_url": "https://res.cloudinary.com/derzqoidk/image/upload/v1733333034/genres/eghtpgjmmzovzdxkffx1.jpg"
        },
        {
            "name": "K-Pop",
            "description": "Nhạc pop Hàn Quốc",
            "hex_code": "#FF2E5E",
            "image_url": "https://res.cloudinary.com/derzqoidk/image/upload/v1733333078/genres/vpuwpyw7bbkm7j7yvspw.jpg"
        },
        {
            "name": "Hip-Hop",
            "description": "Nhạc hip hop và rap",
            "hex_code": "#FF4A1C",
            "image_url": "https://res.cloudinary.com/derzqoidk/image/upload/v1733333116/genres/t3nhfwbvizbm6gzmjsvh.jpg"
        }
    ]
    
    try:
        # Thêm từng genre vào database
        for genre_data in sample_genres:
            genre = Genre(
                id=str(uuid.uuid4()),
                name=genre_data["name"],
                description=genre_data["description"],
                hex_code=genre_data["hex_code"],
                image_url=genre_data["image_url"]
            )
            db.add(genre)
        
        db.commit()
        print("Thêm genres thành công!")
        
    except Exception as e:
        print(f"Lỗi khi thêm genres: {str(e)}")
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    seed_genres() 