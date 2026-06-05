"""
API Proxy — third-party API keys stay server-side.
Frontend calls /api/proxy/* instead of directly hitting external APIs.
"""
import time
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from urllib.parse import urlparse

from config import settings
from routers.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

# Simple in-memory image cache (URL → (content, content_type, expiry))
_image_cache: dict[str, tuple[bytes, str, float]] = {}
_IMAGE_CACHE_TTL = 86400  # 24 hours
_MAX_CACHE_ENTRIES = 200


# ── Open-Meteo: Weather (no key needed, but proxy for consistency) ──
@router.get("/weather")
async def proxy_weather(lat: float = Query(...), lng: float = Query(...)):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current_weather=true"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Weather API unavailable")
        return resp.json()


# ── Open-Meteo: Air Quality (no key needed) ──
@router.get("/air-quality")
async def proxy_air_quality(lat: float = Query(...), lng: float = Query(...)):
    url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lng}&current=pm2_5,pm10,european_aqi"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Air Quality API unavailable")
        return resp.json()


# ── Frankfurter: Exchange Rates ──
@router.get("/exchange-rates")
async def proxy_exchange_rates():
    url = "https://api.frankfurter.app/latest?from=CNY"
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Exchange rate API unavailable")
        return resp.json()


# ── OSM Overpass: Transport Infrastructure ──
@router.get("/osm-transport")
async def proxy_osm_transport(lat: float = Query(...), lng: float = Query(...)):
    query = f"[out:json][timeout:10];(node[railway=station](around:10000,{lat},{lng});node[aeroway=aerodrome](around:50000,{lat},{lng});node[public_transport=station](around:10000,{lat},{lng}););out count;"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://overpass-api.de/api/interpreter",
            content=query,
            headers={
                "Content-Type": "text/plain",
                "Accept": "application/json",
                "User-Agent": "NomadTravelPlanner/1.0",
            },
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="OSM Overpass API unavailable")
        return resp.json()


# ── Unsplash: Destination Images (key required, proxied) ──
@router.get("/unsplash-photo")
async def proxy_unsplash_photo(query: str = Query(...)):
    if not settings.unsplash_access_key:
        raise HTTPException(status_code=503, detail="Unsplash API key not configured")
    url = f"https://api.unsplash.com/search/photos?query={query}&orientation=landscape&per_page=1"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Client-ID {settings.unsplash_access_key}"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Unsplash API unavailable")
        return resp.json()


# ── Geoapify: Local Attractions (key required, proxied) ──
@router.get("/geoapify-places")
async def proxy_geoapify_places(
    lat: float = Query(...), lng: float = Query(...),
    categories: str = Query(default="tourism.sights"),
    limit: int = Query(default=5),
):
    if not settings.geoapify_api_key:
        raise HTTPException(status_code=503, detail="Geoapify API key not configured")
    url = (
        f"https://api.geoapify.com/v2/places"
        f"?categories={categories}"
        f"&filter=circle:{lng},{lat},5000"
        f"&limit={limit}"
        f"&apiKey={settings.geoapify_api_key}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Geoapify API unavailable")
        return resp.json()


# ── AMap / 高德地图: POI, Around, Weather (key required, proxied) ──

@router.get("/amap-around")
async def proxy_amap_around(
    lat: float = Query(...), lng: float = Query(...),
    radius: int = Query(default=5000),
    limit: int = Query(default=10),
):
    if not settings.amap_web_api_key:
        raise HTTPException(status_code=503, detail="AMap API key not configured")
    url = (
        f"https://restapi.amap.com/v3/place/around"
        f"?location={lng},{lat}&radius={radius}&offset={limit}"
        f"&keywords=旅游景点|风景名胜|公园"
        f"&key={settings.amap_web_api_key}&extensions=all"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="AMap Around API unavailable")
        data = resp.json()
        if data.get("status") != "1":
            raise HTTPException(status_code=502, detail=f"AMap error: {data.get('info')}")
        return data


