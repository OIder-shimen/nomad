"""
Generate all-destinations.js from backend/all_cities.json.
Maps 371 cities from backend format to frontend JS format.
Run once; re-run when all_cities.json is updated.
"""
import json
import os
from datetime import datetime

SRC = os.path.join(os.path.dirname(__file__), "backend", "all_cities.json")
OUTPUT = os.path.join(os.path.dirname(__file__), "all-destinations.js")

REGION_MAP = {
    "华北": "华北", "东北": "东北", "华东": "华东",
    "华中": "华中", "华南": "华南", "西南": "西南", "西北": "西北",
    "北京": "华北", "天津": "华北", "河北": "华北", "山西": "华北", "内蒙古": "华北",
    "辽宁": "东北", "吉林": "东北", "黑龙江": "东北",
    "上海": "华东", "江苏": "华东", "浙江": "华东", "安徽": "华东", "福建": "华东", "江西": "华东", "山东": "华东",
    "河南": "华中", "湖北": "华中", "湖南": "华中",
    "广东": "华南", "广西": "华南", "海南": "华南",
    "重庆": "西南", "四川": "西南", "贵州": "西南", "云南": "西南", "西藏": "西南",
    "陕西": "西北", "甘肃": "西北", "青海": "西北", "宁夏": "西北", "新疆": "西北",
}


def region_from_city(city_name, default_region):
    """Normalize region names."""
    if default_region in REGION_MAP:
        return REGION_MAP[default_region]
    return default_region or "华东"


def compute_annual_visitors(popularity, is_tourist_city, scenic_count, pop_tier):
    """Estimate annual visitors (万人) from city attributes.

    Calibrated against 2024 Chinese tourism data:
    - Beijing (pop=99): ~31000万
    - Chengdu (pop=96): ~27000万
    - Mid cities (pop=50): ~5000万
    - Small cities (pop=10): ~200万
    """
    pop = max(popularity, 1)
    base = pop * pop * 2.2
    if is_tourist_city:
        base *= 1.18
    if scenic_count > 100:
        base *= 1.12
    elif scenic_count > 50:
        base *= 1.08
    elif scenic_count > 20:
        base *= 1.04
    tier_boost = {"一线": 1.15, "新一线": 1.08, "二线": 1.0, "三线": 0.85, "四线": 0.7, "五线": 0.5}
    base *= tier_boost.get(pop_tier, 0.75)
    return round(base / 100) * 100  # round to nearest 100万


def compute_ytd_visitors(annual):
    """Compute year-to-date visitors (up to current month)."""
    month = datetime.now().month
    # Seasonal weights by month: Jan=5%, Feb=6%, ..., Dec=6%
    seasonal = [0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.10, 0.09, 0.07, 0.06]
    ytd_ratio = sum(seasonal[:month])
    return round(annual * ytd_ratio / 100) * 100


def main():
    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    print(f"Read {len(items)} cities from {SRC}")

    destinations = []
    adcode_map = {}
    scenic_spots_map = {}

    for c in items:
        # Parse interests from JSON string to array
        interests_raw = c.get("interests", "[]")
        if isinstance(interests_raw, str):
            try:
                interests = json.loads(interests_raw)
            except json.JSONDecodeError:
                interests = []
        elif isinstance(interests_raw, list):
            interests = interests_raw
        else:
            interests = []

        # Compute tourist visitor data
        pop_tier = c.get("population_tier", "")
        is_tourist = c.get("is_tourist_city", False)
        scenic_count = c.get("scenic_spots_count", 0)
        popularity = c.get("popularity", 0)
        annual_visitors = compute_annual_visitors(popularity, is_tourist, scenic_count, pop_tier)
        ytd_visitors = compute_ytd_visitors(annual_visitors)

        # Map fields
        dest = {
            "id": c["id"],
            "city": c["city"],
            "country": c.get("country", "中国"),
            "region": region_from_city(c["city"], c.get("region", "")),
            "currency": c.get("currency", "CNY"),
            "rate": 1,
            "timezone": c.get("timezone", "UTC+8"),
            "lat": c["lat"],
            "lng": c["lng"],
            "weather": {"temp": 20, "condition": "晴", "icon": "☀"},  # placeholder, live-data fills later
            "cost": c.get("cost", 500),
            "popularity": popularity,
            "annualVisitors": annual_visitors,  # 年度游客量（万人）
            "ytdVisitors": ytd_visitors,  # 今年截至本月游客量（万人）
            "scenicSpots": scenic_count,
            "trafficScore": c.get("traffic_score", 50),
            "trafficScore": c.get("traffic_score", 50),
            "priceIndex": c.get("price_index", 100),
            "crowdLevel": c.get("crowd_level", 50),
            "climateScore": c.get("climate_score", 50),
            "nicheScore": c.get("niche_score", 0),
            "interests": interests,
            "isTouristCity": c.get("is_tourist_city", False),
        }
        destinations.append(dest)

        # Adcode map
        adcode = c.get("adcode")
        if adcode:
            adcode_map[c["id"]] = adcode

        # Scenic spots
        spots = c.get("scenic_spots", [])
        if spots:
            scenic_spots_map[c["id"]] = spots

    # Sort by popularity descending
    destinations.sort(key=lambda d: d["popularity"], reverse=True)

    # Generate JS
    dest_json = json.dumps(destinations, ensure_ascii=False, indent=2)
    adcode_json = json.dumps(adcode_map, ensure_ascii=False, indent=2)
    spots_json = json.dumps(scenic_spots_map, ensure_ascii=False, indent=2)

    js_content = f"""// Auto-generated by generate_destinations_js.py
// Source: backend/all_cities.json — {len(destinations)} Chinese cities
// Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}

const ALL_DESTINATIONS = {dest_json};

const ALL_AMAP_ADCODE = {adcode_json};

const ALL_SCENIC_SPOTS = {spots_json};
"""

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(js_content)

    size_kb = len(js_content.encode("utf-8")) / 1024
    total_spots = sum(len(v) for v in scenic_spots_map.values())
    print(f"Output: {OUTPUT} ({size_kb:.0f} KB)")
    print(f"  {len(destinations)} cities")
    print(f"  {len(adcode_map)} adcode mappings")
    print(f"  {total_spots} scenic spots across {len(scenic_spots_map)} cities")
    print("Done!")


if __name__ == "__main__":
    main()
