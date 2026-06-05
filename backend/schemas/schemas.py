from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


# ── Destination ──
class ScenicSpotOut(BaseModel):
    id: int
    name: str
    grade: str

    model_config = {"from_attributes": True}


class DestinationOut(BaseModel):
    id: str
    city: str
    country: str
    region: str
    currency: str
    timezone: str
    lat: float
    lng: float
    cost: int
    popularity: int
    scenic_spots_count: int
    traffic_score: int
    price_index: int
    crowd_level: int
    climate_score: int
    niche_score: int
    interests: str
    adcode: str | None = None
    level: str = "city"
    parent_adcode: str | None = None
    population_tier: str = ""
    is_tourist_city: bool = False
    image_url: str = ""
    scenic_spots: list[ScenicSpotOut] = []

    model_config = {"from_attributes": True}


class DestinationBrief(BaseModel):
    """Lightweight destination card for list views (no scenic_spots)."""
    id: str
    city: str
    country: str
    region: str
    lat: float
    lng: float
    cost: int
    popularity: int
    scenic_spots_count: int
    traffic_score: int
    price_index: int
    crowd_level: int
    climate_score: int
    niche_score: int
    interests: str
    adcode: str | None = None
    level: str = "city"
    population_tier: str = ""
    is_tourist_city: bool = False

    model_config = {"from_attributes": True}


class DestinationCreate(BaseModel):
    id: str
    city: str
    country: str = "中国"
    region: str
    lat: float
    lng: float
    cost: int
    popularity: int = 0
    scenic_spots_count: int = 0
    traffic_score: int = 0
    price_index: int = 100
    crowd_level: int = 50
    climate_score: int = 50
    niche_score: int = 0
    interests: list[str] = []
    adcode: str | None = None
    level: str = "city"
    parent_adcode: str | None = None
    population_tier: str = ""
    is_tourist_city: bool = False


class ScenicSpotCreate(BaseModel):
    destination_id: str
    name: str
    grade: str  # '5A' or '4A'


# ── Holiday ──
class HolidayOut(BaseModel):
    id: int
    name: str
    start_date: str
    end_date: str
    crowd_boost: int

    model_config = {"from_attributes": True}


class HolidayCreate(BaseModel):
    name: str
    start_date: str
    end_date: str
    crowd_boost: int = 10


# ── Auth ──
class UserCreate(BaseModel):
    username: str
    email: str = ""
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Itinerary ──
class ItineraryStop(BaseModel):
    id: str
    city: str
    country: str
    stayDays: int = 2
    cost: int = 0
    lat: float = 0
    lng: float = 0


class SavedItineraryCreate(BaseModel):
    name: str = "未命名行程"
    trip_start_date: str
    stops: list[ItineraryStop]


class SavedItineraryOut(BaseModel):
    id: int
    name: str
    trip_start_date: str
    stops: str  # JSON string
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Recommendation Request ──
class RecommendRequest(BaseModel):
    budget: int = 1500
    interests: list[str] = []
    style: str = "舒适休闲"  # 背包穷游, 舒适休闲, 奢华体验, 亲子家庭
    climate: str = "温和"   # 温暖, 温和, 凉爽


# ── Admin Stats ──
class AdminStats(BaseModel):
    user_count: int
    destination_count: int
    itinerary_count: int
    api_call_count: int
