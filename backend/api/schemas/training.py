import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from models.training_progress import MAX_MINUTES_DONE, WorkoutCategory, WorkoutIntensity


class ProgramSummaryOut(BaseModel):
    slug: str
    title: str
    description: str
    goal_tag: str
    level: str
    intensity_label: str
    duration_days: int
    training_days: int
    total_minutes: Optional[int]          # None khi không mục nào có thời lượng
    required_minutes: Optional[int]
    items_without_duration: int


class ProgramDaySummaryOut(BaseModel):
    day_number: int
    is_rest: bool
    note: Optional[str]
    items_count: int
    total_minutes: Optional[int]
    required_minutes: Optional[int]
    items_without_duration: int


class CompletedDayOut(BaseModel):
    day_number: int
    completed_on: str
    minutes_done: Optional[int]           # None khi có mục bắt buộc thiếu thời lượng


class EnrollmentOut(BaseModel):
    id: str
    program_slug: str
    program_title: str
    status: str
    started_on: str
    ended_on: Optional[str]
    available: bool                       # False khi chương trình hiện là draft
    schedule_changed: bool                # có ngày đã đánh dấu không còn được tính (lịch đổi)
    message: Optional[str]
    training_days_total: int
    training_days_done: int
    completed_days: list[CompletedDayOut]
    next_day: Optional[int]


class ProgramDetailOut(ProgramSummaryOut):
    days: list[ProgramDaySummaryOut]
    my_enrollment: Optional[EnrollmentOut] = None     # enrollment gần nhất của người dùng với chương trình này


class CurrentEnrollmentOut(BaseModel):
    enrollment: Optional[EnrollmentOut]


class StartEnrollmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    program_slug: str = Field(..., min_length=1, max_length=60)


class WeekDayOut(BaseModel):
    date: str
    completed_days: Optional[int]
    minutes: Optional[int]
    days_without_minutes: Optional[int]


class TrainingWeekSummaryOut(BaseModel):
    week_start: str
    week_end: str
    completed_days: Optional[int]         # số ngày chương trình đã đánh dấu; None khi không có dữ liệu
    workout_sessions: Optional[int] = None  # số buổi tập tự do đã ghi; None khi không có
    active_dates: Optional[int]           # số ngày lịch có đánh dấu hoặc ghi buổi tập
    total_minutes: Optional[int]          # cộng các ngày/buổi có thời lượng
    days_without_minutes: Optional[int]
    series: list[WeekDayOut]


class DayItemOut(BaseModel):
    position: int
    label: str
    video_title: str
    channel: Optional[str]
    category: Optional[str]
    duration_min: Optional[int]
    required: bool
    url: str
    youtube_id: str


class ProgramDayOut(BaseModel):
    program_slug: str
    program_title: str
    goal_tag: str
    duration_days: int
    day_number: int
    is_rest: bool
    note: Optional[str]
    total_minutes: Optional[int]
    required_minutes: Optional[int]
    items_without_duration: int
    items: list[DayItemOut]


class RecommendedProgramOut(BaseModel):
    slug: str
    title: str
    duration_days: int
    level: str
    goal_tag: str


class RecommendationOut(BaseModel):
    primary: Optional[RecommendedProgramOut]           # None: không gợi ý (xem reason)
    alternative: Optional[RecommendedProgramOut]
    reason_code: str
    reason: str
    notes: list[str]
    experience: Optional[str]


class WorkoutLogCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_name: str = Field(..., min_length=1, max_length=120)
    duration_min: int = Field(..., ge=1, le=MAX_MINUTES_DONE)
    category: WorkoutCategory = WorkoutCategory.OTHER
    intensity: WorkoutIntensity = WorkoutIntensity.MODERATE
    trained_on: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=300)


class WorkoutLogUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_name: Optional[str] = Field(None, min_length=1, max_length=120)
    duration_min: Optional[int] = Field(None, ge=1, le=MAX_MINUTES_DONE)
    category: Optional[WorkoutCategory] = None
    intensity: Optional[WorkoutIntensity] = None
    notes: Optional[str] = Field(None, max_length=300)


class WorkoutLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trained_on: date
    activity_name: str
    category: WorkoutCategory
    duration_min: int
    intensity: WorkoutIntensity
    notes: Optional[str]
    created_at: datetime


class WorkoutLogsOut(BaseModel):
    start_date: date
    end_date: date
    items: list[WorkoutLogOut]
