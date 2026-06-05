from datetime import datetime

from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Destination(Base):
    __tablename__ = "destinations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    city: Mapped[str] = mapped_column(String(64), index=True)
    country: Mapped[str] = mapped_column(String(32), default="中国")
    region: Mapped[str] = mapped_column(String(16))
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    timezone: Mapped[str] = mapped_column(String(16), default="UTC+8")
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    cost: Mapped[int] = mapped_column(Integer)
    popularity: Mapped[int] = mapped_column(Integer, default=0)
    scenic_spots_count: Mapped[int] = mapped_column(Integer, default=0)
    traffic_score: Mapped[int] = mapped_column(Integer, default=0)
    price_index: Mapped[int] = mapped_column(Integer, default=100)
    crowd_level: Mapped[int] = mapped_column(Integer, default=50)
    climate_score: Mapped[int] = mapped_column(Integer, default=50)
    niche_score: Mapped[int] = mapped_column(Integer, default=0)
    interests: Mapped[str] = mapped_column(Text, default="[]")
    adcode: Mapped[str | None] = mapped_column(String(6), index=True, nullable=True)
    level: Mapped[str] = mapped_column(String(10), default="city")
    parent_adcode: Mapped[str | None] = mapped_column(String(6), nullable=True)
    population_tier: Mapped[str] = mapped_column(String(8), default="")
    is_tourist_city: Mapped[bool] = mapped_column(Boolean, default=False)
    image_url: Mapped[str] = mapped_column(String(512), default="")

    scenic_spots: Mapped[list["ScenicSpot"]] = relationship(
        back_populates="destination", cascade="all, delete-orphan"
    )


class ScenicSpot(Base):
    __tablename__ = "scenic_spots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    destination_id: Mapped[str] = mapped_column(String(32), ForeignKey("destinations.id"))
    name: Mapped[str] = mapped_column(String(128))
    grade: Mapped[str] = mapped_column(String(4))  # '5A' or '4A'

    destination: Mapped["Destination"] = relationship(back_populates="scenic_spots")


class Holiday(Base):
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32))
    start_date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    end_date: Mapped[str] = mapped_column(String(10))
    crowd_boost: Mapped[int] = mapped_column(Integer, default=10)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(128), default="")
    hashed_password: Mapped[str] = mapped_column(String(256))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    saved_itineraries: Mapped[list["SavedItinerary"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class SavedItinerary(Base):
    __tablename__ = "saved_itineraries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(128), default="未命名行程")
    trip_start_date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    stops: Mapped[str] = mapped_column(Text)  # JSON: [{id, stayDays, ...}]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="saved_itineraries")
