from sqlalchemy import TEXT, Column, DateTime, Integer, String, ForeignKey, func
from sqlalchemy.orm import relationship
from models.base import Base

class Block(Base):
    __tablename__ = 'blocks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    blocker_id = Column(TEXT, ForeignKey('users.id'), nullable=False)  # Người chặn
    blocked_id = Column(TEXT, ForeignKey('users.id'), nullable=False)  # Người bị chặn
    blocked_at = Column(DateTime(timezone=True), server_default=func.now())

    blocker = relationship("User", foreign_keys=[blocker_id])
    blocked = relationship("User", foreign_keys=[blocked_id])

    def as_dict(self):
        return {
            "blocker_id": self.blocker_id,
            "blocked_id": self.blocked_id,
            "blocked_at": self.blocked_at.isoformat() if self.blocked_at else None
        }