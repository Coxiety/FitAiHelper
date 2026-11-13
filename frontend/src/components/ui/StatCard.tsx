import { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface StatCardProgress {
  value: number;
  max: number | null | undefined;
  label: string;
}

export interface StatCardProps {
  label: string;
  value: ReactNode;
  unit?: string;
  hint?: ReactNode;
  icon?: ReactNode;
  emphasis?: "default" | "accent";
  progress?: StatCardProgress;
  status?: "normal" | "over";
  /** Màu viền cánh hoa cho từng loại chỉ số */
  petalColor?: string;
  className?: string;
}

export function isValidTarget(max: number | null | undefined): max is number {
  return typeof max === "number" && Number.isFinite(max) && max > 0;
}

/**
 * Widget chỉ số thiết kế theo phong cách Petal Line-Art (không đóng khung hộp chữ nhật cứng nhắc).
 * Biểu tượng nằm trong hình giọt nước/cánh hoa viền mảnh, thông số nổi trực tiếp trên nền thoáng.
 */
export function StatCard({
  label,
  value,
  unit,
  hint,
  icon,
  emphasis = "default",
  progress,
  status = "normal",
  petalColor = "#2ebd85",
  className,
}: StatCardProps) {
  const showBar = progress !== undefined && isValidTarget(progress.max);
  const pct = showBar ? Math.min(100, Math.max(0, (progress.value / (progress.max as number)) * 100)) : 0;

  return (
    <div
      className={cn(
        "group relative flex items-center gap-4 rounded-2xl border border-line/60 bg-surface/75 px-4 py-3.5 backdrop-blur-sm transition-all hover:border-line hover:bg-surface",
        className
      )}
    >
      {icon && (
        <div
          aria-hidden
          style={{ borderColor: petalColor, color: petalColor }}
          className="flex h-13 w-13 shrink-0 -rotate-12 items-center justify-center rounded-[50%_50%_12%_50%] border-2 bg-surface shadow-2xs transition-transform group-hover:rotate-0"
        >
          <span className="rotate-12 transition-transform group-hover:rotate-0">{icon}</span>
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted">{label}</p>
        <p
          className={cn(
            "mt-0.5 font-numeric text-xl font-bold tabular-nums",
            emphasis === "accent" ? "text-accent-700" : "text-ink"
          )}
        >
          {value}
          {unit && <span className="ml-1 text-xs font-medium text-muted">{unit}</span>}
        </p>
        {showBar && (
          <div
            className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-line/60"
            role="progressbar"
            aria-label={progress.label}
            aria-valuenow={Math.round(pct)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${pct}%`,
                backgroundColor: status === "over" ? "#d9822b" : petalColor,
              }}
            />
          </div>
        )}
        {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
      </div>
    </div>
  );
}
