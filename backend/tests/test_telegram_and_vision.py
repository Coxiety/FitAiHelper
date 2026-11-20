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
        log_workout=AsyncMock(return_value={"status": "logged"}),
    )
    full_tools = build_tools(ctx_with_writes)
    names = {t.name for t in full_tools}
    assert len(full_tools) == 10
    assert "log_meal" in names
    assert "log_body_metric" in names
    assert "log_workout" in names


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
        patch("services.meal_vision.settings.LLM_PROVIDER", "gemini"),
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
    assert "2D" in result.disclaimer and "trước khi log" in result.disclaimer


def test_format_vision_reply_includes_2d_accuracy_disclaimer():
    from scripts.run_telegram_bot import _format_vision_reply
    from services.meal_vision import DetectedFoodItem, PHOTO_ACCURACY_DISCLAIMER, VisionMealResult

    result = VisionMealResult(
        meal_type=MealType.TRUA,
        items=[
            DetectedFoodItem(
                display_name="Cơm trắng",
                query_vi="cơm trắng",
                grams=150.0,
                matched=True,
                food_id=1,
                food_name_vi="Cơm trắng",
                energy_kcal=195.0,
                protein_g=4.0,
                fat_g=0.4,
                carb_g=42.0,
            )
        ],
    )
    reply = _format_vision_reply(result)
    assert PHOTO_ACCURACY_DISCLAIMER in reply


@pytest.mark.asyncio
async def test_openrouter_chat_model_bind_tools_and_vision(monkeypatch):
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
    from services.ai_agents.llm_factory import OpenRouterChatModel

    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_123",
                                    "type": "function",
                                    "function": {
                                        "name": "calc_body_metrics",
                                        "arguments": "{}",
                                    },
                                }
                            ],
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json
            return FakeResponse()

    monkeypatch.setattr("services.ai_agents.llm_factory.httpx.AsyncClient", FakeClient)

    tools = build_tools(AgentToolContext())
    llm = OpenRouterChatModel(
        model="qwen/qwen3.7-flash",
        api_key="or-test-key",
        reasoning_effort="low",
    ).bind_tools(tools, tool_choice="any")

    resp = await llm.ainvoke([
        SystemMessage(content="Sys"),
        HumanMessage(content="Tính TDEE"),
        ToolMessage(content="ok", tool_call_id="call_prev"),
    ])

    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer or-test-key"
    assert captured["body"]["model"] == "qwen/qwen3.7-flash"
    assert captured["body"]["tool_choice"] == "required"
    assert captured["body"]["reasoning"] == {"effort": "low", "exclude": True}
    assert len(captured["body"]["tools"]) == len(tools)
    assert resp.tool_calls == [{"name": "calc_body_metrics", "args": {}, "id": "call_123", "type": "tool_call"}]


@pytest.mark.asyncio
async def test_analyze_meal_photo_routes_to_openrouter_when_enabled():
    fake_food = SimpleNamespace(
        id=42,
        name_vi="Ức gà nướng",
        energy_kcal=165.0,
        protein_g=31.0,
        fat_g=3.6,
        carb_g=0.0,
        fiber_g=0.0,
    )
    fake_resp = SimpleNamespace(
        content='{"items": [{"query_vi": "ức gà", "display_name": "Ức gà nướng", "estimated_grams": 100}], "notes": "OK"}'
    )
    with (
        patch("services.meal_vision.settings.LLM_PROVIDER", "openrouter"),
        patch("services.meal_vision.settings.OPENROUTER_API_KEY", "or-test-key"),
        patch("services.meal_vision.OpenRouterChatModel") as mock_or_cls,
        patch(
            "services.meal_vision.search_foods",
            new=AsyncMock(return_value=[FoodMatch(food=fake_food, level=MATCH_EXACT)]),
        ),
    ):
        mock_or = MagicMock()
        mock_or.ainvoke = AsyncMock(return_value=fake_resp)
        mock_or_cls.return_value = mock_or

        result = await analyze_meal_photo(db=MagicMock(), image_bytes=b"img", mime_type="image/jpeg")

    assert result.total_kcal == 165.0
    assert mock_or_cls.called

