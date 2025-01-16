from models.base import Base
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

class PlayCountHistory(Base):
    __tablename__ = 'play_count_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    song_id = Column(Text, ForeignKey('songs.id'), nullable=False)
    week_start_date = Column(DateTime, nullable=False)  # Ngày bắt đầu của tuần
    play_count = Column(Integer, default=0)  # Số lượt nghe trong tuần

    song = relationship("Song", back_populates="play_count_history")
    
    def __repr__(self):
        return f"<PlayCountHistory(song_id={self.song_id}, week_start_date={self.week_start_date}, play_count={self.play_count})>"
