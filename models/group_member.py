


from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from models.base import Base
from models.group import Group

class GroupMember(Base):
    __tablename__ = "group_members"
    is_banned = Column(Boolean, default=False) 

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="groups")
    group = relationship("Group", back_populates="members")
    