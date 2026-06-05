from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.models import User, SavedItinerary
from schemas.schemas import (
    UserCreate, UserLogin, UserOut, TokenOut,
    SavedItineraryCreate, SavedItineraryOut,
)

MAX_USERS = 20

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def create_token(user_id: int, username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="无效的认证令牌")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


@router.post("/register")
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Public registration endpoint — capped at MAX_USERS."""
    total = (await db.execute(select(func.count(User.id)))).scalar() or 0
    if total >= MAX_USERS:
        raise HTTPException(status_code=403, detail=f"注册名额已满（限制{MAX_USERS}人），无法注册新用户")

    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少需要6位")
    user = User(
        username=data.username,
        email=data.email or "",
        hashed_password=pwd_context.hash(data.password),
        is_admin=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_token(user.id, user.username)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/slots")
async def registration_slots(db: AsyncSession = Depends(get_db)):
    """Returns remaining registration slots."""
    total = (await db.execute(select(func.count(User.id)))).scalar() or 0
    return {"total": MAX_USERS, "used": total, "remaining": max(0, MAX_USERS - total)}


@router.post("/login", response_model=TokenOut)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user or not pwd_context.verify(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_token(user.id, user.username)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


# ── Saved Itineraries ──

@router.get("/itineraries", response_model=list[SavedItineraryOut])
async def list_itineraries(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedItinerary)
        .where(SavedItinerary.user_id == current_user.id)
        .order_by(SavedItinerary.updated_at.desc())
    )
    return [SavedItineraryOut.model_validate(r) for r in result.scalars().all()]


@router.post("/itineraries", response_model=SavedItineraryOut)
async def save_itinerary(
    data: SavedItineraryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import json
    itinerary = SavedItinerary(
        user_id=current_user.id,
        name=data.name,
        trip_start_date=data.trip_start_date,
        stops=json.dumps([s.model_dump() for s in data.stops], ensure_ascii=False),
    )
    db.add(itinerary)
    await db.commit()
    await db.refresh(itinerary)
    return SavedItineraryOut.model_validate(itinerary)


@router.delete("/itineraries/{itinerary_id}")
async def delete_itinerary(
    itinerary_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedItinerary).where(
            SavedItinerary.id == itinerary_id,
            SavedItinerary.user_id == current_user.id,
        )
    )
    itinerary = result.scalar_one_or_none()
    if not itinerary:
        raise HTTPException(status_code=404, detail="行程不存在")
    await db.delete(itinerary)
    await db.commit()
    return {"ok": True}
