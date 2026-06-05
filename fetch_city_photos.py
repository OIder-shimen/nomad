"""
Fetch Unsplash photos for all Chinese cities and update destinations-photos.js.
Supports batched execution to stay within 50 req/hr API limit.

Usage:
  python fetch_city_photos.py            # fetch all (may take hours)
  python fetch_city_photos.py 0 25       # batch: cities 0-24
  python fetch_city_photos.py 25 50      # next batch
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse

UNSPLASH_KEY = "OKB5oL2NfsMAZkJwHoE41mRfzK0Sk7_6n1OY2RMr2JI"
PER_QUERY = 10
TARGET_PER_CITY = 3
OUTPUT = os.path.join(os.path.dirname(__file__), "destinations-photos.js")
ALL_CITIES = os.path.join(os.path.dirname(__file__), "backend", "all_cities.json")


def load_cities(batch_start=0, batch_end=None):
    """Load city data from all_cities.json, return [(id, city, region), ...] sorted by popularity."""
    with open(ALL_CITIES, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", [])
    items.sort(key=lambda c: c.get("popularity", 0), reverse=True)
    if batch_end is None:
        batch_end = len(items)
    cities = []
    for c in items[batch_start:batch_end]:
        city_name = c["city"]
        region = c.get("region", "")
        cities.append((c["id"], city_name, region))
    return cities


def load_existing_photos():
    """Load existing destinationPhotos from destinations-photos.js if it exists."""
    if not os.path.exists(OUTPUT):
        return {}
    with open(OUTPUT, "r", encoding="utf-8") as f:
        content = f.read()
    # Extract JSON between "const destinationPhotos = " and the trailing ";"
    prefix = "const destinationPhotos = "
    start = content.find(prefix)
    if start < 0:
        return {}
    start += len(prefix)
    end = content.rfind(";")
    if end < 0:
        end = len(content)
    try:
        return json.loads(content[start:end].strip())
    except json.JSONDecodeError:
        return {}


def search_photos(query, per_page=10):
    url = (
        f"https://api.unsplash.com/search/photos"
        f"?query={urllib.parse.quote(query)}"
        f"&orientation=landscape"
        f"&per_page={per_page}"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return data.get("results", [])


def build_photo(p):
    return {
        "id": p["id"],
        "url": p["urls"]["regular"],
        "fullUrl": p["urls"]["full"],
        "thumb": p["urls"]["thumb"],
        "desc": (p.get("description") or p.get("alt_description") or ""),
        "author": p["user"]["name"],
        "authorUrl": p["user"]["links"]["html"] + "?utm_source=nomad&utm_medium=referral",
        "width": p["width"],
        "height": p["height"],
        "blurHash": p.get("blur_hash", ""),
        "likes": p.get("likes", 0),
        "color": p.get("color", ""),
    }


def main():
    batch_start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    batch_end = int(sys.argv[2]) if len(sys.argv) > 2 else None

    cities = load_cities(batch_start, batch_end)
    print(f"Batch: cities {batch_start}-{batch_end or 'ALL'} ({len(cities)} cities)")

    # Load existing photos to avoid re-fetching
    existing = load_existing_photos()
    print(f"Existing photos: {len(existing)} cities already have data")

    output = dict(existing)  # copy existing
    total_requests = 0

    for dest_id, city_name, region in cities:
        # Skip if already has enough photos
        if dest_id in existing and len(existing[dest_id]) >= TARGET_PER_CITY:
            print(f"  {city_name:10s} SKIP (already has {len(existing[dest_id])} photos)")
            continue

        queries = [
            f"{city_name} China travel",
            f"{city_name} {region} landmark"
        ]

        all_photos = []
        seen = set()
        existing_ids = {p["id"] for p in existing.get(dest_id, [])}
        seen.update(existing_ids)

        for qi, query in enumerate(queries):
            if total_requests >= 48:  # stop before hitting 50/hr limit
                print(f"  HIT RATE LIMIT ({total_requests} requests), stopping batch")
                break

            print(f"  {city_name:10s} [{qi+1}/2] \"{query}\" ... ", end="", flush=True)
            try:
                photos = search_photos(query, per_page=PER_QUERY)
                new_count = 0
                for p in photos:
                    if p["id"] not in seen:
                        seen.add(p["id"])
                        all_photos.append(p)
                        new_count += 1
                print(f"{new_count} new ({len(all_photos)} total)")
                total_requests += 1
            except Exception as e:
                print(f"FAILED: {e}")
            time.sleep(1.5)

        if all_photos:
            all_photos.sort(key=lambda p: p.get("likes", 0) or 0, reverse=True)
            # Merge with existing
            merged = existing.get(dest_id, []) + [build_photo(p) for p in all_photos]
            # Dedup by id, keeping order
            seen_ids = set()
            unique = []
            for p in merged:
                if p["id"] not in seen_ids:
                    seen_ids.add(p["id"])
                    unique.append(p)
            output[dest_id] = unique[:TARGET_PER_CITY * 3]  # keep more than target for cycling
            print(f"  => {len(output[dest_id])} photos total")

        if total_requests >= 48:
            break

    # Report
    print(f"\n{'='*55}")
    print(f"API requests this batch: {total_requests}")
    cities_with = sum(1 for v in output.values() if v)
    total_photos = sum(len(v) for v in output.values())
    print(f"Cities with photos: {cities_with} / {len(output)}")
    print(f"Total photos: {total_photos}")
    print(f"{'='*55}")

    # Generate JS
    lines = [
        "// Auto-generated by fetch_city_photos.py",
        f"// Unsplash API — photos for {cities_with} Chinese destinations",
        f"// Generated photos per destination: { {k: len(v) for k, v in sorted(output.items()) if v} }",
        "",
        "const destinationPhotos = " + json.dumps(output, ensure_ascii=False, indent=2) + ";",
        "",
    ]
    js_content = "\n".join(lines)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(js_content)

    size_kb = len(js_content.encode("utf-8")) / 1024
    print(f"\nOutput: {OUTPUT} ({size_kb:.0f} KB)")
    print("Done!")


if __name__ == "__main__":
    main()
