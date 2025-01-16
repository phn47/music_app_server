from sqlalchemy import Column, TEXT, VARCHAR, ForeignKey, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models import genre
from models.base import Base
from models.song_artist import song_artists


class Song(Base):
    __tablename__ = 'songs'

    id = Column(TEXT, primary_key=True)
    song_name = Column(VARCHAR(100), nullable=False)
    thumbnail_url = Column(TEXT)
    song_url = Column(TEXT)
    hex_code = Column(TEXT)
    user_id = Column(TEXT, ForeignKey('users.id'))
    album_id = Column(TEXT, ForeignKey('albums.id'))
    artist_id = Column(TEXT, ForeignKey('artists.id'))
    genre_id = Column(TEXT, ForeignKey('genres.id'))
    
    status = Column(Enum('pending', 'approved', 'rejected', name='content_status'), default='pending')
    approved_by = Column(TEXT, ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_reason = Column(TEXT, nullable=True)
    
    is_hidden = Column(Boolean, default=False)
    hidden_reason = Column(TEXT, nullable=True)
    hidden_by = Column(TEXT, ForeignKey('users.id'), nullable=True)
    hidden_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship('User', back_populates='songs', foreign_keys=[user_id])
    hidden_by_user = relationship('User', foreign_keys=[hidden_by])
    approved_by_user = relationship('User', foreign_keys=[approved_by])
    album = relationship('Album', back_populates='songs')
    artists = relationship('Artist', secondary=song_artists, back_populates='songs')
    genres = relationship('Genre', back_populates='songs')
    comments = relationship('Comment', back_populates='song')
    play_count_history = relationship("PlayCountHistory", back_populates="song")





    def as_dict(self):
        """
        Chuyển đổi đối tượng Song thành dictionary để trả về tất cả thông tin.
        """
        data = {
            "id": self.id,
            "song_name": self.song_name,
            "thumbnail_url": self.thumbnail_url,
            "song_url": self.song_url,
            "hex_code": self.hex_code,
            "user_id": self.user_id,
            "album_id": self.album_id,
            "artist_id": self.artist_id,
            "status": self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "rejected_reason": self.rejected_reason,
            "is_hidden": self.is_hidden,
            "hidden_reason": self.hidden_reason,
            "hidden_by": self.hidden_by,
            "hidden_at": self.hidden_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

        # Nếu bài hát bị ẩn, thêm thông tin về người ẩn
        if self.hidden_by is not None:
            # Thêm thông tin về người ẩn bài hát và vai trò
            if hasattr(self, 'hidden_by_user_role'):
                data["hidden_by_user_role"] = self.hidden_by_user_role

        return data

