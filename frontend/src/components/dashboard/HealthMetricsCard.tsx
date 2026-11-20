"use client";

import { useState } from "react";
import { Activity, BookOpen, ChevronDown, ChevronUp, ExternalLink, Flame, HeartPulse, ShieldCheck } from "lucide-react";
import { formatNumber, type ProfileMetrics } from "@/lib/progress";
import { ProfileInvite } from "@/components/dashboard/TodayCard";
import { cn } from "@/lib/utils";

type BmiStandard = "asia" | "global";

interface BmiBand {
  label: string;
  range: string;
  min: number;
  max: number;
  color: string;
  badgeClass: string;
}

const ASIA_BMI_BANDS: BmiBand[] = [
  { label: "Thiếu cân", range: "< 18.5", min: 14, max: 18.5, color: "#38bdf8", badgeClass: "bg-sky-50 text-sky-700 border-sky-200" },
  { label: "Bình thường", range: "18.5 – 22.9", min: 18.5, max: 23, color: "#2ebd85", badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  { label: "Thừa cân", range: "23.0 – 24.9", min: 23, max: 25, color: "#f59e0b", badgeClass: "bg-amber-50 text-amber-800 border-amber-200" },
  { label: "Béo phì", range: "≥ 25.0", min: 25, max: 35, color: "#ef4444", badgeClass: "bg-red-50 text-red-700 border-red-200" },
];

const GLOBAL_BMI_BANDS: BmiBand[] = [
  { label: "Thiếu cân", range: "< 18.5", min: 14, max: 18.5, color: "#38bdf8", badgeClass: "bg-sky-50 text-sky-700 border-sky-200" },
  { label: "Bình thường", range: "18.5 – 24.9", min: 18.5, max: 25, color: "#2ebd85", badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  { label: "Thừa cân", range: "25.0 – 29.9", min: 25, max: 30, color: "#f59e0b", badgeClass: "bg-amber-50 text-amber-800 border-amber-200" },
  { label: "Béo phì", range: "≥ 30.0", min: 30, max: 35, color: "#ef4444", badgeClass: "bg-red-50 text-red-700 border-red-200" },
];

function badgeForCategory(category: string | null, bands: BmiBand[]): string {
  return bands.find((b) => b.label === category)?.badgeClass ?? "bg-gray-100 text-gray-700 border-gray-200";
}

function bmiMarkerPct(bmi: number): number {
  const minScale = 14;
  const maxScale = 35;
  const clamped = Math.min(Math.max(bmi, minScale), maxScale);
  return ((clamped - minScale) / (maxScale - minScale)) * 100;
}

/** Thẻ trực quan chỉ số sức khỏe (BMI Quốc tế & Châu Á, BMR, TDEE, Macro) kèm căn cứ tài liệu khoa học. */
export function HealthMetricsCard({ metrics }: { metrics: ProfileMetrics }) {
  const [bmiStandard, setBmiStandard] = useState<BmiStandard>("asia");
  const [showRefs, setShowRefs] = useState(true);

  const bands = bmiStandard === "asia" ? ASIA_BMI_BANDS : GLOBAL_BMI_BANDS;
  const activeCategory = bmiStandard === "asia" ? metrics.bmi_asia_category : metrics.bmi_category;
  const scaleSpan = 35 - 14;

  const pKcal = (metrics.protein_g ?? 0) * 4;
  const fKcal = (metrics.fat_g ?? 0) * 9;
  const cKcal = (metrics.carb_g ?? 0) * 4;
  const macroTotalKcal = Math.max(pKcal + fKcal + cKcal, 1);
  const pPct = Math.round((pKcal / macroTotalKcal) * 100);
  const fPct = Math.round((fKcal / macroTotalKcal) * 100);
  const cPct = Math.max(0, 100 - pPct - fPct);

  return (
    <section className="rounded-3xl border border-line/75 bg-surface/85 p-5 sm:p-6 shadow-card backdrop-blur-md">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3.5">
        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className="flex h-8 w-8 items-center justify-center rounded-2xl bg-[#2ebd85]/15 text-[#1f9668]"
          >
            <HeartPulse className="h-4.5 w-4.5" />
          </span>
          <div>
            <h2 className="text-base font-bold tracking-tight text-ink">
              Chỉ số Sức khỏe &amp; Căn cứ Khoa học
            </h2>
            <p className="text-xs text-muted">
              Tính toán trực tiếp từ công thức chuẩn y khoa — không dùng suy đoán AI
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setShowRefs((v) => !v)}
          className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-[#7c5ce6] hover:text-[#7c5ce6] cursor-pointer"
        >
          <BookOpen className="h-3.5 w-3.5 text-[#7c5ce6]" />
          <span>{showRefs ? "Ẩn căn cứ tài liệu" : `Xem ${metrics.references.length} căn cứ tài liệu`}</span>
          {showRefs ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>
      </div>

      {!metrics.is_complete ? (
        <div className="py-2">
          <ProfileInvite missing={metrics.missing_fields} />
        </div>
      ) : (
        <div className="space-y-5">
          {/* Hàng 4 thẻ chỉ số chính */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-line/70 bg-canvas/65 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wide text-muted">Chỉ số BMI</span>
                <span className={cn("rounded-full border px-2.5 py-0.5 text-[11px] font-bold", badgeForCategory(activeCategory, bands))}>
                  {activeCategory}
                </span>
              </div>
              <p className="mt-2 font-numeric text-2xl font-bold text-ink">
                {metrics.bmi !== null ? formatNumber(metrics.bmi, 1) : "—"}
                <span className="ml-1 text-xs font-medium text-muted">kg/m²</span>
              </p>
              <p className="mt-1 text-[11px] text-muted">
                Châu Á (WPRO): <strong className="text-ink">{metrics.bmi_asia_category}</strong> · Quốc tế (WHO):{" "}
                <strong className="text-ink">{metrics.bmi_category}</strong>
              </p>
            </div>

            <div className="rounded-2xl border border-line/70 bg-canvas/65 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wide text-muted">BMR (Cơ bản)</span>
                <Activity className="h-4 w-4 text-[#1ca8d4]" />
              </div>
              <p className="mt-2 font-numeric text-2xl font-bold text-ink">
                {metrics.bmr !== null ? formatNumber(metrics.bmr, 0) : "—"}
                <span className="ml-1 text-xs font-medium text-muted">kcal/ngày</span>
              </p>
              <p className="mt-1 text-[11px] text-muted">
                Năng lượng duy trì sự sống khi nghỉ ngơi (Mifflin-St Jeor, 1990)
              </p>
            </div>

            <div className="rounded-2xl border border-line/70 bg-canvas/65 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wide text-muted">TDEE (Duy trì)</span>
                <Flame className="h-4 w-4 text-[#d9822b]" />
              </div>
              <p className="mt-2 font-numeric text-2xl font-bold text-ink">
                {metrics.tdee !== null ? formatNumber(metrics.tdee, 0) : "—"}
                <span className="ml-1 text-xs font-medium text-muted">kcal/ngày</span>
              </p>
              <p className="mt-1 text-[11px] text-muted">
                Tổng tiêu hao ngày = BMR × Hệ số vận động (FAO/WHO/UNU PAL)
              </p>
            </div>

            <div className="rounded-2xl border border-line/70 bg-canvas/65 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wide text-muted">Calo mục tiêu</span>
                {metrics.calorie_floor_applied ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-800 border border-amber-200">
                    <ShieldCheck className="h-3 w-3" /> Sàn an toàn
                  </span>
                ) : (
                  <span className="rounded-full bg-[#7c5ce6]/10 px-2 py-0.5 text-[11px] font-semibold text-[#7c5ce6]">
                    Khuyến nghị/ngày
                  </span>
                )}
              </div>
              <p className="mt-2 font-numeric text-2xl font-bold text-[#7c5ce6]">
                {metrics.target_calories !== null ? formatNumber(metrics.target_calories, 0) : "—"}
                <span className="ml-1 text-xs font-medium text-muted">kcal/ngày</span>
              </p>
              <p className="mt-1 text-[11px] text-muted">
                {metrics.calorie_floor_applied
                  ? "Đã nâng lên mức sàn an toàn (1,200 nữ / 1,500 nam) theo NIDDK/Harvard"
                  : "Ngưỡng an toàn tối thiểu: ≥1,200 kcal (nữ) / ≥1,500 kcal (nam)"}
              </p>
            </div>
          </div>

          {/* Thanh thang đo BMI trực quan & Thanh tỷ lệ Macro */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Thang đo BMI */}
            <div className="rounded-2xl border border-line/70 bg-canvas/50 p-4">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-bold text-ink">Thang phân loại BMI trực quan</span>
                <div className="inline-flex rounded-full border border-line bg-surface p-0.5 text-[11px] font-semibold">
                  <button
                    type="button"
                    onClick={() => setBmiStandard("asia")}
                    className={cn(
                      "rounded-full px-2.5 py-0.5 transition cursor-pointer",
                      bmiStandard === "asia" ? "bg-[#2ebd85] text-white" : "text-muted hover:text-ink"
                    )}
                  >
                    WHO Châu Á (VN)
                  </button>
                  <button
                    type="button"
                    onClick={() => setBmiStandard("global")}
                    className={cn(
                      "rounded-full px-2.5 py-0.5 transition cursor-pointer",
                      bmiStandard === "global" ? "bg-[#7c5ce6] text-white" : "text-muted hover:text-ink"
                    )}
                  >
                    WHO Quốc tế
                  </button>
                </div>
              </div>

              <div className="relative pt-5 pb-2">
                {metrics.bmi !== null && (
                  <div
                    style={{ left: `${bmiMarkerPct(metrics.bmi)}%` }}
                    className="absolute top-0 -translate-x-1/2 flex flex-col items-center"
                  >
                    <span className="rounded-md bg-ink px-1.5 py-0.5 text-[10px] font-bold text-white shadow-xs">
                      {formatNumber(metrics.bmi, 1)}
                    </span>
                    <span className="h-2 w-0.5 bg-ink" />
                  </div>
                )}
                <div className="flex h-3 w-full overflow-hidden rounded-full">
                  {bands.map((b) => (
                    <div
                      key={b.label}
                      style={{
                        width: `${((b.max - b.min) / scaleSpan) * 100}%`,
                        backgroundColor: b.color,
                      }}
                      title={`${b.label}: ${b.range}`}
                    />
                  ))}
                </div>
              </div>

              <div className="mt-2 grid grid-cols-2 gap-1.5 sm:grid-cols-4">
                {bands.map((b) => (
                  <div key={b.label} className="flex items-center gap-1.5 text-[11px]">
                    <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: b.color }} />
                    <span className="truncate text-ink font-medium">{b.label}</span>
                    <span className="text-muted">({b.range})</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Thanh phân bổ Macro mục tiêu */}
            <div className="rounded-2xl border border-line/70 bg-canvas/50 p-4 flex flex-col justify-between">
              <div>
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="text-xs font-bold text-ink">Phân bổ Macro mục tiêu (IOM AMDR &amp; ISSN)</span>
                  <span className="text-[11px] text-muted">Atwater 4–9–4 kcal/g</span>
                </div>

                <div className="mt-3 flex h-3.5 w-full overflow-hidden rounded-full bg-gray-100">
                  <div style={{ width: `${pPct}%`, backgroundColor: "#2ebd85" }} title={`Protein ${pPct}%`} />
                  <div style={{ width: `${fPct}%`, backgroundColor: "#d9822b" }} title={`Fat ${fPct}%`} />
                  <div style={{ width: `${cPct}%`, backgroundColor: "#1ca8d4" }} title={`Carb ${cPct}%`} />
                </div>
              </div>

              <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                <div className="rounded-xl border border-line/60 bg-surface px-3 py-2">
                  <span className="flex items-center gap-1.5 text-[11px] font-semibold text-muted">
                    <span className="h-2 w-2 rounded-full bg-[#2ebd85]" /> Đạm (Protein)
                  </span>
                  <p className="mt-0.5 font-numeric font-bold text-ink">
                    {metrics.protein_g} g <span className="text-[11px] font-normal text-muted">({pPct}%)</span>
                  </p>
                </div>
                <div className="rounded-xl border border-line/60 bg-surface px-3 py-2">
                  <span className="flex items-center gap-1.5 text-[11px] font-semibold text-muted">
                    <span className="h-2 w-2 rounded-full bg-[#d9822b]" /> Béo (Fat)
                  </span>
                  <p className="mt-0.5 font-numeric font-bold text-ink">
                    {metrics.fat_g} g <span className="text-[11px] font-normal text-muted">({fPct}%)</span>
                  </p>
                </div>
                <div className="rounded-xl border border-line/60 bg-surface px-3 py-2">
                  <span className="flex items-center gap-1.5 text-[11px] font-semibold text-muted">
                    <span className="h-2 w-2 rounded-full bg-[#1ca8d4]" /> Tinh bột (Carb)
                  </span>
                  <p className="mt-0.5 font-numeric font-bold text-ink">
                    {metrics.carb_g} g <span className="text-[11px] font-normal text-muted">({cPct}%)</span>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Bảng danh mục tài liệu căn cứ khoa học */}
      {showRefs && metrics.references.length > 0 && (
        <div className="mt-5 rounded-2xl border border-line/70 bg-canvas/55 p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-ink">
              Tài liệu căn cứ khoa học cho từng chỉ số ({metrics.references.length} nguồn)
            </h3>
            <span className="text-[11px] text-muted">
              Lưu tại <code className="rounded bg-surface px-1.5 py-0.5">data/knowledge/health_metrics_references.md</code>
            </span>
          </div>
          <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            {metrics.references.map((ref) => (
              <div key={ref.key} className="rounded-xl border border-line/65 bg-surface/90 p-3 text-xs">
                <div className="flex items-start justify-between gap-2">
                  <span className="font-bold text-ink">{ref.metric}</span>
                  <a
                    href={ref.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex shrink-0 items-center gap-1 rounded-full bg-[#7c5ce6]/10 px-2 py-0.5 text-[10px] font-semibold text-[#7c5ce6] hover:bg-[#7c5ce6]/20"
                  >
                    <span>{ref.identifier}</span>
                    <ExternalLink className="h-2.5 w-2.5" />
                  </a>
                </div>
                <p className="mt-1 font-medium text-[#1f9668]">{ref.formula}</p>
                <p className="mt-1 text-muted">
                  <strong className="text-ink">{ref.authors_org} ({ref.year})</strong> — <em>{ref.source_title}</em>
                </p>
                <p className="mt-1 text-[11px] text-muted">{ref.notes}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
