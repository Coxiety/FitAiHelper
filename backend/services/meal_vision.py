"""Nhận diện món ăn từ ảnh bằng Gemini Vision và đối chiếu bảng thực phẩm FitAI.

Luồng xử lý:
1. Gửi ảnh (base64) tới `gemini-2.5-flash` yêu cầu trả JSON các món ăn + ước lượng gram.
2. Tra cứu từng món qua `services.foods.lookup.search_foods` để lấy `food_id` và tính
   calo/macro chính xác từ bảng `foods` (không dùng số calo do LLM tự đoán).
3. Nếu một món chưa có trong bảng `foods`, vẫn trả về tên món + gram với `matched=False`
   để thông báo rõ cho người dùng.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.food import Food
from models.meal_log import MAX_MEAL_GRAMS, MealType
from services.foods.lookup import (
    AmbiguousFoodQuery,
    FoodLookupError,
    FoodQueryError,
    RawOnlyFoodQuery,
    search_foods,
)
from services.meals import snapshot

logger = logging.getLogger(__name__)

VN_OFFSET = timedelta(hours=7)
_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

VISION_PROMPT = """Bạn là chuyên gia dinh dưỡng FitAI. Hãy quan sát bức ảnh bữa ăn này và liệt kê các món ăn / nguyên liệu chính nhìn thấy được.

Trả về DUY NHẤT một JSON hợp lệ (không thêm markdown hay giải thích ngoài JSON) theo cấu trúc:
{
  "items": [
    {
      "query_vi": "tên thực phẩm tiếng Việt ngắn gọn 1-4 từ để tra từ điển (vd: cơm trắng, ức gà, trứng gà, thịt bò, phở bò, rau muống, cá hồi, bánh mì)",
      "display_name": "mô tả ngắn món ăn trên ảnh (vd: 1 bát cơm trắng)",
      "estimated_grams": 150
    }
  ],
  "notes": "nhận xét ngắn 1 câu về bữa ăn"
}