@router.get("/amap-poi")
async def proxy_amap_poi(
    keywords: str = Query(default="旅游景点"),
    city: str = Query(...),  # adcode
):
    if not settings.amap_web_api_key:
        raise HTTPException(status_code=503, detail="AMap API key not configured")
    url = (
        f"https://restapi.amap.com/v3/place/text"
        f"?keywords={keywords}&city={city}&citylimit=true"
        f"&offset=10&page=1&key={settings.amap_web_api_key}&extensions=all"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="AMap POI API unavailable")
        return resp.json()


@router.get("/amap-weather")
async def proxy_amap_weather(city: str = Query(...)):  # adcode
    if not settings.amap_web_api_key:
        raise HTTPException(status_code=503, detail="AMap API key not configured")
    url = (
        f"https://restapi.amap.com/v3/weather/weatherInfo"
        f"?city={city}&key={settings.amap_web_api_key}&extensions=base"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="AMap Weather API unavailable")
        return resp.json()


# ── AMap / 高德地图: Geocoding (key required) ──

@router.get("/geocode-search")
async def proxy_geocode_search(q: str = Query(...), limit: int = Query(default=5)):
    if not settings.amap_web_api_key:
        raise HTTPException(status_code=503, detail="AMap API key not configured")
    url = (
        f"https://restapi.amap.com/v3/assistant/inputtips"
        f"?keywords={q}&datatype=all"
        f"&key={settings.amap_web_api_key}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="AMap Geocode API unavailable")
        data = resp.json()
        if data.get("status") != "1":
            raise HTTPException(status_code=502, detail=f"AMap error: {data.get('info')}")
        tips = data.get("tips", [])
        results = []
        for t in tips[:limit]:
            loc = t.get("location", "")
            lng, lat = (loc.split(",") + ["0", "0"])[:2] if loc else ("0", "0")
            results.append({
                "name": t.get("name", ""),
                "district": t.get("district", ""),
                "address": t.get("address", ""),
                "lat": float(lat),
                "lng": float(lng),
            })
        return results


@router.get("/geocode-reverse")
async def proxy_geocode_reverse(lat: float = Query(...), lng: float = Query(...)):
    if not settings.amap_web_api_key:
        raise HTTPException(status_code=503, detail="AMap API key not configured")
    url = (
        f"https://restapi.amap.com/v3/geocode/regeo"
        f"?location={lng},{lat}&extensions=base"
        f"&key={settings.amap_web_api_key}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="AMap Regeo API unavailable")
        data = resp.json()
        if data.get("status") != "1":
            raise HTTPException(status_code=502, detail=f"AMap error: {data.get('info')}")
        regeo = data.get("regeocode", {})
        addr = regeo.get("addressComponent", {})
        return {
            "address": regeo.get("formatted_address", ""),
            "province": addr.get("province", ""),
            "city": addr.get("city", "") or addr.get("province", ""),
            "district": addr.get("district", ""),
        }


# ── Image Proxy (bypass GFW blocking of Unsplash CDN) ──

@router.get("/image")
async def proxy_image(url: str = Query(...)):
    """Proxy an image through our server so it loads even if CDN is blocked."""
    parsed = urlparse(url)
    if parsed.netloc not in ("images.unsplash.com", "plus.unsplash.com"):
        raise HTTPException(status_code=400, detail="Only Unsplash CDN images allowed")

    # Check cache
    now = time.time()
    cached = _image_cache.get(url)
    if cached and cached[2] > now:
        content, content_type, _ = cached
        return StreamingResponse(
            iter([content]), media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Image fetch failed")
        content = resp.content
        content_type = resp.headers.get("content-type", "image/jpeg")

        # Store in cache (evict oldest if over limit)
        if len(_image_cache) >= _MAX_CACHE_ENTRIES:
            oldest = min(_image_cache, key=lambda k: _image_cache[k][2])
            del _image_cache[oldest]
        _image_cache[url] = (content, content_type, now + _IMAGE_CACHE_TTL)

        return StreamingResponse(
            iter([content]), media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )
