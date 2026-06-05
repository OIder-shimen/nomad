"""Import all Chinese cities/districts from AMap District API into the destinations table."""
import asyncio
import json
import sys

import httpx

from city_tiers import get_tier, get_interests, compute_scores
from database import init_db, async_session
from models.models import Destination

AMAP_KEY = "b4386ecc145fdb417bcc3dde5f52dfbb"
AMAP_DISTRICT_URL = "https://restapi.amap.com/v3/config/district"

# Original 12 curated cities — preserve their existing scores
CURATED: set[str] = {
    "beijing", "shanghai", "chengdu", "lijiang", "sanya",
    "xian", "guilin", "lhasa", "zhangjiajie", "xiamen", "harbin", "dunhuang",
}

CURATED_DATA: dict[str, dict] = {
    "beijing": {"id": "beijing", "city": "北京", "region": "华北", "lat": 39.90, "lng": 116.41, "cost": 1000, "popularity": 99, "scenic_spots_count": 238, "traffic_score": 98, "price_index": 120, "crowd_level": 95, "climate_score": 68, "niche_score": 3, "interests": ["历史文化", "城市探索", "美食体验"], "adcode": "110000", "level": "city", "is_tourist_city": True, "population_tier": "一线"},
    "shanghai": {"id": "shanghai", "city": "上海", "region": "华东", "lat": 31.23, "lng": 121.47, "cost": 1100, "popularity": 98, "scenic_spots_count": 180, "traffic_score": 99, "price_index": 135, "crowd_level": 92, "climate_score": 72, "niche_score": 5, "interests": ["城市探索", "美食体验", "休闲度假"], "adcode": "310000", "level": "city", "is_tourist_city": True, "population_tier": "一线"},
    "chengdu": {"id": "chengdu", "city": "成都", "region": "西南", "lat": 30.57, "lng": 104.07, "cost": 600, "popularity": 96, "scenic_spots_count": 155, "traffic_score": 85, "price_index": 62, "crowd_level": 75, "climate_score": 78, "niche_score": 18, "interests": ["美食体验", "休闲度假", "历史文化"], "adcode": "510100", "level": "city", "is_tourist_city": True, "population_tier": "新一线"},
    "lijiang": {"id": "lijiang", "city": "丽江", "region": "西南", "lat": 26.87, "lng": 100.23, "cost": 500, "popularity": 89, "scenic_spots_count": 42, "traffic_score": 38, "price_index": 45, "crowd_level": 62, "climate_score": 84, "niche_score": 58, "interests": ["自然风光", "历史文化", "休闲度假"], "adcode": "530700", "level": "city", "is_tourist_city": True, "population_tier": "三线"},
    "sanya": {"id": "sanya", "city": "三亚", "region": "华南", "lat": 18.25, "lng": 109.50, "cost": 900, "popularity": 91, "scenic_spots_count": 30, "traffic_score": 52, "price_index": 95, "crowd_level": 72, "climate_score": 92, "niche_score": 32, "interests": ["休闲度假", "自然风光", "美食体验"], "adcode": "460200", "level": "city", "is_tourist_city": True, "population_tier": "三线"},
    "xian": {"id": "xian", "city": "西安", "region": "西北", "lat": 34.34, "lng": 108.94, "cost": 550, "popularity": 95, "scenic_spots_count": 175, "traffic_score": 80, "price_index": 50, "crowd_level": 80, "climate_score": 65, "niche_score": 15, "interests": ["历史文化", "美食体验", "城市探索"], "adcode": "610100", "level": "city", "is_tourist_city": True, "population_tier": "新一线"},
    "guilin": {"id": "guilin", "city": "桂林", "region": "华南", "lat": 25.27, "lng": 110.28, "cost": 450, "popularity": 87, "scenic_spots_count": 76, "traffic_score": 48, "price_index": 38, "crowd_level": 58, "climate_score": 82, "niche_score": 62, "interests": ["自然风光", "户外探险", "休闲度假"], "adcode": "450300", "level": "city", "is_tourist_city": True, "population_tier": "三线"},
    "lhasa": {"id": "lhasa", "city": "拉萨", "region": "西南", "lat": 29.65, "lng": 91.13, "cost": 700, "popularity": 81, "scenic_spots_count": 48, "traffic_score": 20, "price_index": 60, "crowd_level": 25, "climate_score": 30, "niche_score": 92, "interests": ["历史文化", "自然风光", "户外探险"], "adcode": "540100", "level": "city", "is_tourist_city": True, "population_tier": "三线"},
    "zhangjiajie": {"id": "zhangjiajie", "city": "张家界", "region": "华中", "lat": 29.12, "lng": 110.48, "cost": 550, "popularity": 86, "scenic_spots_count": 35, "traffic_score": 42, "price_index": 42, "crowd_level": 55, "climate_score": 76, "niche_score": 65, "interests": ["自然风光", "户外探险", "休闲度假"], "adcode": "430800", "level": "city", "is_tourist_city": True, "population_tier": "三线"},
    "xiamen": {"id": "xiamen", "city": "厦门", "region": "华东", "lat": 24.48, "lng": 118.09, "cost": 700, "popularity": 88, "scenic_spots_count": 60, "traffic_score": 75, "price_index": 72, "crowd_level": 60, "climate_score": 86, "niche_score": 42, "interests": ["休闲度假", "美食体验", "城市探索"], "adcode": "350200", "level": "city", "is_tourist_city": True, "population_tier": "二线"},
    "harbin": {"id": "harbin", "city": "哈尔滨", "region": "东北", "lat": 45.80, "lng": 126.53, "cost": 500, "popularity": 84, "scenic_spots_count": 85, "traffic_score": 70, "price_index": 48, "crowd_level": 48, "climate_score": 22, "niche_score": 48, "interests": ["自然风光", "城市探索", "历史文化"], "adcode": "230100", "level": "city", "is_tourist_city": True, "population_tier": "二线"},
    "dunhuang": {"id": "dunhuang", "city": "敦煌", "region": "西北", "lat": 40.14, "lng": 94.66, "cost": 600, "popularity": 76, "scenic_spots_count": 25, "traffic_score": 28, "price_index": 38, "crowd_level": 22, "climate_score": 38, "niche_score": 95, "interests": ["历史文化", "户外探险", "自然风光"], "adcode": "620982", "level": "city", "is_tourist_city": True, "population_tier": "五线"},
}


