from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class MessageReaction(Base):
    __tablename__ = "message_reactions"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey('group_messages.id'))
    user_id = Column(String, ForeignKey('users.id'))
    group_id = Column(Integer, ForeignKey('groups.id'))  # Thêm khóa ngoại
    emoji = Column(String, index=True)  # Cảm xúc sẽ là một emoji

    # Các quan hệ
    message = relationship("GroupMessage", back_populates="reactions")  # Mối quan hệ với GroupMessage
    user = relationship("User", back_populates="reactions")



    group = relationship("Group", back_populates="reactions")

