from sqlalchemy import NVARCHAR, TEXT, VARCHAR, Column, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base

class Album(Base):
    __tablename__ = 'albums'

    id = Column(TEXT, primary_key=True)
    name = Column(VARCHAR(100), nullable=False)
    description = Column(TEXT)
    thumbnail_url = Column(TEXT)
    user_id = Column(TEXT, ForeignKey("users.id"))
    
    # Trạng thái duyệt
    status = Column(Enum('pending', 'approved', 'rejected', name='content_status'), default='pending')
    approved_by = Column(TEXT, ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_reason = Column(TEXT, nullable=True)
    
    # Trạng thái ẩn
    is_hidden = Column(Boolean, default=False)
    hidden_reason = Column(TEXT, nullable=True)
    hidden_by = Column(TEXT, ForeignKey('users.id'), nullable=True)
    hidden_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    songs = relationship('Song', back_populates='album')
    user = relationship('User', 
                       back_populates='albums', 
                       foreign_keys=[user_id])
    hidden_by_user = relationship('User', 
                                foreign_keys=[hidden_by])
    approved_by_user = relationship('User', 
                                  foreign_keys=[approved_by])
    is_public = Column(Boolean, default=True)
