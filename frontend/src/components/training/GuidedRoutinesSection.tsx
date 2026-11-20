"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Pause,
  Play,
  RotateCcw,
  ShieldAlert,
  Sparkles,
  Timer,
  Wind,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { PoseIllustration } from "@/components/training/PoseIllustration";
import { GUIDED_ROUTINES, type GuidedRoutine } from "@/data/guidedRoutines";
import { friendlyTrainingError, trainingApi } from "@/lib/training";
import { cn } from "@/lib/utils";

interface GuidedRoutinesSectionProps {
  onWorkoutLogged: () => void;
  onUnauthorized: () => void;
}

/** Giao diện hướng dẫn từng bước trực quan (Tập thở + Khởi động/Giãn cơ cơ bản, không video). */
export function GuidedRoutinesSection({ onWorkoutLogged, onUnauthorized }: GuidedRoutinesSectionProps) {
  const [selectedId, setSelectedId] = useState<string>(GUIDED_ROUTINES[0].id);
  const routine = GUIDED_ROUTINES.find((r) => r.id === selectedId) ?? GUIDED_ROUTINES[0];

  return (
    <section
      aria-labelledby="guided-practice-title"
      className="rounded-3xl border border-line/75 bg-surface/90 p-5 sm:p-6 shadow-card backdrop-blur-md space-y-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3.5">
        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className="flex h-9 w-9 items-center justify-center rounded-2xl bg-[#2ebd85]/15 text-[#1f9668]"
          >
            <Wind className="h-5 w-5" />
          </span>
          <div>
            <h2 id="guided-practice-title" className="text-lg font-bold tracking-tight text-ink">
              Hướng dẫn Cơ bản Từng bước (Trực quan · Không Video)
            </h2>
            <p className="text-xs sm:text-sm text-muted">
              Tập thở điều hòa nhịp tim và khởi động/giãn cơ trực tiếp bằng nhịp đếm &amp; sơ đồ tư thế
            </p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200">
          <Sparkles className="h-3.5 w-3.5" /> Tương tác trực tiếp
        </span>
      </div>

      {/* Bộ chọn 4 bài cơ bản */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {GUIDED_ROUTINES.map((item) => {
          const active = item.id === routine.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setSelectedId(item.id)}
              aria-pressed={active}
              className={cn(
                "flex flex-col items-start rounded-2xl border p-3.5 text-left transition cursor-pointer",
                active
                  ? "border-2 bg-canvas/85 shadow-sm"
                  : "border-line/75 bg-surface hover:border-gray-300 hover:bg-canvas/50"
              )}
              style={active ? { borderColor: item.accentColor } : undefined}
            >
              <span
                className="rounded-full px-2 py-0.5 text-[10px] font-bold"
                style={{
                  backgroundColor: `${item.accentColor}1a`,
                  color: item.accentColor,
                }}
              >
                {item.badge}
              </span>
              <span className="mt-2 text-sm font-bold text-ink">{item.title}</span>
              <span className="mt-1 text-xs text-muted line-clamp-2">{item.subtitle}</span>
              <span className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-ink/80">
                <Timer className="h-3 w-3" /> {item.durationLabel}
              </span>
            </button>
          );
        })}
      </div>

      {/* Trình hướng dẫn chi tiết theo loại bài */}
      {routine.kind === "breathing" ? (
        <BreathingPlayer
          key={routine.id}
          routine={routine}
          onWorkoutLogged={onWorkoutLogged}
          onUnauthorized={onUnauthorized}
        />
      ) : (
        <StepMobilityPlayer
          key={routine.id}
          routine={routine}
          onWorkoutLogged={onWorkoutLogged}
          onUnauthorized={onUnauthorized}
        />
      )}
    </section>
  );
}

