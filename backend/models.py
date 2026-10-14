
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    spotify_id: str
    display_name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    city: str | None = None


class CityUpdate(BaseModel):
    city: str


class ArtistResponse(BaseModel):
    artist_id: str
    artist_name: str
    artist_image_url: str | None = None
    affinity_score: float
    genres: list[str] = []


class SyncResponse(BaseModel):
    synced: int
    artists: list[ArtistResponse]


class ConcertResponse(BaseModel):
    event_id: str
    event_name: str
    venue_name: str | None = None
    venue_city: str | None = None
    event_date: str | None = None
    ticket_url: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    artist_id: str
    artist_name: str
    artist_image_url: str | None = None
    affinity_score: float
    genres: list[str] = []


class ConcertsListResponse(BaseModel):
    total: int
    concerts: list[ConcertResponse]
