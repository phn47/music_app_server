from sqlalchemy import Column, ForeignKey, Table
from models.base import Base

song_artists = Table(
    'song_artists',
    Base.metadata,
    Column('song_id', ForeignKey('songs.id'), primary_key=True),
    Column('artist_id', ForeignKey('artists.id'), primary_key=True)
) 