function SaveRoutineButton({
  routine,
  completed,
  onWorkoutLogged,
  onUnauthorized,
}: {
  routine: GuidedRoutine;
  completed: boolean;
  onWorkoutLogged: () => void;
  onUnauthorized: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async () => {
    if (busy || saved) return;
    setBusy(true);
    setError("");
    try {
      await trainingApi.createWorkout({
        activity_name: routine.title,
        duration_min: routine.logMinutes,
        category: "mobility",
        intensity: "light",
        notes: "Hoàn thành hướng dẫn từng bước trực quan",
      });
      setSaved(true);
      onWorkoutLogged();
    } catch (err: any) {
      if (err?.status === 401) return onUnauthorized();
      setError(friendlyTrainingError(err, "Không lưu được buổi tập."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant={completed ? "primary" : "secondary"}
          loading={busy}
          disabled={saved}
          onClick={handleSave}
        >
          <CheckCircle2 className="h-4 w-4" />
          {saved ? "Đã lưu vào nhật ký tuần" : `Lưu buổi tập (${routine.logMinutes} phút)`}
        </Button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

/** Trình hướng dẫn Tập thở trực quan với vòng tròn SVG co giãn theo nhịp đếm. */
function BreathingPlayer({
  routine,
  onWorkoutLogged,
  onUnauthorized,
}: {
  routine: GuidedRoutine;
  onWorkoutLogged: () => void;
  onUnauthorized: () => void;
}) {
  const phases = routine.phases ?? [];
  const totalCycles = routine.cycles ?? 5;
  const [running, setRunning] = useState(false);
  const [cycle, setCycle] = useState(1);
  const [phaseIdx, setPhaseIdx] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(phases[0]?.seconds ?? 4);
  const [finished, setFinished] = useState(false);

  const phase = phases[phaseIdx];

  useEffect(() => {
    if (!running || !phase || finished) return;
    const id = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev > 1) return prev - 1;
        const nextPhaseIdx = phaseIdx + 1;
        if (nextPhaseIdx < phases.length) {
          setPhaseIdx(nextPhaseIdx);
          return phases[nextPhaseIdx].seconds;
        }
        if (cycle < totalCycles) {
          setCycle((c) => c + 1);
          setPhaseIdx(0);
          return phases[0].seconds;
        }
        setRunning(false);
        setFinished(true);
        return 0;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [running, phase, phaseIdx, phases, cycle, totalCycles, finished]);

  const reset = () => {
    setRunning(false);
    setFinished(false);
    setCycle(1);
    setPhaseIdx(0);
    setSecondsLeft(phases[0]?.seconds ?? 4);
  };

  // Tính bán kính co giãn trực quan theo từng pha thở
  const elapsedInPhase = phase ? phase.seconds - secondsLeft : 0;
  const progress = phase ? Math.min(1, Math.max(0, elapsedInPhase / Math.max(phase.seconds, 1))) : 0;
  let orbScale = 0.72;
  if (phase?.key === "inhale") {
    orbScale = 0.68 + 0.32 * progress;
  } else if (phase?.key === "hold") {
    orbScale = 1.0;
  } else if (phase?.key === "exhale") {
    orbScale = 1.0 - 0.32 * progress;
  } else {
    orbScale = 0.68;
  }

  return (
    <div className="grid grid-cols-1 gap-5 rounded-2xl border border-line/70 bg-canvas/55 p-4 sm:p-5 lg:grid-cols-12">
      {/* Cột trái: Vòng tròn nhịp thở animation */}
      <div className="flex flex-col items-center justify-center rounded-2xl border border-line/60 bg-surface p-5 lg:col-span-5">
        <span className="text-xs font-bold uppercase tracking-wider text-muted">
          {finished ? "Hoàn thành bài thở!" : `Chu kỳ ${cycle} / ${totalCycles}`}
        </span>

        <div className="relative my-5 flex h-48 w-48 items-center justify-center">
          <div
            aria-hidden
            className="absolute inset-0 rounded-full transition-transform duration-700 ease-in-out"
            style={{
              transform: `scale(${finished ? 0.9 : orbScale})`,
              backgroundColor: `${phase?.color ?? routine.accentColor}24`,
              border: `3px solid ${phase?.color ?? routine.accentColor}`,
            }}
          />
          <div className="relative z-10 text-center">
            <p className="text-sm font-bold" style={{ color: phase?.color ?? routine.accentColor }}>
              {finished ? "Tuyệt vời!" : phase?.label}
            </p>
            <p className="mt-1 font-numeric text-4xl font-extrabold text-ink">
              {finished ? "✓" : `${secondsLeft}s`}
            </p>
          </div>
        </div>

        {/* Thanh chỉ báo các pha */}
        <div className="mb-4 flex flex-wrap justify-center gap-1.5">
          {phases.map((p, idx) => (
            <span
              key={p.key}
              className={cn(
                "rounded-full border px-2.5 py-0.5 text-[11px] font-semibold transition",
                idx === phaseIdx && !finished ? "text-white" : "border-line bg-canvas text-muted"
              )}
              style={
                idx === phaseIdx && !finished
                  ? { backgroundColor: p.color, borderColor: p.color }
                  : undefined
              }
            >
              {p.label} ({p.seconds}s)
            </span>
          ))}
        </div>

        <div className="flex flex-wrap justify-center gap-2">
          {!finished && (
            <Button type="button" size="sm" onClick={() => setRunning((r) => !r)}>
              {running ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
              {running ? "Tạm dừng" : "Bắt đầu thở"}
            </Button>
          )}
          <Button type="button" size="sm" variant="ghost" onClick={reset}>
            <RotateCcw className="h-4 w-4" /> Đặt lại
          </Button>
        </div>
      </div>

      {/* Cột phải: Hướng dẫn chuẩn bị & chi tiết từng pha */}
      <div className="flex flex-col justify-between space-y-4 lg:col-span-7">
        <div className="space-y-3">
          <div className="rounded-xl border border-line/60 bg-surface p-3.5">
            <p className="text-xs font-bold uppercase tracking-wide text-muted">Hướng dẫn ở pha hiện tại</p>
            <p className="mt-1 text-sm font-semibold text-ink">
              {finished
                ? "Bạn đã hoàn thành đủ các chu kỳ hít thở. Hãy hít thở tự nhiên vài nhịp trước khi đứng dậy."
                : phase?.instruction}
            </p>
          </div>

          <div className="rounded-xl border border-line/60 bg-surface p-3.5">
            <p className="text-xs font-bold uppercase tracking-wide text-muted">Các bước chuẩn bị</p>
            <ol className="mt-1.5 list-decimal space-y-1 pl-5 text-xs sm:text-sm text-ink">
              {routine.setupSteps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ol>
            <p className="mt-2 text-xs text-muted">
              <strong className="text-ink">Lợi ích:</strong> {routine.benefit}
            </p>
          </div>
        </div>

        <SaveRoutineButton
          routine={routine}
          completed={finished}
          onWorkoutLogged={onWorkoutLogged}
          onUnauthorized={onUnauthorized}
        />
      </div>
    </div>
  );
}

/** Trình hướng dẫn Khởi động / Giãn cơ Từng bước kèm SVG tư thế + đồng hồ đếm ngược. */
function StepMobilityPlayer({
  routine,
  onWorkoutLogged,
  onUnauthorized,
}: {
  routine: GuidedRoutine;
  onWorkoutLogged: () => void;
  onUnauthorized: () => void;
}) {
  const steps = routine.steps ?? [];
  const [stepIdx, setStepIdx] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(steps[0]?.durationSec ?? 30);
  const [running, setRunning] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  const step = steps[stepIdx];
  const allDone = completedSteps.length >= steps.length;

  useEffect(() => {
    if (!running || !step) return;
    const id = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev > 1) return prev - 1;
        setRunning(false);
        setCompletedSteps((done) => (done.includes(stepIdx) ? done : [...done, stepIdx]));
        return 0;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [running, step, stepIdx]);

  const goToStep = (nextIdx: number) => {
    if (nextIdx < 0 || nextIdx >= steps.length) return;
    setRunning(false);
    setStepIdx(nextIdx);
    setSecondsLeft(steps[nextIdx].durationSec);
  };

  const pct = step ? Math.round(((step.durationSec - secondsLeft) / Math.max(step.durationSec, 1)) * 100) : 0;

  if (!step) return null;

  return (
    <div className="space-y-4 rounded-2xl border border-line/70 bg-canvas/55 p-4 sm:p-5">
      {/* Thanh các bước tuần tự */}
      <div className="flex flex-wrap items-center gap-2">
        {steps.map((s, idx) => {
          const isCurrent = idx === stepIdx;
          const isDone = completedSteps.includes(idx);
          return (
            <button
              key={s.title}
              type="button"
              onClick={() => goToStep(idx)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold transition cursor-pointer",
                isCurrent
                  ? "text-white"
                  : isDone
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-line bg-surface text-muted hover:text-ink"
              )}
              style={
                isCurrent ? { backgroundColor: routine.accentColor, borderColor: routine.accentColor } : undefined
              }
            >
              <span>{isDone ? "✓" : `${idx + 1}.`}</span>
              <span className="truncate max-w-[160px]">{s.title}</span>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        {/* Cột trái: Minh họa SVG tư thế + Timer đếm ngược */}
        <div className="flex flex-col items-center justify-between rounded-2xl border border-line/60 bg-surface p-4 lg:col-span-5">
          <div className="w-full flex items-center justify-between text-xs text-muted">
            <span className="font-bold uppercase tracking-wide">
              Bước {stepIdx + 1} / {steps.length}
            </span>
            <span className="font-numeric font-bold text-ink">{step.durationSec} giây</span>
          </div>

          <div className="my-3">
            <PoseIllustration pose={step.pose} accent={routine.accentColor} />
          </div>

          {/* Đồng hồ đếm ngược + thanh tiến độ */}
          <div className="w-full space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted">Thời gian còn lại</span>
              <span className="font-numeric text-2xl font-extrabold text-ink">
                {secondsLeft === 0 ? "Xong ✓" : `${secondsLeft}s`}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
              <div
                className="h-full transition-all duration-500"
                style={{ width: `${pct}%`, backgroundColor: routine.accentColor }}
              />
            </div>

            <div className="flex flex-wrap justify-center gap-2 pt-1">
              <Button
                type="button"
                size="sm"
                onClick={() => {
                  if (secondsLeft === 0) setSecondsLeft(step.durationSec);
                  setRunning((r) => !r);
                }}
              >
                {running ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                {running ? "Tạm dừng" : secondsLeft === 0 ? "Tập lại bước này" : "Bắt đầu đếm"}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => {
                  setRunning(false);
                  setSecondsLeft(step.durationSec);
                }}
              >
                <RotateCcw className="h-4 w-4" /> Đặt lại
              </Button>
            </div>
          </div>
        </div>

        {/* Cột phải: Hướng dẫn động tác từng ý, nhịp thở & an toàn */}
        <div className="flex flex-col justify-between space-y-4 lg:col-span-7">
          <div className="space-y-3">
            <div className="rounded-xl border border-line/60 bg-surface p-4">
              <h3 className="text-base font-bold text-ink">{step.title}</h3>
              <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-sm text-ink">
                {step.instructions.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ol>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-emerald-200/80 bg-emerald-50/70 p-3 text-xs">
                <p className="font-bold text-emerald-800 flex items-center gap-1.5">
                  <Wind className="h-3.5 w-3.5" /> Nhịp thở gợi ý
                </p>
                <p className="mt-1 text-emerald-900">{step.breathingCue}</p>
              </div>
              <div className="rounded-xl border border-amber-200/80 bg-amber-50/70 p-3 text-xs">
                <p className="font-bold text-amber-800 flex items-center gap-1.5">
                  <ShieldAlert className="h-3.5 w-3.5" /> Lưu ý an toàn
                </p>
                <p className="mt-1 text-amber-900">{step.safetyTip}</p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <div className="flex items-center gap-2">
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={stepIdx === 0}
                onClick={() => goToStep(stepIdx - 1)}
              >
                <ChevronLeft className="h-4 w-4" /> Bước trước
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={stepIdx >= steps.length - 1}
                onClick={() => {
                  setCompletedSteps((done) => (done.includes(stepIdx) ? done : [...done, stepIdx]));
                  goToStep(stepIdx + 1);
                }}
              >
                Bước tiếp <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

            <SaveRoutineButton
              routine={routine}
              completed={allDone}
              onWorkoutLogged={onWorkoutLogged}
              onUnauthorized={onUnauthorized}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
