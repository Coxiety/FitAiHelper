"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { WorkoutLogModal } from "@/components/training/WorkoutLogModal";
import {
  WORKOUT_CATEGORY_LABELS,
  WORKOUT_INTENSITY_LABELS,
  friendlyTrainingError,
  trainingApi,
  type WorkoutLogIntensity,
  type WorkoutLogItem,
} from "@/lib/training";
import { fullDate } from "@/lib/progress";

const INTENSITY_TONE: Record<WorkoutLogIntensity, "neutral" | "brand" | "accent"> = {
  light: "neutral",
  moderate: "brand",
  vigorous: "accent",
};

/** Nhật ký các buổi tập tự do trong tuần hiện tại trên trang /training. */
export function WorkoutLogsSection({
  onUnauthorized,
  refreshKey = 0,
}: {
  onUnauthorized: () => void;
  refreshKey?: number;
}) {
  const [items, setItems] = useState<WorkoutLogItem[] | null>(null);
  const [range, setRange] = useState<{ start: string; end: string } | null>(null);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadLogs = useCallback(() => {
    trainingApi
      .listWorkouts()
      .then((res) => {
        setItems(res.items);
        setRange({ start: res.start_date, end: res.end_date });
        setError("");
      })
      .catch((err) => {
        if (err?.status === 401) return onUnauthorized();
        setError("Không tải được nhật ký buổi tập.");
      });
  }, [onUnauthorized]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs, refreshKey]);

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    setError("");
    try {
      await trainingApi.deleteWorkout(id);
      setItems((prev) => (prev ? prev.filter((item) => item.id !== id) : prev));
    } catch (err) {
      setError(friendlyTrainingError(err, "Không xoá được buổi tập."));
    } finally {
      setDeletingId(null);
    }
  };

  const totalMinutes = items?.reduce((sum, x) => sum + x.duration_min, 0) ?? 0;

  return (
    <section
      className="rounded-card border border-line bg-surface p-5 shadow-card sm:p-6"
      aria-labelledby="workout-logs-title"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="workout-logs-title" className="text-base font-semibold text-ink">
            Nhật ký buổi tập tự do tuần này
          </h2>
          {range && (
            <p className="text-xs text-muted">
              {fullDate(range.start)} – {fullDate(range.end)}
              {items && items.length > 0 && ` · ${items.length} buổi · ${totalMinutes} phút`}
            </p>
          )}
        </div>
        <Button size="sm" onClick={() => setModalOpen(true)}>
          + Ghi buổi tập
        </Button>
      </div>

      {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
      {items === null && !error && <p className="mt-3 text-sm text-muted">Đang tải nhật ký…</p>}

      {items && items.length === 0 && (
        <p className="mt-3 text-sm text-muted">
          Chưa có buổi tập tự do nào trong tuần này. Bạn có thể bấm “+ Ghi buổi tập” hoặc nhắn trực tiếp cho Trợ lý
          FitAI (vd: “hôm nay chạy bộ 30 phút”).
        </p>
      )}

      {items && items.length > 0 && (
        <ul className="mt-4 divide-y divide-line">
          {items.map((w) => (
            <li key={w.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm">
              <div className="space-y-0.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-ink">{w.activity_name}</span>
                  <Badge tone="neutral">{WORKOUT_CATEGORY_LABELS[w.category] ?? w.category}</Badge>
                  <Badge tone={INTENSITY_TONE[w.intensity]}>{WORKOUT_INTENSITY_LABELS[w.intensity]}</Badge>
                </div>
                <p className="text-xs text-muted">
                  {fullDate(w.trained_on)} · <strong>{w.duration_min} phút</strong>
                  {w.notes ? ` · ${w.notes}` : ""}
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleDelete(w.id)}
                disabled={deletingId === w.id}
                className="rounded-control px-2 py-1 text-xs text-muted transition-colors hover:bg-red-50 hover:text-red-700 disabled:opacity-50"
              >
                {deletingId === w.id ? "Đang xoá…" : "Xoá"}
              </button>
            </li>
          ))}
        </ul>
      )}

      <WorkoutLogModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSaved={(created) => {
          setItems((prev) => (prev ? [created, ...prev] : [created]));
        }}
      />
    </section>
  );
}