def assign_region(province: str) -> str:
    region_map = {
        "黑龙江省": "东北", "吉林省": "东北", "辽宁省": "东北",
        "北京市": "华北", "天津市": "华北", "河北省": "华北", "山西省": "华北", "内蒙古自治区": "华北",
        "山东省": "华东", "江苏省": "华东", "上海市": "华东", "浙江省": "华东", "安徽省": "华东",
        "福建省": "华东", "江西省": "华东", "台湾省": "华东",
        "河南省": "华中", "湖北省": "华中", "湖南省": "华中",
        "广东省": "华南", "广西壮族自治区": "华南", "海南省": "华南", "香港特别行政区": "华南", "澳门特别行政区": "华南",
        "重庆市": "西南", "四川省": "西南", "贵州省": "西南", "云南省": "西南", "西藏自治区": "西南",
        "陕西省": "西北", "甘肃省": "西北", "青海省": "西北", "宁夏回族自治区": "西北", "新疆维吾尔自治区": "西北",
    }
    return region_map.get(province, "华中")


async def fetch_district_tree() -> list[dict]:
    """Fetch the full China district tree from AMap. Returns flat list of nodes."""
    print("Fetching district tree from AMap...")
    url = f"{AMAP_DISTRICT_URL}?keywords=中国&subdistrict=3&key={AMAP_KEY}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        data = resp.json()
        if data.get("status") != "1":
            print(f"AMap API error: {data.get('info')}")
            sys.exit(1)

    districts = data.get("districts", [])
    if not districts:
        print("No districts returned")
        sys.exit(1)

    china = districts[0]
    nodes = []

    def walk(entry, parent_adcode=None):
        adcode = entry.get("adcode", "")
        name = entry.get("name", "")
        level = entry.get("level", "")
        center = entry.get("center", "")

        if center:
            parts = center.split(",")
            lng, lat = float(parts[0]), float(parts[1])
        else:
            lng, lat = 0.0, 0.0

        # Map AMap level to our level
        level_map = {"province": "province", "city": "city", "district": "district"}
        our_level = level_map.get(level, level)

        if our_level in ("province", "city", "district"):
            nodes.append({
                "adcode": adcode,
                "name": name,
                "level": our_level,
                "parent_adcode": parent_adcode or "",
                "lat": lat,
                "lng": lng,
            })

        for child in entry.get("districts", []):
            walk(child, adcode or parent_adcode)

    walk(china)
    print(f"Parsed {len(nodes)} nodes from AMap district tree")
    return nodes


def generate_id(name: str, level: str, adcode: str) -> str:
    """Generate a unique ID from adcode."""
    if level == "province":
        return f"prov-{adcode[:2]}"
    return f"{level}-{adcode}"


