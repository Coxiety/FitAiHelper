"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  WORKOUT_CATEGORY_LABELS,
  WORKOUT_INTENSITY_LABELS,
  friendlyTrainingError,
  trainingApi,
  type WorkoutLogCategory,
  type WorkoutLogIntensity,
  type WorkoutLogItem,
} from "@/lib/training";
import { cn } from "@/lib/utils";

const PRESETS: { label: string; category: WorkoutLogCategory; minutes: number }[] = [
  { label: "Chạy bộ", category: "cardio", minutes: 30 },
  { label: "Tập tạ / Gym", category: "strength", minutes: 45 },
  { label: "Đạp xe", category: "cardio", minutes: 35 },
  { label: "Đi bộ nhanh", category: "cardio", minutes: 30 },
  { label: "Yoga / Giãn cơ", category: "mobility", minutes: 25 },
  { label: "Cầu lông / Bóng đá", category: "sport", minutes: 60 },
];

const INTENSITIES: WorkoutLogIntensity[] = ["light", "moderate", "vigorous"];

interface Props {
  open: boolean;
  onClose: () => void;
  onSaved: (item: WorkoutLogItem) => void;
}

/** Hộp thoại ghi nhanh một buổi tập tự do (không ước tính kcal đốt). */
export function WorkoutLogModal({ open, onClose, onSaved }: Props) {
  const [activityName, setActivityName] = useState("");
  const [durationMin, setDurationMin] = useState("30");
  const [category, setCategory] = useState<WorkoutLogCategory>("cardio");
  const [intensity, setIntensity] = useState<WorkoutLogIntensity>("moderate");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  const applyPreset = (p: (typeof PRESETS)[number]) => {
    setActivityName(p.label);
    setCategory(p.category);
    setDurationMin(String(p.minutes));
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = activityName.trim();
    const mins = Number(durationMin);
    if (!trimmed) {
      setError("Vui lòng nhập tên hoạt động tập luyện.");
      return;
    }
    if (!Number.isInteger(mins) || mins < 1 || mins > 600) {
      setError("Thời lượng tập phải là số nguyên từ 1 đến 600 phút.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const created = await trainingApi.createWorkout({
        activity_name: trimmed,
        duration_min: mins,
        category,
        intensity,
        notes: notes.trim() || undefined,
      });
      setActivityName("");
      setDurationMin("30");
      setNotes("");
      onSaved(created);
      onClose();
    } catch (err) {
      setError(friendlyTrainingError(err, "Không lưu được buổi tập. Vui lòng thử lại."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="workout-modal-title"
    >
      <div className="w-full max-w-md rounded-card border border-line bg-surface p-5 shadow-xl sm:p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 id="workout-modal-title" className="text-lg font-semibold text-ink">
            Ghi buổi tập hôm nay
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-control px-2 py-1 text-sm text-muted hover:bg-gray-100 hover:text-ink"
            aria-label="Đóng"
          >
            ✕
          </button>
        </div>

        <div className="mb-3">
          <p className="mb-1.5 text-xs font-medium text-muted">Chọn nhanh</p>
          <div className="flex flex-wrap gap-1.5">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => applyPreset(p)}
                className={cn(
                  "rounded-full border px-2.5 py-1 text-xs transition-colors",
                  activityName === p.label
                    ? "border-brand-600 bg-brand-50 font-medium text-brand-700"
                    : "border-line bg-canvas text-ink hover:bg-gray-50"
                )}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label htmlFor="wk-activity" className="mb-1 block text-xs font-medium text-ink">
              Hoạt động tập luyện *
            </label>
            <Input
              id="wk-activity"
              value={activityName}
              onChange={(e) => setActivityName(e.target.value)}
              placeholder="Ví dụ: Chạy bộ công viên, Tập thân trên…"
              maxLength={120}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="wk-duration" className="mb-1 block text-xs font-medium text-ink">
                Thời lượng (phút) *
              </label>
              <Input
                id="wk-duration"
                type="number"
                min={1}
                max={600}
                value={durationMin}
                onChange={(e) => setDurationMin(e.target.value)}
                required
              />
            </div>

            <div>
              <label htmlFor="wk-category" className="mb-1 block text-xs font-medium text-ink">
                Nhóm bài tập
              </label>
              <Select
                id="wk-category"
                value={category}
                onChange={(e) => setCategory(e.target.value as WorkoutLogCategory)}
              >
                {(Object.keys(WORKOUT_CATEGORY_LABELS) as WorkoutLogCategory[]).map((k) => (
                  <option key={k} value={k}>
                    {WORKOUT_CATEGORY_LABELS[k]}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <div>
            <span className="mb-1 block text-xs font-medium text-ink">Cường độ</span>
            <div className="grid grid-cols-3 gap-2" role="group" aria-label="Cường độ buổi tập">
              {INTENSITIES.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setIntensity(item)}
                  aria-pressed={intensity === item}
                  className={cn(
                    "rounded-control border py-1.5 text-xs font-medium transition-colors",
                    intensity === item
                      ? "border-brand-600 bg-brand-700 text-white"
                      : "border-line bg-canvas text-ink hover:bg-gray-50"
                  )}
                >
                  {WORKOUT_INTENSITY_LABELS[item]}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="wk-notes" className="mb-1 block text-xs font-medium text-ink">
              Ghi chú (tuỳ chọn)
            </label>
            <Input
              id="wk-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Ví dụ: 5km pace 6:30, hoặc 4 hiệp squat"
              maxLength={300}
            />
          </div>

          {error && <p className="text-xs text-red-700">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" size="sm" onClick={onClose} disabled={busy}>
              Huỷ
            </Button>
            <Button type="submit" size="sm" loading={busy}>
              Lưu buổi tập
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
