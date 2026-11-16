"""Nhật ký buổi tập tự do của người dùng (WorkoutLog).

- Chỉ ghi nhận hoạt động, thể loại, thời lượng (1–600 phút), cường độ và ghi chú; KHÔNG ước tính kcal đốt.
- user_id luôn lấy từ JWT; bản ghi của user khác coi như không tồn tại (WorkoutNotFoundError → 404).
- Ngày theo giờ Việt Nam (today_vn / check_eaten_on dùng chung từ services.meals).
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.training_progress import MAX_MINUTES_DONE, WorkoutCategory, WorkoutIntensity, WorkoutLog
from services import meals as meal_service
from services.progress import monday_of


class WorkoutNotFoundError(LookupError):
    """Không tìm thấy buổi tập với id này của user hiện tại."""


class WorkoutValidationError(ValueError):
    """Dữ liệu buổi tập không hợp lệ."""


_CATEGORY_ALIASES: dict[str, WorkoutCategory] = {
    "cardio": WorkoutCategory.CARDIO,
    "tim mach": WorkoutCategory.CARDIO,
    "chay": WorkoutCategory.CARDIO,
    "dap xe": WorkoutCategory.CARDIO,
    "boi": WorkoutCategory.CARDIO,
    "strength": WorkoutCategory.STRENGTH,
    "suc manh": WorkoutCategory.STRENGTH,
    "gym": WorkoutCategory.STRENGTH,
    "ta": WorkoutCategory.STRENGTH,
    "mobility": WorkoutCategory.MOBILITY,
    "gian co": WorkoutCategory.MOBILITY,
    "yoga": WorkoutCategory.MOBILITY,
    "pilates": WorkoutCategory.MOBILITY,
    "sport": WorkoutCategory.SPORT,
    "the thao": WorkoutCategory.SPORT,
    "bong da": WorkoutCategory.SPORT,
    "cau long": WorkoutCategory.SPORT,
    "other": WorkoutCategory.OTHER,
    "khac": WorkoutCategory.OTHER,
}

_INTENSITY_ALIASES: dict[str, WorkoutIntensity] = {
    "light": WorkoutIntensity.LIGHT,
    "nhe": WorkoutIntensity.LIGHT,
    "nhẹ": WorkoutIntensity.LIGHT,
    "easy": WorkoutIntensity.LIGHT,
    "moderate": WorkoutIntensity.MODERATE,
    "vua": WorkoutIntensity.MODERATE,
    "vừa": WorkoutIntensity.MODERATE,
    "medium": WorkoutIntensity.MODERATE,
    "vigorous": WorkoutIntensity.VIGOROUS,
    "nang": WorkoutIntensity.VIGOROUS,
    "nặng": WorkoutIntensity.VIGOROUS,
    "manh": WorkoutIntensity.VIGOROUS,
    "mạnh": WorkoutIntensity.VIGOROUS,
    "hard": WorkoutIntensity.VIGOROUS,
    "high": WorkoutIntensity.VIGOROUS,
}


def normalize_workout_category(raw: str | WorkoutCategory | None) -> WorkoutCategory:
    if isinstance(raw, WorkoutCategory):
        return raw
    val = (raw or "").strip().lower()
    if val in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[val]
    try:
        return WorkoutCategory(val)
    except ValueError:
        return WorkoutCategory.OTHER


def normalize_workout_intensity(raw: str | WorkoutIntensity | None) -> WorkoutIntensity:
    if isinstance(raw, WorkoutIntensity):
        return raw
    val = (raw or "").strip().lower()
    if val in _INTENSITY_ALIASES:
        return _INTENSITY_ALIASES[val]
    try:
        return WorkoutIntensity(val)
    except ValueError:
        return WorkoutIntensity.MODERATE


def _validate_duration(duration_min: int) -> int:
    if not 1 <= int(duration_min) <= MAX_MINUTES_DONE:
        raise WorkoutValidationError(f"Thời lượng tập phải từ 1 đến {MAX_MINUTES_DONE} phút.")
    return int(duration_min)


def _check_trained_on(day: date | None) -> date:
    target = day or meal_service.today_vn()
    try:
        return meal_service.check_eaten_on(target)
    except meal_service.MealDateError as exc:
        raise WorkoutValidationError(str(exc)) from exc


async def _get_own_workout(db: AsyncSession, user_id: uuid.UUID, workout_id: uuid.UUID) -> WorkoutLog:
    res = await db.execute(select(WorkoutLog).where(WorkoutLog.id == workout_id, WorkoutLog.user_id == user_id))
    workout = res.scalar_one_or_none()
    if workout is None:
        raise WorkoutNotFoundError("Không tìm thấy buổi tập.")
    return workout


async def create_workout(
    db: AsyncSession,
    user_id: uuid.UUID,
    activity_name: str,
    duration_min: int,
    category: WorkoutCategory = WorkoutCategory.OTHER,
    intensity: WorkoutIntensity = WorkoutIntensity.MODERATE,
    trained_on: date | None = None,
    notes: str | None = None,
) -> WorkoutLog:
    name = (activity_name or "").strip()
    if not name:
        raise WorkoutValidationError("Tên hoạt động không được để trống.")
    workout = WorkoutLog(
        user_id=user_id,
        trained_on=_check_trained_on(trained_on),
        activity_name=name[:120],
        category=category,
        duration_min=_validate_duration(duration_min),
        intensity=intensity,
        notes=notes.strip()[:300] if notes and notes.strip() else None,
    )
    db.add(workout)
    await db.flush()
    await db.refresh(workout)
    return workout


async def list_workouts(
    db: AsyncSession,
    user_id: uuid.UUID,
    day: date | None = None,
    week_start: date | None = None,
) -> tuple[date, date, list[WorkoutLog]]:
    """Liệt kê buổi tập của user theo ngày cụ thể hoặc theo tuần (mặc định tuần hiện tại giờ VN)."""
    if day is not None:
        start_day, end_day = day, day
    else:
        start_day = week_start or monday_of(meal_service.today_vn())
        if start_day.weekday() != 0:
            raise WorkoutValidationError("week_start phải là thứ Hai.")
        end_day = start_day + timedelta(days=6)

    stmt = (
        select(WorkoutLog)
        .where(
            WorkoutLog.user_id == user_id,
            WorkoutLog.trained_on >= start_day,
            WorkoutLog.trained_on <= end_day,
        )
        .order_by(WorkoutLog.trained_on.desc(), WorkoutLog.created_at.desc(), WorkoutLog.id)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return start_day, end_day, rows


async def update_workout(
    db: AsyncSession,
    user_id: uuid.UUID,
    workout_id: uuid.UUID,
    activity_name: str | None = None,
    duration_min: int | None = None,
    category: WorkoutCategory | None = None,
    intensity: WorkoutIntensity | None = None,
    notes: str | None = None,
    clear_notes: bool = False,
) -> WorkoutLog:
    workout = await _get_own_workout(db, user_id, workout_id)
    if activity_name is not None:
        cleaned = activity_name.strip()
        if not cleaned:
            raise WorkoutValidationError("Tên hoạt động không được để trống.")
        workout.activity_name = cleaned[:120]
    if duration_min is not None:
        workout.duration_min = _validate_duration(duration_min)
    if category is not None:
        workout.category = category
    if intensity is not None:
        workout.intensity = intensity
    if clear_notes:
        workout.notes = None
    elif notes is not None:
        workout.notes = notes.strip()[:300] or None
    await db.flush()
    await db.refresh(workout)
    return workout


async def delete_workout(db: AsyncSession, user_id: uuid.UUID, workout_id: uuid.UUID) -> None:
    workout = await _get_own_workout(db, user_id, workout_id)
    await db.delete(workout)
    await db.flush()
