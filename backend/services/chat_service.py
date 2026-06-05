import json
import httpx
from typing import Any

from anthropic import AsyncAnthropic

from config import settings


SYSTEM_PROMPT = """你是 Nomad AI 旅行规划助手，专门帮助用户发现和规划中国境内的旅游目的地。

你的能力范围：
- 根据用户的偏好（预算、兴趣、旅行风格、气候偏好）推荐最合适的目的地
- 解答关于特定目的地的详细信息（景点、消费、交通、天气等）
- 搜索符合条件的目的地
- 提供实时天气和中国假期客流信息

你的行为准则：
- 全程用中文交流，语气热情、专业、简洁
- 当用户表达旅行偏好时，**必须调用 recommend_destinations 函数**来获取基于算法的精准推荐
- 当用户询问特定城市详情时，调用 get_destination_detail 获取信息
- 当用户想搜索目的地时，调用 search_destinations
- 主动引导用户说明偏好：预算多少？喜欢什么类型（自然风光/历史文化/美食体验等）？什么旅行风格（穷游/舒适/奢华/亲子）？
- 在展示推荐结果后，鼓励用户追问和细化需求
- 回复中要包含目的地的具体数据（费用、景点数、匹配置信度等），让推荐有说服力"""

TOOLS = [
    {
        "name": "search_destinations",
        "description": "搜索/筛选中国旅游目的地。根据关键词、地区、城市等级、兴趣标签等条件搜索。",
        "input_schema": {
            "type": "object",
            "properties": {
                "q": {"type": "string", "description": "搜索关键词（城市名、省份名或区域名）"},
                "region": {"type": "string", "description": "地理区域：华北、华东、华南、西南、西北、东北、华中"},
                "interest": {"type": "string", "description": "兴趣标签：自然风光、历史文化、美食体验、户外探险、休闲度假、城市探索"},
                "tier": {"type": "string", "description": "城市等级：一线、新一线、二线、三线、四线、五线"},
                "limit": {"type": "integer", "description": "最多返回数量，默认10"},
            }
        }
    },
    {
        "name": "get_destination_detail",
        "description": "获取单个目的地的完整详细信息，包括景点列表、消费水平、交通评分、气候评分、人气度等。",
        "input_schema": {
            "type": "object",
            "properties": {
                "dest_id": {
                    "type": "string",
                    "description": "目的地ID，可选值：beijing、shanghai、chengdu、lijiang、sanya、xian、guilin、lhasa、zhangjiajie、xiamen、harbin、dunhuang",
                },
            },
            "required": ["dest_id"]
        }
    },
    {
        "name": "recommend_destinations",
        "description": "核心推荐引擎。基于7维度算法（气候匹配、预算适配、兴趣契合、交通便利、客流避让、景区丰度、空气质量），为用户推荐最匹配的中国旅游目的地。当用户表达旅行偏好时必须调用此函数。",
        "input_schema": {
            "type": "object",
            "properties": {
                "budget": {"type": "integer", "description": "每人每日预算（人民币元），范围 500-5000"},
                "interests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "兴趣标签列表，可选值：自然风光、历史文化、美食体验、户外探险、休闲度假、城市探索"
                },
                "style": {
                    "type": "string",
                    "description": "旅行风格：背包穷游、舒适休闲、奢华体验、亲子家庭"
                },
                "climate": {
                    "type": "string",
                    "description": "气候偏好：温暖、温和、凉爽"
                }
            },
            "required": ["budget", "interests", "style", "climate"]
        }
    },
    {
        "name": "get_weather",
        "description": "获取指定目的地的实时天气信息。",
        "input_schema": {
            "type": "object",
            "properties": {
                "dest_id": {
                    "type": "string",
                    "description": "目的地ID，如 beijing、shanghai 等",
                },
            },
            "required": ["dest_id"]
        }
    },
    {
        "name": "get_holidays",
        "description": "获取中国法定节假日列表，用于判断出行期间是否逢节假日（客流会显著增加）。",
        "input_schema": {"type": "object", "properties": {}}
    },
]

DEST_ID_MAP = {
    "beijing": ("北京", 39.90, 116.41),
    "shanghai": ("上海", 31.23, 121.47),
    "chengdu": ("成都", 30.57, 104.07),
    "lijiang": ("丽江", 26.86, 100.23),
    "sanya": ("三亚", 18.25, 109.51),
    "xian": ("西安", 34.34, 108.94),
    "guilin": ("桂林", 25.27, 110.28),
    "lhasa": ("拉萨", 29.65, 91.13),
    "zhangjiajie": ("张家界", 29.12, 110.48),
    "xiamen": ("厦门", 24.48, 118.09),
    "harbin": ("哈尔滨", 45.80, 126.53),
    "dunhuang": ("敦煌", 40.14, 94.66),
}


