from sqlalchemy import Column, TEXT, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from models.base import Base

class Comment(Base):
    __tablename__ = 'comments'

    id = Column(TEXT, primary_key=True)
    song_id = Column(TEXT, ForeignKey('songs.id'), nullable=False)
    user_id = Column(TEXT, ForeignKey('users.id'), nullable=False)
    content = Column(TEXT, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Quan hệ với song và user
    song = relationship("Song", back_populates="comments")
    user = relationship("User", back_populates="comments")




    def as_dict(self):
        return {
            "id": self.id,
            "song_id": self.song_id,
            "user_id": self.user_id,
            "content": self.content,
        }