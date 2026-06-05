"""Chinese city population tier classification (source: 第一财经·新一线城市研究所)."""

CITY_TIERS: dict[str, str] = {
    # 一线城市 (4)
    "北京市": "一线", "上海市": "一线", "广州市": "一线", "深圳市": "一线",
    # 新一线城市 (15)
    "成都市": "新一线", "杭州市": "新一线", "重庆市": "新一线", "武汉市": "新一线",
    "西安市": "新一线", "苏州市": "新一线", "天津市": "新一线", "南京市": "新一线",
    "长沙市": "新一线", "郑州市": "新一线", "东莞市": "新一线", "青岛市": "新一线",
    "沈阳市": "新一线", "宁波市": "新一线", "昆明市": "新一线",
    # 二线城市 (30)
    "无锡市": "二线", "佛山市": "二线", "合肥市": "二线", "福州市": "二线",
    "厦门市": "二线", "哈尔滨市": "二线", "济南市": "二线", "温州市": "二线",
    "南宁市": "二线", "长春市": "二线", "泉州市": "二线", "石家庄市": "二线",
    "贵阳市": "二线", "南昌市": "二线", "金华市": "二线", "常州市": "二线",
    "南通市": "二线", "嘉兴市": "二线", "太原市": "二线", "徐州市": "二线",
    "惠州市": "二线", "珠海市": "二线", "中山市": "二线", "台州市": "二线",
    "烟台市": "二线", "兰州市": "二线", "绍兴市": "二线", "海口市": "二线",
    "乌鲁木齐市": "二线", "呼和浩特市": "二线",
    # 三线城市 (~70) — key tourist destinations and provincial capitals
    "三亚市": "三线", "桂林市": "三线", "丽江市": "三线", "拉萨市": "三线",
    "张家界市": "三线", "敦煌市": "三线", "黄山市": "三线", "大理市": "三线",
    "遵义市": "三线", "宜昌市": "三线", "九江市": "三线", "洛阳市": "三线",
    "开封市": "三线", "秦皇岛市": "三线", "威海市": "三线", "日照市": "三线",
    "连云港市": "三线", "扬州市": "三线", "镇江市": "三线", "芜湖市": "三线",
    "洛阳市": "三线", "岳阳市": "三线", "柳州市": "三线", "绵阳市": "三线",
    "洛阳市": "三线", "吉林市": "三线", "大庆市": "三线", "包头市": "三线",
    "洛阳市": "三线", "赣州市": "三线", "唐山市": "三线", "汕头市": "三线",
    "江门市": "三线", "湛江市": "三线", "肇庆市": "三线", "泰安市": "三线",
    "临沂市": "三线", "洛阳市": "三线", "襄阳市": "三线", "洛阳市": "三线",
    "洛阳市": "三线", "洛阳市": "三线",
}

# Interest tag rules by region and city type
INTEREST_RULES = {
    "华北": ["历史文化", "城市探索"],
    "东北": ["自然风光", "城市探索"],
    "华东": ["城市探索", "美食体验"],
    "华中": ["自然风光", "历史文化"],
    "华南": ["休闲度假", "自然风光"],
    "西南": ["自然风光", "美食体验"],
    "西北": ["历史文化", "户外探险"],
}

# Known tourist cities — override interest tags
TOURIST_INTERESTS: dict[str, list[str]] = {
    "三亚市": ["休闲度假", "自然风光", "美食体验"],
    "丽江市": ["自然风光", "历史文化", "休闲度假"],
    "桂林市": ["自然风光", "户外探险", "休闲度假"],
    "拉萨市": ["历史文化", "自然风光", "户外探险"],
    "张家界市": ["自然风光", "户外探险"],
    "黄山市": ["自然风光", "户外探险", "历史文化"],
    "大理市": ["自然风光", "休闲度假", "历史文化"],
    "九寨沟县": ["自然风光", "户外探险"],
    "峨眉山市": ["自然风光", "历史文化"],
    "香格里拉市": ["自然风光", "户外探险", "历史文化"],
    "西双版纳": ["自然风光", "休闲度假"],
    "凤凰县": ["自然风光", "历史文化"],
    "平遥县": ["历史文化", "城市探索"],
    "武隆区": ["自然风光", "户外探险"],
    "稻城县": ["自然风光", "户外探险"],
    "阳朔县": ["自然风光", "户外探险"],
    "迪庆": ["自然风光", "户外探险"],
}

# Provincial capitals for traffic/importance boost
PROVINCIAL_CAPITALS = {
    "北京市", "上海市", "天津市", "重庆市",
    "哈尔滨市", "长春市", "沈阳市", "石家庄市",
    "济南市", "南京市", "杭州市", "福州市",
    "广州市", "海口市", "南宁市", "昆明市",
    "贵阳市", "成都市", "长沙市", "武汉市",
    "郑州市", "合肥市", "南昌市", "西安市",
    "太原市", "兰州市", "西宁市", "银川市",
    "乌鲁木齐市", "呼和浩特市", "拉萨市",
}


def get_tier(city_name: str) -> str:
    return CITY_TIERS.get(city_name, "四线")


def get_interests(city_name: str, region: str) -> list[str]:
    if city_name in TOURIST_INTERESTS:
        return TOURIST_INTERESTS[city_name]
    return INTEREST_RULES.get(region, ["城市探索", "自然风光"])


def compute_scores(tier: str, province_name: str, city_name: str) -> dict:
    """Compute destination scores heuristically based on tier and location."""
    tier_map = {"一线": 5, "新一线": 4, "二线": 3, "三线": 2, "四线": 1, "五线": 0}
    t = tier_map.get(tier, 0)
    is_capital = city_name in PROVINCIAL_CAPITALS

    cost = 300 + t * 180
    popularity = 25 + t * 12 + (8 if is_capital else 0)
    traffic = 30 + t * 16 + (15 if is_capital else 0)
    price_index = 40 + t * 20
    crowd = 30 + t * 15
    climate = 60 + (5 if province_name in ("广东", "广西", "海南", "福建") else
                   -10 if province_name in ("黑龙江", "吉林", "辽宁", "内蒙古") else 0)
    niche = max(0, 90 - t * 15 - (20 if is_capital else 0))

    if city_name in TOURIST_INTERESTS:
        popularity += 15
        niche += 20

    return {
        "cost": cost,
        "popularity": min(100, popularity),
        "traffic_score": min(100, traffic),
        "price_index": min(200, price_index),
        "crowd_level": min(100, crowd),
        "climate_score": climate,
        "niche_score": min(100, niche),
        "scenic_spots_count": 5 + t * 10 + (30 if city_name in TOURIST_INTERESTS else 0),
        "is_tourist_city": city_name in TOURIST_INTERESTS,
    }