class ChatService:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def execute_tool(self, tool_name: str, tool_input: dict, db) -> Any:
        from routers.destinations import (
            search_destinations_internal,
            get_destination_internal,
            compute_recommendations_internal,
            get_holidays_internal,
        )

        if tool_name == "search_destinations":
            return await search_destinations_internal(
                db,
                q=tool_input.get("q", ""),
                region=tool_input.get("region", ""),
                tier=tool_input.get("tier", ""),
                interest=tool_input.get("interest", ""),
                limit=tool_input.get("limit", 10),
            )

        elif tool_name == "get_destination_detail":
            dest_id = tool_input["dest_id"]
            dest = await get_destination_internal(db, dest_id)
            if not dest:
                return {"error": f"未找到目的地: {dest_id}"}
            return dest.model_dump()

        elif tool_name == "recommend_destinations":
            return await compute_recommendations_internal(
                db,
                budget=tool_input["budget"],
                interests=tool_input.get("interests", []),
                style=tool_input.get("style", "舒适休闲"),
                climate=tool_input.get("climate", "温和"),
            )

        elif tool_name == "get_weather":
            dest_id = tool_input["dest_id"]
            if dest_id not in DEST_ID_MAP:
                return {"error": f"未知目的地: {dest_id}"}
            city, lat, lng = DEST_ID_MAP[dest_id]
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        "https://api.open-meteo.com/v1/forecast",
                        params={
                            "latitude": lat, "longitude": lng,
                            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                            "timezone": "Asia/Shanghai",
                        },
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        current = data.get("current", {})
                        weather_codes = {
                            0: "晴", 1: "大部晴", 2: "多云", 3: "阴",
                            45: "雾", 48: "雾凇", 51: "小雨", 53: "中雨", 55: "大雨",
                            61: "小雨", 63: "中雨", 65: "大雨", 71: "小雪", 73: "中雪",
                            75: "大雪", 80: "阵雨", 95: "雷暴",
                        }
                        code = current.get("weather_code", 0)
                        return {
                            "city": city,
                            "temp": current.get("temperature_2m", "N/A"),
                            "humidity": current.get("relative_humidity_2m", "N/A"),
                            "condition": weather_codes.get(code, str(code)),
                            "wind_speed": current.get("wind_speed_10m", "N/A"),
                        }
            except Exception:
                pass
            return {"city": city, "temp": "N/A", "condition": "暂无数据"}

        elif tool_name == "get_holidays":
            return await get_holidays_internal(db)

        return {"error": f"未知工具: {tool_name}"}

    async def chat(self, messages: list[dict], db) -> dict:
        system = SYSTEM_PROMPT

        # Convert messages to Anthropic format
        anthropic_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role in ("user", "assistant"):
                anthropic_messages.append({"role": role, "content": content})

        max_turns = 5
        cards = None

        for _ in range(max_turns):
            response = await self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=system,
                messages=anthropic_messages,
                tools=TOOLS,
                temperature=0.7,
            )

            # Check for tool use
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            text_blocks = [b for b in response.content if b.type == "text"]

            if not tool_use_blocks:
                text = "\n".join(b.text for b in text_blocks)
                # Parse card data from last recommendation results
                return {"text": text.strip(), "cards": cards}

            # Execute tools
            tool_results = []
            for tool_block in tool_use_blocks:
                result = await self.execute_tool(tool_block.name, tool_block.input, db)
                tool_results.append({
                    "tool_use_id": tool_block.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
                # If this was a recommend call, extract card data
                if tool_block.name == "recommend_destinations" and isinstance(result, dict) and "all" in result:
                    cards = self._extract_cards(result)

            # Build assistant message with tool use
            assistant_content = list(response.content)

            # Send tool results back
            anthropic_messages.append({"role": "assistant", "content": assistant_content})
            anthropic_messages.append({
                "role": "user",
                "content": [{"type": "tool_result", **tr} for tr in tool_results],
            })

        text = "抱歉，处理请求时遇到了一些问题。请稍后再试。"
        return {"text": text, "cards": cards}

    def _extract_cards(self, result: dict) -> list[dict]:
        cards = []
        top = result.get("top")
        if top:
            cards.append({
                "type": "hero",
                "rank": 1,
                "city": top["dest"]["city"],
                "destId": top["dest"]["id"],
                "cost": top["dest"]["cost"],
                "confidence": top.get("confidence", 0),
                "matchReasons": top.get("matchReasons", []),
                "dimensions": top.get("dimensions", {}),
                "region": top["dest"]["region"],
                "scenicSpots": top["dest"]["scenicSpots"],
            })
        for i, r in enumerate(result.get("runners", [])[:3]):
            cards.append({
                "type": "runner",
                "rank": i + 2,
                "city": r["dest"]["city"],
                "destId": r["dest"]["id"],
                "cost": r["dest"]["cost"],
                "confidence": r.get("confidence", 0),
                "matchReasons": r.get("matchReasons", []),
                "region": r["dest"]["region"],
            })
        return cards


chat_service = ChatService()