async def import_cities():
    await init_db()
    nodes = await fetch_district_tree()

    # Build province lookup
    provinces = {}
    cities = []
    districts = []

    for n in nodes:
        if n["level"] == "province":
            provinces[n["adcode"]] = n["name"]
        elif n["level"] == "city":
            cities.append(n)
        elif n["level"] == "district":
            districts.append(n)

    print(f"  Provinces: {len(provinces)}")
    print(f"  Cities: {len(cities)}")
    print(f"  Districts: {len(districts)}")

    rows = []

    # First pass: build province adcode → name map for region assignment
    province_adcode_map = {}
    for n in nodes:
        if n["level"] == "province":
            province_adcode_map[n["adcode"]] = n["name"]

    def get_province_name(node):
        if node["level"] == "province":
            return node["name"]
        parent = node["parent_adcode"]
        # Parent adcode for cities is first 2 digits + 0000
        prov_adcode = parent[:2] + "0000" if len(parent) >= 2 else parent
        return province_adcode_map.get(prov_adcode, "")

    # Add provinces
    for n in nodes:
        if n["level"] != "province":
            continue
        name = n["name"]
        tier = get_tier(name)
        region = assign_region(name)
        scores = compute_scores(tier, name, name)
        interests = get_interests(name, region)
        row = Destination(
            id=generate_id(name, "province", n["adcode"]),
            city=name, country="中国", region=region,
            lat=n["lat"] or 35, lng=n["lng"] or 105,
            adcode=n["adcode"], level="province", parent_adcode="",
            population_tier=tier,
            interests=json.dumps(interests, ensure_ascii=False),
            **{k: v for k, v in scores.items() if k != "interests"},
        )
        rows.append(row)

    # Add cities
    for n in cities:
        province_name = get_province_name(n)
        name = n["name"]
        tier = get_tier(name)
        region = assign_region(province_name)
        # Strip common suffixes for matching (AMap returns "北京市"/"北京城区", curated uses "北京")
        match_name = name.replace("城区", "").replace("市辖区", "").rstrip("市")
        is_curated = match_name in {d["city"] for d in CURATED_DATA.values()}

        if is_curated:
            curated = next(v for v in CURATED_DATA.values() if v["city"] == match_name)
            row = Destination(
                id=curated["id"], city=name, country="中国", region=curated["region"],
                lat=curated["lat"], lng=curated["lng"],
                adcode=n["adcode"], level="city", parent_adcode=n["parent_adcode"],
                cost=curated["cost"], popularity=curated["popularity"],
                scenic_spots_count=curated["scenic_spots_count"],
                traffic_score=curated["traffic_score"], price_index=curated["price_index"],
                crowd_level=curated["crowd_level"], climate_score=curated["climate_score"],
                niche_score=curated["niche_score"],
                interests=json.dumps(curated["interests"], ensure_ascii=False),
                population_tier=curated["population_tier"],
                is_tourist_city=True,
            )
        else:
            scores = compute_scores(tier, province_name, name)
            interests = get_interests(name, region)
            row = Destination(
                id=generate_id(name, "city", n["adcode"]),
                city=name, country="中国", region=region,
                lat=n["lat"] or 30, lng=n["lng"] or 110,
                adcode=n["adcode"], level="city", parent_adcode=n["parent_adcode"],
                population_tier=tier,
                interests=json.dumps(interests, ensure_ascii=False),
                **{k: v for k, v in scores.items() if k != "interests"},
            )
        rows.append(row)

    # Add districts
    for n in districts:
        if not n["lat"] or not n["lng"]:
            continue
        region = assign_region(get_province_name(n))
        match_name = n["name"].replace("城区", "").replace("市辖区", "").rstrip("市")
        is_curated_district = match_name in {d["city"] for d in CURATED_DATA.values()}

        if is_curated_district:
            curated = next(v for v in CURATED_DATA.values() if v["city"] == match_name)
            row = Destination(
                id=curated["id"], city=n["name"], country="中国", region=curated["region"],
                lat=curated["lat"], lng=curated["lng"],
                adcode=n["adcode"], level="city", parent_adcode=n["parent_adcode"],
                cost=curated["cost"], popularity=curated["popularity"],
                scenic_spots_count=curated["scenic_spots_count"],
                traffic_score=curated["traffic_score"], price_index=curated["price_index"],
                crowd_level=curated["crowd_level"], climate_score=curated["climate_score"],
                niche_score=curated["niche_score"],
                interests=json.dumps(curated["interests"], ensure_ascii=False),
                population_tier=curated["population_tier"],
                is_tourist_city=True,
            )
        else:
            row = Destination(
                id=generate_id(n["name"], "district", n["adcode"]),
                city=n["name"], country="中国", region=region,
                lat=n["lat"], lng=n["lng"],
                adcode=n["adcode"], level="district", parent_adcode=n["parent_adcode"],
                cost=200, popularity=10, scenic_spots_count=2,
                traffic_score=30, price_index=30, crowd_level=20, climate_score=60, niche_score=80,
                interests=json.dumps(["城市探索", "自然风光"], ensure_ascii=False),
                population_tier="五线",
            )
        rows.append(row)

    # Bulk insert
    async with async_session() as session:
        # Insert in batches of 500
        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            session.add_all(batch)
            await session.commit()
            print(f"  Inserted {min(i + batch_size, len(rows))}/{len(rows)} rows")

    print(f"\nDone! Imported {len(rows)} destinations total.")
    print(f"  Provinces: {sum(1 for r in rows if r.level == 'province')}")
    print(f"  Cities: {sum(1 for r in rows if r.level == 'city')}")
    print(f"  Districts: {sum(1 for r in rows if r.level == 'district')}")


if __name__ == "__main__":
    asyncio.run(import_cities())
