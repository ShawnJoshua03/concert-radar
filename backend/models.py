from typing import Optional
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    spotify_id: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    city: Optional[str] = None


class CityUpdate(BaseModel):
    city: str


class ArtistResponse(BaseModel):
    artist_id: str
    artist_name: str
    artist_image_url: Optional[str] = None
    affinity_score: float
    genres: list[str] = []


class SyncResponse(BaseModel):
    synced: int
    artists: list[ArtistResponse]


class ConcertResponse(BaseModel):
    event_id: str
    event_name: str
    venue_name: Optional[str] = None
    venue_city: Optional[str] = None
    event_date: Optional[str] = None
    ticket_url: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    artist_id: str
    artist_name: str
    artist_image_url: Optional[str] = None
    affinity_score: float
    genres: list[str] = []


class ConcertsListResponse(BaseModel):
    total: int
    concerts: list[ConcertResponse]
