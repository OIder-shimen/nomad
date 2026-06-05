import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.models import Destination, ScenicSpot, Holiday, User, SavedItinerary
from schemas.schemas import (
    DestinationCreate, DestinationOut, ScenicSpotCreate, ScenicSpotOut,
    HolidayCreate, HolidayOut, AdminStats, UserCreate,
)
from passlib.context import CryptContext
from routers.auth import get_admin_user

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(dependencies=[Depends(get_admin_user)])


# ── Stats Dashboard ──

@router.get("/stats", response_model=AdminStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    user_count = (await db.execute(select(func.count(User.id)))).scalar()
    dest_count = (await db.execute(select(func.count(Destination.id)))).scalar()
    itin_count = (await db.execute(select(func.count(SavedItinerary.id)))).scalar()
    return AdminStats(
        user_count=user_count or 0,
        destination_count=dest_count or 0,
        itinerary_count=itin_count or 0,
        api_call_count=0,  # placeholder
    )


# ── Destination Management ──

@router.post("/destinations", response_model=DestinationOut)
async def create_destination(data: DestinationCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Destination).where(Destination.id == data.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Destination ID already exists")

    dest = Destination(
        id=data.id, city=data.city, country=data.country, region=data.region,
        lat=data.lat, lng=data.lng, cost=data.cost,
        popularity=data.popularity, scenic_spots_count=data.scenic_spots_count,
        traffic_score=data.traffic_score, price_index=data.price_index,
        crowd_level=data.crowd_level, climate_score=data.climate_score,
        niche_score=data.niche_score,
        interests=json.dumps(data.interests, ensure_ascii=False),
        adcode=data.adcode, level=data.level, parent_adcode=data.parent_adcode,
        population_tier=data.population_tier, is_tourist_city=data.is_tourist_city,
    )
    db.add(dest)
    await db.commit()
    await db.refresh(dest)
    return DestinationOut.model_validate(dest)


@router.put("/destinations/{dest_id}", response_model=DestinationOut)
async def update_destination(dest_id: str, data: DestinationCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Destination).where(Destination.id == dest_id))
    dest = result.scalar_one_or_none()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")

    for field, value in data.model_dump(exclude={"id", "interests", "image_url"}, exclude_none=True).items():
        setattr(dest, field, value)
    dest.interests = json.dumps(data.interests, ensure_ascii=False)
    await db.commit()
    await db.refresh(dest)
    return DestinationOut.model_validate(dest)


@router.delete("/destinations/{dest_id}")
async def delete_destination(dest_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Destination).where(Destination.id == dest_id))
    dest = result.scalar_one_or_none()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")
    await db.delete(dest)
    await db.commit()
    return {"ok": True}


# ── Scenic Spot Management ──

@router.post("/spots", response_model=ScenicSpotOut)
async def create_spot(data: ScenicSpotCreate, db: AsyncSession = Depends(get_db)):
    spot = ScenicSpot(destination_id=data.destination_id, name=data.name, grade=data.grade)
    db.add(spot)
    await db.commit()
    await db.refresh(spot)
    return ScenicSpotOut.model_validate(spot)


@router.delete("/spots/{spot_id}")
async def delete_spot(spot_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScenicSpot).where(ScenicSpot.id == spot_id))
    spot = result.scalar_one_or_none()
    if not spot:
        raise HTTPException(status_code=404, detail="Scenic spot not found")
    await db.delete(spot)
    await db.commit()
    return {"ok": True}


# ── Holiday Management ──

@router.post("/holidays", response_model=HolidayOut)
async def create_holiday(data: HolidayCreate, db: AsyncSession = Depends(get_db)):
    holiday = Holiday(**data.model_dump())
    db.add(holiday)
    await db.commit()
    await db.refresh(holiday)
    return HolidayOut.model_validate(holiday)


@router.delete("/holidays/{holiday_id}")
async def delete_holiday(holiday_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Holiday).where(Holiday.id == holiday_id))
    holiday = result.scalar_one_or_none()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    await db.delete(holiday)
    await db.commit()
    return {"ok": True}


# ── User Management ──

@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [{"id": u.id, "username": u.username, "email": u.email, "is_admin": u.is_admin, "created_at": str(u.created_at)} for u in users]


@router.post("/users")
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=pwd_context.hash(data.password),
        is_admin=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "username": user.username, "email": user.email, "is_admin": user.is_admin, "created_at": str(user.created_at)}
