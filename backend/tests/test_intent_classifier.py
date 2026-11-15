"""Unit tests for the local TF-IDF + Logistic Regression Intent Classifier & fast-path lookup."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.foods.lookup import FoodMatch, MATCH_EXACT
from services.foods.preparation import FoodPreparation
from services.foods.sources import USDA_SR, VN2007
from services.intent_classifier import (
    INTENT_COACHING_GENERAL,
    INTENT_DAILY_PROGRESS,
    INTENT_FOOD_LOOKUP,
    INTENT_LOG_ACTION,
    INTENT_OUT_OF_SCOPE,
    OUT_OF_SCOPE_REPLY,
    classify_intent,
    extract_food_lookup_slot,
    is_out_of_scope,
    try_fast_food_lookup,
    try_fast_route,
)


@pytest.mark.parametrize(
    "text,expected_intent",
    [
        ("150g ức gà bao nhiêu calo?", INTENT_FOOD_LOOKUP),
        ("thông tin dinh dưỡng phở bò", INTENT_FOOD_LOOKUP),
        ("calories in 200g salmon", INTENT_FOOD_LOOKUP),
        ("ghi 150g ức gà bữa trưa", INTENT_LOG_ACTION),
        ("hôm nay mình nặng 68kg", INTENT_LOG_ACTION),
        ("hôm nay tôi đã ăn bao nhiêu calo rồi", INTENT_DAILY_PROGRESS),
        ("tiến độ 7 ngày gần nhất", INTENT_DAILY_PROGRESS),
        ("150g ức gà có đủ đạm cho mục tiêu giảm cân không", INTENT_COACHING_GENERAL),
        ("so sánh phở bò và bún bò huế", INTENT_COACHING_GENERAL),
        ("giá vé world cup bao nhiêu?", INTENT_OUT_OF_SCOPE),
        ("viết giúp tôi một bài thơ về mùa thu", INTENT_OUT_OF_SCOPE),
        ("write a python script to sort numbers", INTENT_OUT_OF_SCOPE),
    ],
)
def test_intent_classifier_predictions(text: str, expected_intent: str):
    pred = classify_intent(text)
    assert pred.intent == expected_intent
    assert 0.0 <= pred.confidence <= 1.0


def test_extract_food_slot_preserves_vietnamese_food_names_and_grams():
    slot1 = extract_food_lookup_slot("150g ức gà bao nhiêu calo?")
    assert slot1 is not None
    assert slot1.query.lower() == "ức gà"
    assert slot1.grams == 150.0

    slot2 = extract_food_lookup_slot("giá trị dinh dưỡng của cua biển")
    assert slot2 is not None
    assert slot2.query.lower() == "cua biển"
    assert slot2.grams is None

    slot3 = extract_food_lookup_slot("nutrition of 200g avocado")
    assert slot3 is not None
    assert slot3.query.lower() == "avocado"
    assert slot3.grams == 200.0


def test_guard_blocks_logging_comparison_and_coaching_queries():
    assert extract_food_lookup_slot("ghi 150g ức gà bữa trưa") is None
    assert extract_food_lookup_slot("so sánh ức gà và cá hồi") is None
    assert extract_food_lookup_slot("150g ức gà có đủ đạm cho mục tiêu giảm cân không") is None
    assert extract_food_lookup_slot("hôm nay ăn bao nhiêu calo rồi") is None


@pytest.mark.asyncio
async def test_try_fast_food_lookup_returns_formatted_reply_and_sources():
    fake_source = SimpleNamespace(code=USDA_SR, title="USDA FoodData Central — SR Legacy", authors_org="USDA", year=2018)
    fake_food = SimpleNamespace(
        id=101,
        source=fake_source,
        source_ref="171077",
        source_page=None,
        name_vi="Ức gà sống (thịt, bỏ da)",
        name_en="Chicken breast",
        name_original="Chicken, broilers or fryers, breast, meat only, raw",
        group_name="Thịt gia cầm",
        refuse_pct=None,
        preparation=FoodPreparation.RAW,
        energy_kcal=120.0,
        protein_g=22.5,
        fat_g=2.6,
        carb_g=0.0,
        carb_total_g=0.0,
        fiber_g=0.0,
        water_g=73.9,
        ash_g=1.0,
    )

    with patch(
        "services.intent_classifier.search_foods",
        new=AsyncMock(return_value=[FoodMatch(food=fake_food, level=MATCH_EXACT)]),
    ):
        res = await try_fast_food_lookup(MagicMock(), "150g ức gà bao nhiêu calo?")

    assert res is not None
    reply, sources = res
    assert "Ức gà sống (thịt, bỏ da)" in reply
    assert "180 kcal" in reply
    assert "fdc_id 171077" in reply
    assert len(sources) == 1
    assert sources[0]["source_code"] == USDA_SR


@pytest.mark.asyncio
async def test_try_fast_food_lookup_falls_back_to_llm_on_non_lookup_or_empty_db():
    assert await try_fast_food_lookup(MagicMock(), "tôi nên ăn bao nhiêu calo để giảm cân") is None

    with patch("services.intent_classifier.search_foods", new=AsyncMock(return_value=[])):
        assert await try_fast_food_lookup(MagicMock(), "200g pizza phô mai bao nhiêu calo") is None


@pytest.mark.parametrize(
    "irrelevant_text",
    [
        "Giá vé World Cup bao nhiêu?",
        "Viết giúp tôi một bài thơ về mùa thu.",
        "Thời tiết hôm nay ở Hà Nội có mưa không?",
        "Hướng dẫn tôi cách nấu phở bò.",
        "Sửa lỗi code Python giúp mình với",
        "Giá bitcoin hôm nay bao nhiêu?",
        "Recommend a good sci-fi movie to watch tonight",
    ],
)
def test_out_of_scope_blocks_irrelevant_queries(irrelevant_text: str):
    assert is_out_of_scope(irrelevant_text) is True


@pytest.mark.parametrize(
    "in_domain_text",
    [
        "150g ức gà bao nhiêu calo?",
        "Hướng dẫn kỹ thuật squat đúng cách",
        "Tôi muốn giảm cân an toàn thì ăn bao nhiêu calo?",
        "Xem lịch sử tập luyện tuần này",
        "Chọn mục 1",
        "Xin chào bạn",
    ],
)
def test_out_of_scope_never_blocks_in_domain_or_followup_queries(in_domain_text: str):
    assert is_out_of_scope(in_domain_text) is False


@pytest.mark.asyncio
async def test_try_fast_route_rejects_irrelevant_before_db_or_llm():
    res = await try_fast_route(MagicMock(), "Giá vé World Cup bao nhiêu?")
    assert res == (OUT_OF_SCOPE_REPLY, [])

