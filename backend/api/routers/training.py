"""API chương trình tập luyện (9a: xem chương trình; 9b: theo chương trình, đánh dấu hoàn thành). Cần đăng nhập.

Chỉ chương trình published; chưa published hay không tồn tại đều trả 404. Không lọc theo tuổi.
user_id luôn lấy từ token; enrollment của người khác trả 404.
"""
import uuid
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import get_current_user
from api.schemas.training import (
    CurrentEnrollmentOut, EnrollmentOut, ProgramDayOut, ProgramDetailOut, ProgramSummaryOut, StartEnrollmentIn,
    RecommendationOut, TrainingWeekSummaryOut, WorkoutLogCreate, WorkoutLogOut, WorkoutLogsOut, WorkoutLogUpdate,
)
from core.database import get_db
from models.user import User
from services.training import catalog
from services.training import progress as progress_service
from services.training import recommend as recommend_service
from services.training import workouts as workout_service

router = APIRouter(prefix="/training", tags=["Training"])

NOT_FOUND = "Không tìm thấy chương trình hoặc ngày tập."


@router.get("/programs", response_model=list[ProgramSummaryOut])
async def list_programs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await catalog.list_programs(db)


@router.get("/programs/{slug}", response_model=ProgramDetailOut)
async def get_program(
    slug: str = Path(..., max_length=60),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        detail = await catalog.program_detail(db, slug)
    except catalog.ProgramNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    detail["my_enrollment"] = await progress_service.latest_for_program(db, current_user.id, slug)
    return detail


@router.get("/programs/{slug}/days/{day_number}", response_model=ProgramDayOut)
async def get_program_day(
    slug: str = Path(..., max_length=60),
    day_number: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await catalog.program_day(db, slug, day_number)
    except catalog.ProgramNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)


@router.get("/recommendation", response_model=RecommendationOut)
async def get_recommendation(
    experience: Optional[Literal["regular", "new"]] = Query(
        None, description="regular = đã tập đều vài tháng qua, new = mới bắt đầu; bỏ trống nếu chưa trả lời"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Gợi ý chương trình từ hồ sơ của chính người dùng (đọc từ DB). Không sửa hồ sơ."""
    return await recommend_service.recommendation_for_user(db, current_user.id, experience)


# ── Theo chương trình (9b) ───────────────────────────────────────────────────

async def _run(db: AsyncSession, coro):
    try:
        result = await coro
    except progress_service.TrainingError as exc:
        # get_db rollback khi có exception (kể cả lần đổi sang abandoned trước khi gặp xung đột)
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    await db.commit()
    return result


@router.post("/enrollments", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
async def start_enrollment(
    body: StartEnrollmentIn,
    replace: bool = Query(False, description="true: chuyển enrollment đang active sang abandoned rồi bắt đầu mới"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _run(db, progress_service.start(db, current_user.id, body.program_slug, replace))


@router.get("/enrollments/current", response_model=CurrentEnrollmentOut)
async def get_current_enrollment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"enrollment": await progress_service.current(db, current_user.id)}


@router.post("/enrollments/{enrollment_id}/days/{day_number}/complete", response_model=EnrollmentOut)
async def complete_day(
    enrollment_id: uuid.UUID,
    day_number: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _run(db, progress_service.complete_day(db, current_user.id, enrollment_id, day_number))


@router.delete("/enrollments/{enrollment_id}/days/{day_number}", response_model=EnrollmentOut)
async def uncomplete_day(
    enrollment_id: uuid.UUID,
    day_number: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _run(db, progress_service.uncomplete_day(db, current_user.id, enrollment_id, day_number))


@router.get("/summary", response_model=TrainingWeekSummaryOut)
async def get_training_summary(
    week_start: Optional[date] = Query(None, description="Thứ Hai YYYY-MM-DD; mặc định tuần hiện tại (giờ VN)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await progress_service.weekly_summary(db, current_user.id, week_start)
    except progress_service.TrainingDateError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)


# ── Nhật ký buổi tập tự do ───────────────────────────────────────────────────

@router.post("/logs", response_model=WorkoutLogOut, status_code=status.HTTP_201_CREATED)
async def create_workout_log(
    body: WorkoutLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        workout = await workout_service.create_workout(
            db=db,
            user_id=current_user.id,
            activity_name=body.activity_name,
            duration_min=body.duration_min,
            category=body.category,
            intensity=body.intensity,
            trained_on=body.trained_on,
            notes=body.notes,
        )
    except workout_service.WorkoutValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    await db.commit()
    return workout


@router.get("/logs", response_model=WorkoutLogsOut)
async def list_workout_logs(
    day: Optional[date] = Query(None, alias="date", description="Lọc theo một ngày YYYY-MM-DD (giờ VN)"),
    week_start: Optional[date] = Query(None, description="Lọc theo tuần bắt đầu từ thứ Hai YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        start_day, end_day, items = await workout_service.list_workouts(db, current_user.id, day=day, week_start=week_start)
    except workout_service.WorkoutValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return WorkoutLogsOut(start_date=start_day, end_date=end_day, items=items)


@router.patch("/logs/{workout_id}", response_model=WorkoutLogOut)
async def update_workout_log(
    workout_id: uuid.UUID,
    body: WorkoutLogUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clear_notes = "notes" in body.model_fields_set and body.notes is None
    try:
        workout = await workout_service.update_workout(
            db=db,
            user_id=current_user.id,
            workout_id=workout_id,
            activity_name=body.activity_name,
            duration_min=body.duration_min,
            category=body.category,
            intensity=body.intensity,
            notes=body.notes,
            clear_notes=clear_notes,
        )
    except workout_service.WorkoutNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy buổi tập.")
    except workout_service.WorkoutValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    await db.commit()
    return workout


@router.delete("/logs/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout_log(
    workout_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await workout_service.delete_workout(db, current_user.id, workout_id)
    except workout_service.WorkoutNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy buổi tập.")
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
