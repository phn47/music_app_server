from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from models.base import Base
from sqlalchemy.sql import func

class GroupMessage(Base):
    __tablename__ = "group_messages"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(String, ForeignKey("users.id"), nullable=True)  # Cho phép null nếu không có người nhận cụ thể
    content = Column(String, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

    # Quan hệ với bảng Group (nhóm gửi tin nhắn)
    group = relationship("Group", back_populates="group_messages")

    # Quan hệ với bảng User (người gửi tin nhắn)
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    
    # Quan hệ với bảng User (người nhận tin nhắn)
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")

    # Quan hệ với bảng Reaction
    reactions = relationship("MessageReaction", back_populates="message")
    
    
    def as_dict(self):
        return {
            "id": str(self.id),
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "receiver_name": self.receiver.name if self.receiver else None,
            "content": self.content,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None
        }