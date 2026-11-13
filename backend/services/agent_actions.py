"""Hành động ghi dữ liệu dùng chung cho FitnessAdvisorAgent (Web Chat & Telegram Bot)."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.meal_log import MealType
from services import meals as meal_service
from services import progress as progress_service
from services.foods.lookup import AmbiguousFoodQuery, RawOnlyFoodQuery, search_foods


def _normalize_meal_type(raw: str | None) -> MealType:
    val = (raw or "").strip().lower()
    mapping = {
        "sang": MealType.SANG,
        "sáng": MealType.SANG,
        "trua": MealType.TRUA,
        "trưa": MealType.TRUA,
        "toi": MealType.TOI,
        "tối": MealType.TOI,
        "phu": MealType.PHU,
        "phụ": MealType.PHU,
    }
    return mapping.get(val, MealType.PHU)


async def log_meal_for_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    food_query: str,
    grams: float,
    meal_type: str = "phu",
) -> dict:
    """Tra món ăn trong DB rồi ghi một mục MealLog cho user_id."""
    food = None
    try:
        matches = await search_foods(db, food_query, limit=3)
        non_suggestions = [m for m in matches if not m.is_suggestion]
        chosen = non_suggestions[0] if non_suggestions else (matches[0] if matches else None)
        food = chosen.food if chosen else None
    except AmbiguousFoodQuery as exc:
        for meaning in exc.meanings:
            if meaning.foods:
                food = meaning.foods[0]
                break
    except RawOnlyFoodQuery as exc:
        if exc.raw_foods:
            food = exc.raw_foods[0]

    if food is None:
        raise ValueError(f"Không tìm thấy thực phẩm '{food_query}' trong từ điển FitAI.")

    mt = _normalize_meal_type(meal_type)
    entry = await meal_service.create_meal(
        db=db,
        user_id=user_id,
        food_id=food.id,
        grams=grams,
        meal_type=mt,
    )
    await db.commit()
    return {
        "status": "logged",
        "meal_id": str(entry.id),
        "food_name": food.name_vi,
        "grams": entry.grams,
        "meal_type": entry.meal_type.value,
        "eaten_on": entry.eaten_on.isoformat(),
        "energy_kcal": entry.energy_kcal,
        "protein_g": entry.protein_g,
        "fat_g": entry.fat_g,
        "carb_g": entry.carb_g,
    }


async def log_body_metric_for_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    weight_kg: float,
    waist_cm: Optional[float] = None,
) -> dict:
    """Ghi nhận cân nặng (và tuỳ chọn vòng eo) hôm nay cho user_id."""
    fields: dict = {"weight_kg": round(float(weight_kg), 2)}
    if waist_cm is not None:
        fields["waist_cm"] = round(float(waist_cm), 1)
    metric, inserted = await progress_service.upsert_body_metric(
        db=db,
        user_id=user_id,
        measured_on=None,
        fields=fields,
    )
    await db.commit()
    return {
        "status": "created" if inserted else "updated",
        "measured_on": metric.measured_on.isoformat(),
        "weight_kg": metric.weight_kg,
        "waist_cm": metric.waist_cm,
    }

