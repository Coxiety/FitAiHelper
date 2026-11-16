"""Tests CRUD nhật ký buổi tập tự do (/api/v1/training/logs), tổng hợp tuần & công cụ agent log_workout."""
from __future__ import annotations

from datetime import date, datetime, timezone

from services import meals as meal_service
from services.agent_actions import log_workout_for_user
from services.training.progress import build_week_summary
from tests.test_meals_api import client, require_postgres  # noqa: F401
from tests.test_training_enrollments import alice, bob  # noqa: F401

LOGS_URL = "/api/v1/training/logs"
SUMMARY_URL = "/api/v1/training/summary"
MON = date(2026, 11, 2)
MON_1000_VN = datetime(2026, 11, 2, 3, 0, tzinfo=timezone.utc)


def test_build_week_summary_merges_program_and_free_workouts():
    out = build_week_summary(
        MON,
        rows=[(MON, 20)],
        workout_rows=[(MON, 30), (date(2026, 11, 4), 45)],
    )
    assert out["completed_days"] == 1
    assert out["workout_sessions"] == 2
    assert out["active_dates"] == 2
    assert out["total_minutes"] == 95
    assert out["days_without_minutes"] == 0
    by_date = {d["date"]: d for d in out["series"]}
    assert by_date["2026-11-02"]["minutes"] == 50
    assert by_date["2026-11-04"]["minutes"] == 45


async def test_workout_log_crud_and_user_isolation(client, alice, bob, monkeypatch):
    monkeypatch.setattr(meal_service, "utc_now", lambda: MON_1000_VN)

    res = await client.post(
        LOGS_URL,
        headers=alice,
        json={
            "activity_name": "Chạy bộ công viên",
            "duration_min": 35,
            "category": "cardio",
            "intensity": "moderate",
            "notes": "5km nhẹ nhàng",
        },
    )
    assert res.status_code == 201
    created = res.json()
    assert created["activity_name"] == "Chạy bộ công viên"
    assert created["duration_min"] == 35
    assert created["trained_on"] == "2026-11-02"
    wid = created["id"]

    # Danh sách tuần hiện tại chứa buổi tập vừa tạo
    listed = (await client.get(LOGS_URL, headers=alice)).json()
    assert [i["id"] for i in listed["items"]] == [wid]

    # Tổng hợp tuần tính cả buổi tập tự do khi chưa theo chương trình nào
    summary = (await client.get(SUMMARY_URL, headers=alice)).json()
    assert summary["completed_days"] is None
    assert summary["workout_sessions"] == 1
    assert summary["active_dates"] == 1
    assert summary["total_minutes"] == 35

    # User khác không thấy hoặc sửa/xoá được (trả 404)
    bob_list = (await client.get(LOGS_URL, headers=bob)).json()
    assert bob_list["items"] == []
    assert (await client.patch(f"{LOGS_URL}/{wid}", headers=bob, json={"duration_min": 10})).status_code == 404
    assert (await client.delete(f"{LOGS_URL}/{wid}", headers=bob)).status_code == 404

    # Alice sửa thành công
    upd = await client.patch(f"{LOGS_URL}/{wid}", headers=alice, json={"duration_min": 50, "intensity": "vigorous"})
    assert upd.status_code == 200
    assert upd.json()["duration_min"] == 50 and upd.json()["intensity"] == "vigorous"

    summary_after = (await client.get(SUMMARY_URL, headers=alice)).json()
    assert summary_after["total_minutes"] == 50

    # Alice xoá
    assert (await client.delete(f"{LOGS_URL}/{wid}", headers=alice)).status_code == 204
    empty = (await client.get(SUMMARY_URL, headers=alice)).json()
    assert empty["active_dates"] is None and empty["total_minutes"] is None


async def test_workout_log_validation_rejects_bad_duration_and_future_date(client, alice, monkeypatch):
    monkeypatch.setattr(meal_service, "utc_now", lambda: MON_1000_VN)
    assert (
        await client.post(LOGS_URL, headers=alice, json={"activity_name": "Gym", "duration_min": 0})
    ).status_code == 422
    assert (
        await client.post(LOGS_URL, headers=alice, json={"activity_name": "Gym", "duration_min": 601})
    ).status_code == 422
    assert (
        await client.post(
            LOGS_URL,
            headers=alice,
            json={"activity_name": "Gym", "duration_min": 45, "trained_on": "2026-11-10"},
        )
    ).status_code == 422


async def test_agent_action_log_workout_for_user(db_session, client, alice, monkeypatch):
    import uuid
    from jose import jwt

    monkeypatch.setattr(meal_service, "utc_now", lambda: MON_1000_VN)
    token = alice["Authorization"].split(" ", 1)[1]
    uid = uuid.UUID(jwt.get_unverified_claims(token)["sub"])
    res = await log_workout_for_user(
        db=db_session,
        user_id=uid,
        activity_name="Tập thân trên",
        duration_min=40,
        intensity="nặng",
        category="gym",
        notes="4 hiệp bench press",
    )
    assert res["status"] == "logged"
    assert res["activity_name"] == "Tập thân trên"
    assert res["duration_min"] == 40
    assert res["intensity"] == "vigorous"
    assert res["category"] == "strength"

    listed = (await client.get(LOGS_URL, headers=alice)).json()
    assert any(item["id"] == res["workout_id"] for item in listed["items"])
