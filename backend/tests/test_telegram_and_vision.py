"""Unit tests for meal photo vision, agent write tools, and Telegram link code."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.meal_log import MealType
from services.ai_agents.fitness_advisor import AgentToolContext, build_tools
from services.foods.lookup import FoodMatch, MATCH_EXACT
from services.meal_vision import analyze_meal_photo


def test_build_tools_includes_write_tools_only_when_provided():
    base_tools = build_tools(AgentToolContext())
    assert len(base_tools) == 7

    ctx_with_writes = AgentToolContext(
        log_meal=AsyncMock(return_value={"status": "logged"}),
        log_body_metric=AsyncMock(return_value={"status": "created"}),
    )
    full_tools = build_tools(ctx_with_writes)
    names = {t.name for t in full_tools}
    assert len(full_tools) == 9
    assert "log_meal" in names
    assert "log_body_metric" in names


@pytest.mark.asyncio
async def test_analyze_meal_photo_resolves_db_macros():
    fake_food = SimpleNamespace(
        id=42,
        name_vi="Ức gà, phi lê, không da, sống",
        energy_kcal=120.0,
        protein_g=22.5,
        fat_g=2.6,
        carb_g=0.0,
        fiber_g=0.0,
    )
    fake_llm_resp = SimpleNamespace(
        content='{"items": [{"query_vi": "ức gà", "display_name": "Ức gà nướng", "estimated_grams": 150}], "notes": "Bữa ăn giàu đạm."}'
    )

    with (
        patch("services.meal_vision.settings.GOOGLE_API_KEY", "test-key"),
        patch("services.meal_vision.ChatGoogleGenerativeAI") as mock_llm_cls,
        patch(
            "services.meal_vision.search_foods",
            new=AsyncMock(return_value=[FoodMatch(food=fake_food, level=MATCH_EXACT)]),
        ),
    ):
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=fake_llm_resp)
        mock_llm_cls.return_value = mock_llm

        result = await analyze_meal_photo(
            db=MagicMock(),
            image_bytes=b"fake-jpeg-bytes",
            mime_type="image/jpeg",
        )

    assert isinstance(result.meal_type, MealType)
    assert len(result.items) == 1
    item = result.items[0]
    assert item.matched is True
    assert item.food_id == 42
    assert item.grams == 150.0
    assert item.energy_kcal == 180.0
    assert item.protein_g == 33.8
    assert result.total_kcal == 180.0
    assert result.notes == "Bữa ăn giàu đạm."