Quy tắc:
- Nếu ảnh không phải đồ ăn/thức uống, trả về `"items": []` và ghi rõ trong `"notes"`.
- Tách các thành phần chính nếu là đĩa cơm/bữa nhiều món (vd: cơm trắng 180g, ức gà nướng 150g, rau luộc 100g).
- `estimated_grams` là số nguyên dương (gram phần ăn được, tối đa 3000).
"""


@dataclass
class DetectedFoodItem:
    display_name: str
    query_vi: str
    grams: float
    matched: bool
    food_id: int | None = None
    food_name_vi: str | None = None
    energy_kcal: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carb_g: float | None = None
    note: str | None = None


@dataclass
class VisionMealResult:
    meal_type: MealType
    items: list[DetectedFoodItem] = field(default_factory=list)
    notes: str = ""

    @property
    def matched_items(self) -> list[DetectedFoodItem]:
        return [i for i in self.items if i.matched and i.food_id is not None]

    @property
    def total_kcal(self) -> float:
        return round(sum(i.energy_kcal or 0.0 for i in self.matched_items), 1)

    @property
    def total_protein_g(self) -> float:
        return round(sum(i.protein_g or 0.0 for i in self.matched_items), 1)

    @property
    def total_fat_g(self) -> float:
        return round(sum(i.fat_g or 0.0 for i in self.matched_items), 1)

    @property
    def total_carb_g(self) -> float:
        return round(sum(i.carb_g or 0.0 for i in self.matched_items), 1)


def infer_meal_type_vn(now_utc: datetime | None = None) -> MealType:
    """Suy đoán bữa ăn theo giờ Việt Nam hiện tại."""
    vn_now = (now_utc or datetime.now(timezone.utc)) + VN_OFFSET
    hour = vn_now.hour + vn_now.minute / 60.0
    if hour < 10.5:
        return MealType.SANG
    if hour < 14.5:
        return MealType.TRUA
    if hour < 17.5:
        return MealType.PHU
    return MealType.TOI


def _extract_json_payload(raw_text: str) -> dict:
    text = raw_text.strip()
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        return {"items": [], "notes": "Không đọc được JSON từ phản hồi nhận diện ảnh."}
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else {"items": [], "notes": ""}
    except json.JSONDecodeError:
        logger.warning("Vision JSON decode failed")
        return {"items": [], "notes": "Không phân tích được kết quả nhận diện ảnh."}


async def _resolve_food_match(db: AsyncSession, query_vi: str) -> tuple[Food | None, str | None]:
    """Tra cứu một món ăn trong bảng foods; xử lý trường hợp đa nghĩa hoặc nguyên liệu sống."""
    try:
        matches = await search_foods(db, query_vi, limit=3)
        non_suggestions = [m for m in matches if not m.is_suggestion]
        chosen = non_suggestions[0] if non_suggestions else (matches[0] if matches else None)
        if chosen is None:
            return None, None
        return chosen.food, chosen.note
    except AmbiguousFoodQuery as exc:
        for meaning in exc.meanings:
            if meaning.foods:
                return meaning.foods[0], f"từ đa nghĩa → chọn '{meaning.label}'"
        return None, None
    except RawOnlyFoodQuery as exc:
        if exc.raw_foods:
            return exc.raw_foods[0], "ước tính theo nguyên liệu sống trong DB"
        return None, None
    except (FoodQueryError, FoodLookupError):
        return None, None


async def analyze_meal_photo(
    db: AsyncSession,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    caption: str | None = None,
) -> VisionMealResult:
    """Nhận diện ảnh món ăn bằng Gemini Vision rồi đối chiếu dinh dưỡng từ PostgreSQL."""
    if not settings.GOOGLE_API_KEY:
        raise RuntimeError("Thiếu GOOGLE_API_KEY để nhận diện ảnh.")

    b64_image = base64.b64encode(image_bytes).decode("ascii")
    prompt_text = VISION_PROMPT
    if caption and caption.strip():
        prompt_text += f"\nGhi chú thêm của người dùng về ảnh: {caption.strip()}"

    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.1,
    )
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_image}"}},
        ]
    )
    response = await llm.ainvoke([message])
    raw_content = response.content if isinstance(response.content, str) else str(response.content)
    payload = _extract_json_payload(raw_content)

    meal_type = infer_meal_type_vn()
    items: list[DetectedFoodItem] = []

    for raw_item in payload.get("items") or []:
        if not isinstance(raw_item, dict):
            continue
        query_vi = str(raw_item.get("query_vi") or raw_item.get("display_name") or "").strip()
        display_name = str(raw_item.get("display_name") or query_vi).strip()
        if not query_vi:
            continue
        try:
            grams = float(raw_item.get("estimated_grams") or 100)
        except (TypeError, ValueError):
            grams = 100.0
        grams = max(10.0, min(grams, float(MAX_MEAL_GRAMS)))

        food, note = await _resolve_food_match(db, query_vi)
        if food is None:
            items.append(
                DetectedFoodItem(
                    display_name=display_name,
                    query_vi=query_vi,
                    grams=round(grams, 1),
                    matched=False,
                    note="Chưa tìm thấy món khớp trong từ điển thực phẩm",
                )
            )
            continue

        macros = snapshot(food, grams)
        items.append(
            DetectedFoodItem(
                display_name=display_name,
                query_vi=query_vi,
                grams=round(grams, 1),
                matched=True,
                food_id=food.id,
                food_name_vi=food.name_vi,
                energy_kcal=macros["energy_kcal"],
                protein_g=macros["protein_g"],
                fat_g=macros["fat_g"],
                carb_g=macros["carb_g"],
                note=note,
            )
        )

    return VisionMealResult(
        meal_type=meal_type,
        items=items,
        notes=str(payload.get("notes") or "").strip(),
    )

