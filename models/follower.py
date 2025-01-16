from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class Follower(Base):
    __tablename__ = 'followers'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))
    artist_id = Column(String, ForeignKey('artists.id'))
    
    artist = relationship("Artist", back_populates="followers")