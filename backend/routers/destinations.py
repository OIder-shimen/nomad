import json
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.models import Destination, ScenicSpot, Holiday
from routers.auth import get_current_user
from schemas.schemas import (
    DestinationOut, DestinationBrief, DestinationCreate, ScenicSpotCreate, ScenicSpotOut,
    HolidayOut, HolidayCreate, RecommendRequest,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


def _to_destination_out(dest: Destination, spots: list[ScenicSpot]) -> DestinationOut:
    return DestinationOut(
        id=dest.id, city=dest.city, country=dest.country, region=dest.region,
        currency=dest.currency, timezone=dest.timezone, lat=dest.lat, lng=dest.lng,
        cost=dest.cost, popularity=dest.popularity,
        scenic_spots_count=dest.scenic_spots_count,
        traffic_score=dest.traffic_score, price_index=dest.price_index,
        crowd_level=dest.crowd_level, climate_score=dest.climate_score,
        niche_score=dest.niche_score, interests=dest.interests,
        adcode=dest.adcode, level=dest.level, parent_adcode=dest.parent_adcode,
        population_tier=dest.population_tier, is_tourist_city=dest.is_tourist_city,
        image_url=dest.image_url,
        scenic_spots=[ScenicSpotOut.model_validate(s) for s in spots],
    )


# ── Internal helpers (reusable by chat_service) ──

async def search_destinations_internal(
    db: AsyncSession,
    q: str = "",
    region: str = "",
    level: str = "city",
    tier: str = "",
    interest: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict:
    stmt = select(Destination)
    if level:
        stmt = stmt.where(Destination.level == level)
    if q:
        stmt = stmt.where(
            Destination.city.ilike(f"%{q}%")
            | Destination.country.ilike(f"%{q}%")
            | Destination.region.ilike(f"%{q}%")
        )
    if region:
        stmt = stmt.where(Destination.region == region)
    if tier:
        stmt = stmt.where(Destination.population_tier == tier)
    if interest:
        stmt = stmt.where(Destination.interests.ilike(f"%{interest}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(Destination.popularity.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    destinations = result.scalars().all()

    items = [DestinationBrief.model_validate(d).model_dump() for d in destinations]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def get_destination_internal(db: AsyncSession, dest_id: str) -> DestinationOut | None:
    stmt = select(Destination).options(selectinload(Destination.scenic_spots)).where(Destination.id == dest_id)
    result = await db.execute(stmt)
    d = result.unique().scalar_one_or_none()
    if not d:
        return None
    return _to_destination_out(d, d.scenic_spots)


async def get_holidays_internal(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(Holiday).order_by(Holiday.start_date))
    holidays = result.scalars().all()
    return [
        {"name": h.name, "start_date": h.start_date, "end_date": h.end_date, "crowd_boost": h.crowd_boost}
        for h in holidays
    ]


DIMENSION_LABELS = {
    "climate_match":      {"label": "气候匹配度",   "color": "#7ba58d"},
    "budget_fit":         {"label": "预算适配度",   "color": "#c9a44b"},
    "interest_align":     {"label": "兴趣契合度",   "color": "#c97a5b"},
    "traffic_convenience":{"label": "交通便利度",   "color": "#6b8fbf"},
    "crowd_avoidance":    {"label": "客流避让度",   "color": "#b87c9b"},
    "scenic_density":     {"label": "景区丰度",     "color": "#8b9e7c"},
    "air_quality":        {"label": "空气质量",     "color": "#6bbf8b"},
}

INTEREST_TO_DEST = {
    "自然风光": ["guilin", "lijiang", "zhangjiajie", "sanya", "harbin", "lhasa", "dunhuang"],
    "历史文化": ["beijing", "xian", "dunhuang", "lhasa", "lijiang", "chengdu", "harbin"],
    "美食体验": ["chengdu", "beijing", "xian", "shanghai", "xiamen", "sanya"],
    "户外探险": ["zhangjiajie", "guilin", "lhasa", "dunhuang"],
    "休闲度假": ["sanya", "lijiang", "xiamen", "chengdu", "guilin", "shanghai"],
    "城市探索": ["shanghai", "beijing", "xian", "chengdu", "xiamen", "harbin"],
}


def _normalize(value, mn, mx):
    return max(0, min(1, (value - mn) / (mx - mn) if mx != mn else 0.5))


def _sigmoid(x):
    return 1 / (1 + math.exp(-x))


def _get_holiday_impact(holidays):
    from datetime import date
    today = date.today()
    today_str = today.isoformat()
    for h in holidays:
        if isinstance(h, dict):
            h_start, h_end, h_name, h_boost = h["start_date"], h["end_date"], h["name"], h["crowd_boost"]
        else:
            h_start, h_end, h_name, h_boost = h.start_date, h.end_date, h.name, h.crowd_boost
        if h_start <= today_str <= h_end:
            return {"isHoliday": True, "name": h_name, "crowdBoost": h_boost}
        start = date.fromisoformat(h_start)
        end = date.fromisoformat(h_end)
        if abs((today - start).days) <= 3 or abs((today - end).days) <= 3:
            dist = min(abs((today - start).days), abs((today - end).days))
            factor = 1 if dist <= 1 else 0.6 if dist <= 3 else 0.3
            return {"isHoliday": True, "name": h_name, "crowdBoost": round(h_boost * factor)}
    return {"isHoliday": False, "name": "", "crowdBoost": 0}


async def compute_recommendations_internal(
    db: AsyncSession, budget: int, interests: list[str], style: str, climate: str
) -> dict:
    result = await db.execute(select(Destination).where(Destination.level == "city"))
    destinations = result.scalars().all()

    holidays = await get_holidays_internal(db)

    if not destinations:
        return {"top": None, "runners": [], "niche": [], "all": []}

    costs = [d.cost for d in destinations]
    spots_list = [d.scenic_spots_count for d in destinations]
    cost_min, cost_max = min(costs), max(costs)
    spots_max = max(spots_list)
    holiday = _get_holiday_impact(holidays)

    scored = []
    for d in destinations:
        interests_list = json.loads(d.interests) if isinstance(d.interests, str) else (d.interests or [])

        climate_match = _normalize(d.climate_score, 0, 100)
        raw_budget = 1 - abs(d.cost - budget) / max(budget, cost_max)
        budget_fit = _sigmoid(raw_budget * 6 - 3)

        interest_hits = 0
        for tag in interests:
            if tag in interests_list:
                interest_hits += 1
            if (INTEREST_TO_DEST.get(tag, [])).count(d.id):
                interest_hits += 0.5
        interest_align = _normalize(interest_hits, 0, len(interests) * 1.5)

        traffic = d.traffic_score / 100
        crowd_adj = min(100, d.crowd_level + holiday["crowdBoost"])
        crowd_avoid = 1 - (crowd_adj / 100)
        scenic = d.scenic_spots_count / spots_max if spots_max > 0 else 0
        air_quality = 0.7

        w_interest = 0.22
        w_budget = 0.18
        w_climate = 0.18
        w_crowd = 0.12
        w_traffic = 0.10
        w_scenic = 0.10
        w_aqi = 0.10

        if style == "背包穷游":
            w_budget += 0.08; w_crowd += 0.05
        elif style == "舒适休闲":
            w_scenic += 0.05; w_crowd += 0.05
        elif style == "奢华体验":
            w_scenic += 0.05; w_budget -= 0.05
        elif style == "亲子家庭":
            w_traffic += 0.05; w_crowd += 0.05; w_aqi += 0.03

        niche_boost = 0
        if "户外探险" in interests or "自然风光" in interests:
            niche_boost = d.niche_score / 100 * 0.12

        overall = (
            climate_match * w_climate +
            budget_fit * w_budget +
            interest_align * w_interest +
            traffic * w_traffic +
            crowd_avoid * w_crowd +
            scenic * w_scenic +
            air_quality * w_aqi +
            niche_boost
        )

        dims = {
            "climate_match": round(climate_match * 100),
            "budget_fit": round(budget_fit * 100),
            "interest_align": round(interest_align * 100),
            "traffic_convenience": round(traffic * 100),
            "crowd_avoidance": round(crowd_avoid * 100),
            "scenic_density": round(scenic * 100),
            "air_quality": round(air_quality * 100),
        }

        reasons = []
        if interest_align > 0.7:
            reasons.append(f"与您的兴趣标签匹配")
        if budget_fit > 0.7:
            reasons.append(f"日均消费 ¥{d.cost} 在您的预算范围内")
        if climate_match > 0.7:
            reasons.append("当前气候条件与您的偏好吻合")
        if crowd_avoid > 0.6:
            reasons.append("预测客流适中，可避开拥挤")
        if scenic > 0.6:
            reasons.append(f"拥有 {d.scenic_spots_count} 个以上A级景区")
        if d.niche_score > 60:
            reasons.append("算法挖掘的小众宝藏目的地")
        if holiday["isHoliday"]:
            reasons.append(f"{holiday['name']}期间客流可能增加，建议提前预订")
        if not reasons:
            reasons.append("综合多项指标表现均衡")

        scored.append({
            "dest": {
                "id": d.id, "city": d.city, "country": d.country, "region": d.region,
                "lat": d.lat, "lng": d.lng, "cost": d.cost,
                "popularity": d.popularity, "trafficScore": d.traffic_score,
                "crowdLevel": d.crowd_level, "climateScore": d.climate_score,
                "nicheScore": d.niche_score, "scenicSpots": d.scenic_spots_count,
                "interests": interests_list,
            },
            "overallScore": overall,
            "confidence": round(overall * 100),
            "holiday": holiday,
            "dimensions": dims,
            "matchReasons": reasons[:3],
        })

    scored.sort(key=lambda x: x["overallScore"], reverse=True)

    return {
        "top": scored[0] if scored else None,
        "runners": scored[1:5],
        "niche": [s for s in scored if s["dest"]["popularity"] < 90][:2],
        "all": scored,
    }


# ── REST Endpoints (thin wrappers) ──

@router.get("/", response_model=dict)
async def list_destinations(
    q: str = Query(default=""),
    region: str = Query(default=""),
    level: str = Query(default="city"),
    tier: str = Query(default=""),
    interest: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await search_destinations_internal(db, q=q, region=region, level=level, tier=tier, interest=interest, limit=limit, offset=offset)


@router.get("/hierarchy")
async def get_hierarchy(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Destination).where(Destination.level.in_(["province", "city"]))
    )
    rows = result.scalars().all()

    provinces = [r for r in rows if r.level == "province"]
    cities = [r for r in rows if r.level == "city"]

    tree = []
    for p in sorted(provinces, key=lambda x: x.city):
        pcities = []
        for c in cities:
            if c.parent_adcode and c.parent_adcode.startswith(p.adcode[:2] if p.adcode else ""):
                pcities.append({
                    "id": c.id, "name": c.city, "adcode": c.adcode,
                    "tier": c.population_tier, "popularity": c.popularity,
                    "is_tourist_city": c.is_tourist_city,
                })
        tree.append({
            "id": p.id, "name": p.city, "adcode": p.adcode,
            "cities": sorted(pcities, key=lambda x: -x["popularity"]),
        })

    return tree


@router.get("/{dest_id}", response_model=DestinationOut)
async def get_destination(dest_id: str, db: AsyncSession = Depends(get_db)):
    d = await get_destination_internal(db, dest_id)
    if not d:
        raise HTTPException(status_code=404, detail="Destination not found")
    return d


@router.get("/{dest_id}/spots", response_model=list[ScenicSpotOut])
async def list_spots(dest_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScenicSpot).where(ScenicSpot.destination_id == dest_id)
    )
    return [ScenicSpotOut.model_validate(s) for s in result.scalars().all()]


@router.get("/holidays/list", response_model=list[HolidayOut])
async def list_holidays(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Holiday).order_by(Holiday.start_date))
    return [HolidayOut.model_validate(h) for h in result.scalars().all()]


@router.post("/recommend")
async def recommend(req: RecommendRequest, db: AsyncSession = Depends(get_db)):
    return await compute_recommendations_internal(db, req.budget, req.interests, req.style, req.climate)
