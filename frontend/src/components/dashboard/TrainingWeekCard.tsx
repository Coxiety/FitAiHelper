"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fullDate } from "@/lib/progress";
import { trainingApi, type TrainingWeekSummary } from "@/lib/training";
import { Button } from "@/components/ui/Button";
import { WorkoutLogModal } from "@/components/training/WorkoutLogModal";

/** Thẻ "Tập luyện tuần này" (tuần thứ Hai → Chủ nhật, giờ VN). Không có dữ liệu thì không hiện 0.
 *  Không so sánh "đạt / chưa đạt" khuyến nghị và không ước tính kcal. */
export function TrainingWeekCard({ onUnauthorized }: { onUnauthorized: () => void }) {
  const [week, setWeek] = useState<TrainingWeekSummary | null>(null);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);

  const loadSummary = useCallback(() => {
    trainingApi.summary().then((data) => {
      setWeek(data);
      setError("");
    }).catch((err) => {
      if (err?.status === 401) return onUnauthorized();
      setError("Không tải được số liệu tập luyện.");
    });
  }, [onUnauthorized]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const hasData =
    week !== null && (week.active_dates !== null || week.completed_days !== null || (week.workout_sessions ?? 0) > 0);
  const missing = week?.days_without_minutes ?? 0;
  const details: string[] = [];
  if (week?.completed_days) details.push(`${week.completed_days} ngày giáo án`);
  if (week?.workout_sessions) details.push(`${week.workout_sessions} buổi tự do`);

  return (
    <section className="h-full rounded-card border border-line bg-surface p-5 shadow-card sm:p-6" aria-labelledby="training-week-title">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="training-week-title" className="text-base font-semibold text-ink">Tập luyện tuần này</h2>
        {week && (
          <span className="text-xs text-muted">{fullDate(week.week_start)} – {fullDate(week.week_end)}</span>
        )}
      </div>
      {error && <p className="text-sm text-red-700">{error}</p>}
      {!week && !error && <p className="text-sm text-muted">Đang tải…</p>}
      {week && !hasData && <p className="text-sm text-muted">Chưa có dữ liệu.</p>}
      {week && hasData && (
        <div className="space-y-1 text-sm text-ink">
          <p>
            Đã tập <strong>{week.active_dates}</strong> ngày
            {details.length > 0 && ` (${details.join(" + ")})`}.
          </p>
          {week.total_minutes !== null ? (
            <p>
              Tổng <strong>{week.total_minutes}</strong> phút bạn đã ghi nhận.
              {missing > 0 && (
                <span className="block text-xs text-muted">chưa tính {missing} ngày chưa đủ thời lượng</span>
              )}
            </p>
          ) : (
            <p className="text-muted">Chưa có dữ liệu thời lượng.</p>
          )}
        </div>
      )}
      <p className="mt-3 text-xs text-muted">
        WHO khuyến nghị người lớn 150-300 phút hoạt động thể lực vừa mỗi tuần; số phút ở đây là bạn tự ghi nhận và gồm
        cả bài không phải aerobic, nên chỉ để tham khảo.
      </p>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <Link href="/training" className="text-sm font-medium text-brand-700 hover:text-brand-800">
          Xem chương trình tập →
        </Link>
        <Button size="sm" variant="secondary" onClick={() => setModalOpen(true)}>
          + Ghi buổi tập
        </Button>
      </div>
      <WorkoutLogModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSaved={() => loadSummary()}
      />
    </section>
  );
}
