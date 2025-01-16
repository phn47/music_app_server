from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base
from models.song_artist import song_artists
from models.follower import Follower

class Artist(Base):
    __tablename__ = 'artists'
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey('users.id'), unique=True, nullable=False)
    normalized_name = Column(String, nullable=False)
    bio = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String, nullable=True)
    
    user = relationship('User', back_populates='artists')
    songs = relationship('Song', secondary=song_artists, back_populates='artists')
    followers = relationship('Follower', back_populates='artist')
