# from sqlalchemy import TEXT, VARCHAR, NVARCHAR, Column, LargeBinary, String, Enum, Boolean, DateTime, ForeignKey
# from models.base import Base
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func

# class User(Base):
#     __tablename__ = 'users'

#     id = Column(TEXT, primary_key=True)
#     name = Column(VARCHAR(100))
#     email = Column(VARCHAR(100))
#     password = Column(LargeBinary)
#     role = Column(Enum('admin', 'moderator', 'user', 'artist', name='user_roles'), default='user')
#     is_active = Column(Boolean, default=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     created_by = Column(String, ForeignKey('users.id'), nullable=True)
    
#     favorites = relationship('Favorite', back_populates='user')
#     albums = relationship('Album', back_populates='user', foreign_keys='[Album.user_id]')
#     songs = relationship('Song', back_populates='user', foreign_keys='[Song.user_id]')
#     artists = relationship('Artist', back_populates='user')
#     comments = relationship('Comment', back_populates='user')
#     sent_messages = relationship('Message', foreign_keys='Message.sender_id')
#     received_messages = relationship('Message', foreign_keys='Message.receiver_id')
#     groups = relationship("GroupMember", back_populates="user")
#     blocked_in_groups = relationship("BlockedGroupMember", back_populates="user")
#     # Quan hệ với Reaction (Cần phải khai báo "back_populates" đúng)
#     reactions = relationship("MessageReaction", back_populates="user")
#     messages = relationship("GroupMessage", back_populates="sender")


from sqlalchemy import TEXT, VARCHAR, NVARCHAR, Column, LargeBinary, String, Enum, Boolean, DateTime, ForeignKey
from models.base import Base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
class User(Base):
    __tablename__ = 'users'

    id = Column(TEXT, primary_key=True)
    name = Column(VARCHAR(100))
    email = Column(VARCHAR(100))
    password = Column(LargeBinary)
    role = Column(Enum('admin', 'moderator', 'user', 'artist', name='user_roles'), default='user')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String, ForeignKey('users.id'), nullable=True)

    # Các mối quan hệ khác
    favorites = relationship('Favorite', back_populates='user')
    albums = relationship('Album', back_populates='user', foreign_keys='[Album.user_id]')
    songs = relationship('Song', back_populates='user', foreign_keys='[Song.user_id]')
    artists = relationship('Artist', back_populates='user')
    comments = relationship('Comment', back_populates='user')
    groups = relationship("GroupMember", back_populates="user")
    reactions = relationship("MessageReaction", back_populates="user")

    # Thêm mối quan hệ rõ ràng với GroupMessage
    sent_messages = relationship(
        "GroupMessage",
        foreign_keys='GroupMessage.sender_id',
        back_populates="sender",
    )
    received_messages = relationship(
        "GroupMessage",
        foreign_keys='GroupMessage.receiver_id',
        back_populates="receiver",
    )