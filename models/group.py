
from sqlalchemy import TEXT, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from models.base import Base

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    thumbnail_url = Column(TEXT)
    creator_id = Column(Text, ForeignKey("users.id"), nullable=False)  # Lưu người tạo
    creator = relationship("User", backref="created_groups")  # Quan hệ với User
    # members = relationship('User', secondary='group_members', back_populates='groups')  # Fixed here
    members = relationship("GroupMember", back_populates="group")
    group_messages = relationship("GroupMessage", back_populates="group")
    
    # blocked_members = relationship("BlockedGroupMember", back_populates="group", cascade="all, delete-orphan")


    reactions = relationship("MessageReaction", back_populates="group")  # Phải là "group" thay vì "message"

