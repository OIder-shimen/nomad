"""Seed scenic spots, holidays, and admin user. Run after import_cities.py."""
import asyncio
import json

from sqlalchemy import select

from database import async_session, init_db
from models.models import ScenicSpot, Holiday, User
from config import settings
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SCENIC_SPOTS = {
    "beijing": [
        {"name": "故宫博物院", "grade": "5A"}, {"name": "八达岭长城", "grade": "5A"},
        {"name": "颐和园", "grade": "5A"}, {"name": "天坛公园", "grade": "5A"},
        {"name": "明十三陵", "grade": "5A"}, {"name": "恭王府", "grade": "5A"},
        {"name": "圆明园遗址公园", "grade": "5A"}, {"name": "雍和宫", "grade": "4A"},
    ],
    "shanghai": [
        {"name": "东方明珠", "grade": "5A"}, {"name": "上海野生动物园", "grade": "5A"},
        {"name": "上海科技馆", "grade": "5A"}, {"name": "豫园", "grade": "4A"},
        {"name": "外滩", "grade": "4A"}, {"name": "上海迪士尼", "grade": "5A"},
    ],
    "chengdu": [
        {"name": "都江堰", "grade": "5A"}, {"name": "青城山", "grade": "5A"},
        {"name": "大熊猫繁育基地", "grade": "4A"}, {"name": "武侯祠", "grade": "4A"},
        {"name": "宽窄巷子", "grade": "4A"}, {"name": "杜甫草堂", "grade": "4A"},
    ],
    "lijiang": [
        {"name": "丽江古城", "grade": "5A"}, {"name": "玉龙雪山", "grade": "5A"},
        {"name": "泸沽湖", "grade": "4A"}, {"name": "束河古镇", "grade": "4A"},
        {"name": "虎跳峡", "grade": "4A"},
    ],
    "sanya": [
        {"name": "南山文化旅游区", "grade": "5A"}, {"name": "蜈支洲岛", "grade": "5A"},
        {"name": "天涯海角", "grade": "4A"}, {"name": "亚龙湾", "grade": "4A"},
        {"name": "大小洞天", "grade": "5A"},
    ],
    "xian": [
        {"name": "兵马俑", "grade": "5A"}, {"name": "大雁塔", "grade": "5A"},
        {"name": "华清宫", "grade": "5A"}, {"name": "西安城墙", "grade": "5A"},
        {"name": "大唐芙蓉园", "grade": "5A"}, {"name": "陕西历史博物馆", "grade": "4A"},
    ],
    "guilin": [
        {"name": "漓江景区", "grade": "5A"}, {"name": "象山景区", "grade": "5A"},
        {"name": "两江四湖", "grade": "5A"}, {"name": "龙脊梯田", "grade": "4A"},
        {"name": "阳朔西街", "grade": "4A"},
    ],
    "lhasa": [
        {"name": "布达拉宫", "grade": "5A"}, {"name": "大昭寺", "grade": "5A"},
        {"name": "纳木错", "grade": "4A"}, {"name": "罗布林卡", "grade": "4A"},
        {"name": "色拉寺", "grade": "4A"},
    ],
    "zhangjiajie": [
        {"name": "张家界国家森林公园", "grade": "5A"}, {"name": "天门山", "grade": "5A"},
        {"name": "武陵源", "grade": "5A"}, {"name": "黄龙洞", "grade": "4A"},
        {"name": "袁家界", "grade": "4A"},
    ],
    "xiamen": [
        {"name": "鼓浪屿", "grade": "5A"}, {"name": "南普陀寺", "grade": "4A"},
        {"name": "厦门园林植物园", "grade": "4A"}, {"name": "胡里山炮台", "grade": "4A"},
        {"name": "曾厝垵", "grade": "4A"},
    ],
    "harbin": [
        {"name": "冰雪大世界", "grade": "5A"}, {"name": "太阳岛", "grade": "5A"},
        {"name": "中央大街", "grade": "4A"}, {"name": "圣索菲亚教堂", "grade": "4A"},
        {"name": "东北虎林园", "grade": "4A"},
    ],
    "dunhuang": [
        {"name": "莫高窟", "grade": "5A"}, {"name": "鸣沙山月牙泉", "grade": "5A"},
        {"name": "雅丹魔鬼城", "grade": "4A"}, {"name": "玉门关", "grade": "4A"},
        {"name": "阳关", "grade": "4A"},
    ],
}

HOLIDAYS = [
    {"name": "元旦", "start_date": "2025-01-01", "end_date": "2025-01-01", "crowd_boost": 5},
    {"name": "春节", "start_date": "2025-01-28", "end_date": "2025-02-04", "crowd_boost": 25},
    {"name": "清明节", "start_date": "2025-04-04", "end_date": "2025-04-06", "crowd_boost": 10},
    {"name": "劳动节", "start_date": "2025-05-01", "end_date": "2025-05-05", "crowd_boost": 20},
    {"name": "端午节", "start_date": "2025-05-31", "end_date": "2025-06-02", "crowd_boost": 10},
    {"name": "中秋节+国庆", "start_date": "2025-10-01", "end_date": "2025-10-08", "crowd_boost": 25},
    {"name": "元旦", "start_date": "2026-01-01", "end_date": "2026-01-03", "crowd_boost": 5},
    {"name": "春节", "start_date": "2026-02-17", "end_date": "2026-02-23", "crowd_boost": 25},
    {"name": "清明节", "start_date": "2026-04-05", "end_date": "2026-04-07", "crowd_boost": 10},
    {"name": "劳动节", "start_date": "2026-05-01", "end_date": "2026-05-05", "crowd_boost": 20},
    {"name": "端午节", "start_date": "2026-05-20", "end_date": "2026-05-22", "crowd_boost": 10},
    {"name": "中秋节", "start_date": "2026-09-25", "end_date": "2026-09-27", "crowd_boost": 12},
    {"name": "国庆节", "start_date": "2026-10-01", "end_date": "2026-10-07", "crowd_boost": 25},
]

ORIGINAL_SPOT_IDS = list(SCENIC_SPOTS.keys())


async def seed():
    await init_db()

    async with async_session() as db:
        # Scenic spots — skip if already seeded
        spot_count = (await db.execute(select(ScenicSpot).limit(1))).scalar_one_or_none()
        if spot_count:
            print("Scenic spots already seeded. Skipping.")
        else:
            for dest_id, spots in SCENIC_SPOTS.items():
                for s in spots:
                    db.add(ScenicSpot(destination_id=dest_id, name=s["name"], grade=s["grade"]))
            await db.flush()
            print(f"Seeded {sum(len(v) for v in SCENIC_SPOTS.values())} scenic spots.")

        # Holidays — skip if already seeded
        holiday_count = (await db.execute(select(Holiday).limit(1))).scalar_one_or_none()
        if holiday_count:
            print("Holidays already seeded. Skipping.")
        else:
            for h in HOLIDAYS:
                db.add(Holiday(**h))
            await db.flush()
            print(f"Seeded {len(HOLIDAYS)} holidays.")

        # Admin user — create only if not exists
        admin = (await db.execute(select(User).where(User.username == settings.admin_username))).scalar_one_or_none()
        if admin:
            print("Admin user already exists. Skipping.")
        else:
            admin = User(
                username=settings.admin_username,
                hashed_password=pwd_context.hash(settings.admin_password),
                is_admin=True,
            )
            db.add(admin)
            print(f"Created admin user: {settings.admin_username}")

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
