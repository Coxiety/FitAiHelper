"""Nạp toàn bộ 7,793 thực phẩm từ USDA FoodData Central SR Legacy (2018-04) vào bảng `foods`.

- Giữ nguyên tên tiếng Việt đã duyệt cho 20 món trong `USDA_SELECTION`.
- Các món còn lại dùng tên tiếng Anh chuẩn từ `food.csv` (`name_vi`, `name_en`, `name_original`),
  được `normalize_search` để tìm kiếm được bằng cả tiếng Việt (nhóm đã duyệt) và tiếng Anh.
- Không xoá dòng `VN2007`, `ADMIN_MANUAL`, hay `meal_logs` đang tham chiếu.
- Upsert theo lô 500 dòng để không vượt giới hạn bind parameter của PostgreSQL.

Chạy từ thư mục `backend`:
    .venv\\Scripts\\python.exe -m scripts.ingest_usda_full
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.database import AsyncSessionLocal, engine  # noqa: E402
from models.food import Food  # noqa: E402
from services.foods.normalize import normalize_search  # noqa: E402
from services.foods.preparation import PREPARATION_OVERRIDES, classify  # noqa: E402
from services.foods.sources import USDA_SR, USDA_SR_ID  # noqa: E402
from services.foods.usda import (  # noqa: E402
    CATEGORY_VI,
    FLAG_NEGATIVE_CARB,
    USDA_SELECTION,
    _quality,
    _rows,
    carb_without_fiber,
    nutrient_ids,
)

DEFAULT_SR_DIR = REPO_ROOT / "data" / "foods" / "external" / "FoodData_Central_sr_legacy_food_csv_2018-04"
BATCH_SIZE = 500


def build_full_sr_legacy_rows(sr_dir: Path = DEFAULT_SR_DIR) -> list[dict]:
    """Đọc toàn bộ SR Legacy CSV và trả về danh sách dict sẵn sàng upsert vào bảng `foods`."""
    curated_names = {str(p.fdc_id): p.name_vi for p in USDA_SELECTION}
    ids = nutrient_ids(sr_dir)
    col_of = {v: k for k, v in ids.items()}
    categories = {r["id"]: r["description"] for r in _rows(sr_dir / "food_category.csv")}

    foods_by_id: dict[str, dict] = {}
    for r in _rows(sr_dir / "food.csv"):
        foods_by_id[r["fdc_id"]] = r

    values: dict[str, dict] = {fid: {} for fid in foods_by_id}
    for r in _rows(sr_dir / "food_nutrient.csv"):
        fid = r["fdc_id"]
        nid = r["nutrient_id"]
        if fid in values and nid in col_of and r["amount"] != "":
            values[fid][col_of[nid]] = float(r["amount"])

    conv = {r["id"]: r["fdc_id"] for r in _rows(sr_dir / "food_nutrient_conversion_factor.csv") if r["fdc_id"] in foods_by_id}
    factors: dict[str, tuple] = {}
    for r in _rows(sr_dir / "food_calorie_conversion_factor.csv"):
        fid = conv.get(r["food_nutrient_conversion_factor_id"])
        if fid:
            factors[fid] = tuple(
                float(r[k]) if r[k] else None
                for k in ("protein_value", "fat_value", "carbohydrate_value")
            )

    rows: list[dict] = []
    for fid, food in foods_by_id.items():
        v = values[fid]
        desc = (food["description"] or "").strip()
        if not desc:
            continue

        carb_g, neg = carb_without_fiber(v.get("carb_total_g"), v.get("fiber_g"))
        if v.get("energy_kcal") is not None:
            flags = _quality(v, factors.get(fid), desc)
        else:
            flags = {}
        if neg:
            flags[FLAG_NEGATIVE_CARB] = neg

        category = categories.get(food["food_category_id"], "")
        group_name = (
            f"{CATEGORY_VI[category]} ({category})"
            if category in CATEGORY_VI
            else (category or "USDA SR Legacy")
        )[:255]

        display_name = curated_names.get(fid, desc)[:255]
        override = PREPARATION_OVERRIDES.get((USDA_SR, fid))
        prep = override.value if override else classify("", desc).value.value
        prep_source = "manual" if override else "auto"

        rows.append(
            {
                "source_id": USDA_SR_ID,
                "source_ref": fid,
                "code": None,
                "stt": None,
                "name_vi": display_name,
                "name_en": desc[:255],
                "name_original": desc[:500],
                "name_search": normalize_search(display_name)[:255],
                "group_code": None,
                "group_name": group_name,
                "refuse_pct": None,
                "water_g": v.get("water_g"),
                "energy_kcal": v.get("energy_kcal"),
                "protein_g": v.get("protein_g"),
                "fat_g": v.get("fat_g"),
                "carb_g": carb_g,
                "carb_total_g": v.get("carb_total_g"),
                "fiber_g": v.get("fiber_g"),
                "ash_g": v.get("ash_g"),
                "source_page": None,
                "quality_flags": flags or None,
                "preparation": prep,
                "preparation_source": prep_source,
            }
        )
    return rows


async def ingest_full_usda(sr_dir: Path = DEFAULT_SR_DIR) -> tuple[int, int]:
    rows = build_full_sr_legacy_rows(sr_dir)
    async with AsyncSessionLocal() as session:
        existing = set(
            (await session.execute(select(Food.source_ref).where(Food.source_id == USDA_SR_ID))).scalars()
        )
        for i in range(0, len(rows), BATCH_SIZE):
            chunk = rows[i : i + BATCH_SIZE]
            stmt = insert(Food).values(chunk)
            manual = Food.preparation_source == "manual"
            update_cols = {c: stmt.excluded[c] for c in chunk[0] if c not in ("source_id", "source_ref")}
            update_cols["preparation"] = case((manual, Food.preparation), else_=stmt.excluded.preparation)
            update_cols["preparation_source"] = case(
                (manual, Food.preparation_source), else_=stmt.excluded.preparation_source
            )
            update_cols["updated_at"] = func.now()
            await session.execute(
                stmt.on_conflict_do_update(
                    index_elements=[Food.source_id, Food.source_ref],
                    set_=update_cols,
                )
            )
        await session.commit()
    refs = {r["source_ref"] for r in rows}
    inserted = len(refs - existing)
    updated = len(refs & existing)
    return inserted, updated


async def _main() -> None:
    try:
        inserted, updated = await ingest_full_usda()
        print(f"USDA SR Legacy ingest complete: inserted={inserted}, updated={updated}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())

