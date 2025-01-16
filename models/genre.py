from sqlalchemy import Column, TEXT, VARCHAR
from sqlalchemy.orm import relationship
from models.base import Base

class Genre(Base):
    __tablename__ = 'genres'
    
    id = Column(TEXT, primary_key=True)
    name = Column(VARCHAR(50), nullable=False)
    image_url = Column(TEXT)
    hex_code = Column(TEXT)
    description = Column(TEXT)
    
    # Thêm relationship với songs
    songs = relationship('Song', back_populates='genres')
    