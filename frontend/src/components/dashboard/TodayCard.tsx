"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { Beef, Droplet, Flame, TriangleAlert, UtensilsCrossed, Wheat } from "lucide-react";
import type { DailySummary, MacroValues } from "@/lib/meals";
import { formatNumber } from "@/lib/progress";
import { isValidTarget } from "@/components/ui/StatCard";
import { cn } from "@/lib/utils";

const MACROS: {
  key: keyof MacroValues;
  label: string;
  unit: string;
  color: string;
  angleDeg: number;
  side: "left" | "right";
  icon: ReactNode;
}[] = [
  {
    key: "energy_kcal",
    label: "Năng lượng (Calo)",
    unit: "kcal",
    color: "#7c5ce6",
    angleDeg: -142,
    side: "left",
    icon: <Flame className="h-6 w-6" strokeWidth={1.85} />,
  },
  {
    key: "protein_g",
    label: "Chất đạm (Protein)",
    unit: "g",
    color: "#2ebd85",
    angleDeg: -38,
    side: "right",
    icon: <Beef className="h-6 w-6" strokeWidth={1.85} />,
  },
  {
    key: "fat_g",
    label: "Chất béo (Fat)",
    unit: "g",
    color: "#d9822b",
    angleDeg: 142,
    side: "left",
    icon: <Droplet className="h-6 w-6" strokeWidth={1.85} />,
  },
  {
    key: "carb_g",
    label: "Tinh bột (Carb)",
    unit: "g",
    color: "#1ca8d4",
    angleDeg: 38,
    side: "right",
    icon: <Wheat className="h-6 w-6" strokeWidth={1.85} />,
  },
];

const FIELD_LABELS: Record<string, string> = {
  age: "tuổi",
  gender: "giới tính",
  height_cm: "chiều cao",
  weight_kg: "cân nặng",
  activity_level: "mức vận động",
  fitness_goal: "mục tiêu",
};

export function ProfileInvite({ missing }: { missing: string[] }) {
  const vnMissing = missing.map((m) => FIELD_LABELS[m] ?? m).join(", ");
  return (
    <div className="mx-auto max-w-lg rounded-full border border-line bg-surface/85 px-4 py-2 text-center text-xs text-muted shadow-2xs backdrop-blur-sm">
      Hồ sơ còn thiếu <span className="font-medium text-ink">{vnMissing}</span> nên chưa tính được mục tiêu TDEE.{" "}
      <Link href="/onboarding" className="font-bold text-brand-700 underline underline-offset-4 hover:text-brand-800">
        Thiết lập ngay →
      </Link>
    </div>
  );
}

/**
 * Sơ đồ Vòng Tròn 4 Cánh Hoa Dinh Dưỡng Hôm Nay (Calo, Protein, Fat, Carb).
 * Thiết kế gọn để đặt vừa vặn ở góc trên bên trái của Dashboard.
 */
export function TodayStats({ summary }: { summary: DailySummary }) {
  const hasLog = summary.entries_count > 0;
  const centerX = 310;
  const centerY = 160;
  const ringRadius = 74;
  const petalDistance = 112;

  return (
    <section aria-label="Dinh dưỡng hôm nay" className="space-y-3">
      {/* Desktop / Tablet: Sơ đồ vòng tròn 4 cánh hoa */}
      <div className="relative mx-auto hidden h-[320px] w-full max-w-[620px] select-none sm:block">
        {/* Vòng tròn mảnh ở tâm */}
        <svg aria-hidden viewBox="0 0 620 320" className="pointer-events-none absolute inset-0 h-full w-full">
          <circle
            cx={centerX}
            cy={centerY}
            r={ringRadius}
            fill="rgba(255, 250, 248, 0.72)"
            stroke="#45413e"
            strokeWidth="2.2"
          />
        </svg>

        {/* Nội dung ở tâm vòng tròn */}
        <Link
          href="/meals"
          title="Nhấn để ghi bữa ăn hôm nay"
          style={{ left: `${centerX}px`, top: `${centerY}px` }}
          className="group absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center justify-center rounded-full p-3 text-center transition-transform hover:scale-105"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border-2 border-[#45413e] bg-surface text-[#45413e] transition-transform group-hover:rotate-6">
            <UtensilsCrossed className="h-4.5 w-4.5" strokeWidth={2} />
          </div>
          <span className="mt-1.5 text-[11px] font-bold uppercase tracking-wider text-ink">
            {hasLog ? `${summary.entries_count} món hôm nay` : "Ghi bữa ăn"}
          </span>
          <span className="mt-0.5 text-[10px] font-medium text-muted">
            {hasLog ? "Nhấn để thêm món" : "Chạm để bắt đầu"}
          </span>
        </Link>

        {/* 4 Cánh Hoa Macro xung quanh vòng tròn */}
        {MACROS.map(({ key, label, unit, color, angleDeg, side, icon }) => {
          const digits = unit === "kcal" ? 0 : 1;
          const eaten = summary.eaten[key];
          const rawTarget = summary.target?.[key];
          const target = isValidTarget(rawTarget) ? rawTarget : null;
          const over = hasLog && target !== null && eaten > target;
          const pct =
            target !== null ? Math.min(100, Math.max(0, ((hasLog ? eaten : 0) / target) * 100)) : 0;

          const rad = (angleDeg * Math.PI) / 180;
          const px = centerX + Math.cos(rad) * petalDistance;
          const py = centerY + Math.sin(rad) * petalDistance;
          const petalRotationDeg = angleDeg + 135;

          return (
            <div
              key={key}
              style={{ left: `${px}px`, top: `${py}px` }}
              className="absolute -translate-x-1/2 -translate-y-1/2 flex items-center"
            >
              {/* Cánh hoa giọt nước hướng tâm */}
              <div
                style={{
                  borderColor: color,
                  color: color,
                  transform: `rotate(${petalRotationDeg}deg)`,
                }}
                className="flex h-17 w-17 shrink-0 items-center justify-center rounded-[50%_50%_4px_50%] border-[2.4px] bg-surface shadow-sm transition-transform duration-200 hover:scale-108"
              >
                <div style={{ transform: `rotate(${-petalRotationDeg}deg)` }}>{icon}</div>
              </div>

              {/* Thông số nổi bên cạnh cánh hoa */}
              <div
                className={cn(
                  "w-[155px]",
                  side === "left" ? "absolute right-full mr-3 text-right" : "absolute left-full ml-3 text-left"
                )}
              >
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted leading-tight">
                  {label}
                </p>
                <p className="mt-0.5 font-numeric text-lg font-bold tabular-nums text-ink">
                  {hasLog ? (
                    <>
                      {formatNumber(eaten, digits)}
                      {target !== null && (
                        <span className="text-xs font-medium text-muted"> / {formatNumber(target, digits)}</span>
                      )}
                      <span className="ml-1 text-xs font-medium text-muted">{unit}</span>
                    </>
                  ) : (
                    <span className="text-sm font-bold text-ink">Chưa ghi</span>
                  )}
                </p>

                {target !== null && (
                  <div
                    className={cn(
                      "mt-1 h-1.5 w-28 overflow-hidden rounded-full bg-line/70",
                      side === "left" ? "ml-auto" : "mr-auto"
                    )}
                    role="progressbar"
                    aria-label={`${label} đã ăn so với mục tiêu`}
                    aria-valuenow={Math.round(pct)}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  >
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: over ? "#d9822b" : color,
                      }}
                    />
                  </div>
                )}

                {over ? (
                  <p className="mt-1 inline-flex items-center gap-1 text-[11px] font-semibold text-accent-800">
                    <TriangleAlert aria-hidden className="h-3 w-3" />
                    Vượt {formatNumber(eaten - target!, digits)} {unit}
                  </p>
                ) : !hasLog && target !== null ? (
                  <p className="mt-0.5 text-[11px] text-muted">
                    Mục tiêu {formatNumber(target, digits)} {unit}
                  </p>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>

      {/* Mobile (< sm): Lưới 2x2 cánh hoa gọn gàng */}
      <div className="grid grid-cols-2 gap-4 sm:hidden">
        {MACROS.map(({ key, label, unit, color, icon }) => {
          const digits = unit === "kcal" ? 0 : 1;
          const eaten = summary.eaten[key];
          const rawTarget = summary.target?.[key];
          const target = isValidTarget(rawTarget) ? rawTarget : null;
          return (
            <div key={key} className="flex flex-col items-center text-center p-2">
              <div
                style={{ borderColor: color, color: color }}
                className="flex h-14 w-14 -rotate-45 items-center justify-center rounded-[50%_50%_4px_50%] border-2 bg-surface shadow-2xs"
              >
                <span className="rotate-45">{icon}</span>
              </div>
              <p className="mt-2 text-[11px] font-bold uppercase tracking-wider text-muted">{label}</p>
              <p className="font-numeric text-base font-bold text-ink">
                {hasLog ? (
                  <>
                    {formatNumber(eaten, digits)}
                    {target !== null && `/${formatNumber(target, digits)}`} {unit}
                  </>
                ) : (
                  "Chưa ghi"
                )}
              </p>
            </div>
          );
        })}
      </div>

      {summary.incomplete_totals && (
        <p className="text-center text-xs text-accent-800">
          ! Tổng chưa đầy đủ: {summary.incomplete_entries} mục thiếu số liệu, chỉ cộng các mục có số liệu.
        </p>
      )}
      {!summary.is_complete && <ProfileInvite missing={summary.missing_fields} />}
    </section>
  );
}
