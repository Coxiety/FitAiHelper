"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";
import { AppHeader } from "@/components/layout/AppHeader";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/Button";
import { isValidTarget } from "@/components/ui/StatCard";
import { CalendarDays, UtensilsCrossed } from "lucide-react";
import { cn } from "@/lib/utils";
import { authApi } from "@/lib/auth";
import { mealsApi, todayVN, type DailySummary } from "@/lib/meals";
import {
  PROGRESS_DAYS,
  bodyMetricsApi,
  formatNumber,
  fullDate,
  progressApi,
  type BodyMetric,
  type Progress,
  type ProgressDays,
  type WeeklyReport,
} from "@/lib/progress";
import { BodyMetricsPanel } from "@/components/dashboard/BodyMetricsPanel";
import { CalorieChart } from "@/components/dashboard/CalorieChart";
import { ProfileInvite, TodayStats } from "@/components/dashboard/TodayCard";
import { WeeklyReportCard } from "@/components/dashboard/WeeklyReportCard";
import { TrainingWeekCard } from "@/components/dashboard/TrainingWeekCard";
import { WeightChart } from "@/components/dashboard/WeightChart";

function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function mondayOf(iso: string): string {
  const weekday = (new Date(`${iso}T00:00:00Z`).getUTCDay() + 6) % 7;
  return addDays(iso, -weekday);
}

function weekdayVN(iso: string): string {
  const names = ["Chủ nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"];
  return names[new Date(`${iso}T00:00:00Z`).getUTCDay()];
}

function SectionStage({
  title,
  accentColor,
  right,
  className,
  children,
}: {
  title: string;
  accentColor: string;
  right?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className={cn(
        "rounded-3xl border border-line/75 bg-surface/85 p-6 shadow-card backdrop-blur-md",
        className
      )}
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3.5">
        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className="h-4 w-4 -rotate-45 rounded-[50%_50%_2px_50%] border-2"
            style={{ borderColor: accentColor, backgroundColor: `${accentColor}1a` }}
          />
          <h2 className="text-base font-bold tracking-tight text-ink">{title}</h2>
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}

export function DashboardView() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const [days, setDays] = useState<ProgressDays>(7);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [today, setToday] = useState<DailySummary | null>(null);
  const [metrics, setMetrics] = useState<BodyMetric[]>([]);
  const [weekStart, setWeekStart] = useState(() => addDays(mondayOf(todayVN()), -7));
  const [weekly, setWeekly] = useState<WeeklyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [weeklyLoading, setWeeklyLoading] = useState(false);
  const [error, setError] = useState("");
  const [weeklyError, setWeeklyError] = useState("");
  const loadSeq = useRef(0);
  const weeklySeq = useRef(0);

  const handleUnauthorized = useCallback(() => {
    useAuthStore.getState().logout();
    router.replace("/login");
  }, [router]);

  useEffect(() => {
    const hasToken = typeof window !== "undefined" && !!localStorage.getItem("access_token");
    if (!isAuthenticated && !hasToken) {
      router.replace("/login");
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    authApi
      .me()
      .then((me) => {
        const { token, setAuth } = useAuthStore.getState();
        if (token) setAuth(me, token);
      })
      .catch(() => {});
  }, [isAuthenticated]);

  const load = useCallback(
    async (range: ProgressDays) => {
      const seq = ++loadSeq.current;
      setLoading(true);
      setError("");
      try {
        const [p, s, m] = await Promise.all([
          progressApi.get(range),
          mealsApi.summary(todayVN()),
          bodyMetricsApi.list(),
        ]);
        if (seq !== loadSeq.current) return;
        setProgress(p);
        setToday(s);
        setMetrics(m.items);
      } catch (err: any) {
        if (seq !== loadSeq.current) return;
        if (err?.status === 401) return handleUnauthorized();
        setError("Không tải được dữ liệu tiến độ. Vui lòng thử lại sau.");
      } finally {
        if (seq === loadSeq.current) setLoading(false);
      }
    },
    [handleUnauthorized]
  );

  const loadWeekly = useCallback(
    async (start: string) => {
      const seq = ++weeklySeq.current;
      setWeeklyLoading(true);
      setWeeklyError("");
      try {
        const r = await progressApi.weeklyReport(start);
        if (seq !== weeklySeq.current) return;
        setWeekly(r);
      } catch (err: any) {
        if (seq !== weeklySeq.current) return;
        if (err?.status === 401) return handleUnauthorized();
        setWeeklyError("Không tải được báo cáo tuần. Vui lòng thử lại sau.");
      } finally {
        if (seq === weeklySeq.current) setWeeklyLoading(false);
      }
    },
    [handleUnauthorized]
  );

  useEffect(() => {
    if (isAuthenticated) load(days);
  }, [isAuthenticated, days, load]);

  useEffect(() => {
    if (isAuthenticated) loadWeekly(weekStart);
  }, [isAuthenticated, weekStart, loadWeekly]);

  const refreshAll = () => {
    load(days);
    loadWeekly(weekStart);
  };

  const stats = progress?.stats;
  const kcalComparison = stats?.comparison?.energy_kcal ?? null;
  const currentMonday = mondayOf(todayVN());
  const displayName = user?.full_name ?? user?.email ?? "bạn";
  const hasLog = !!today && today.entries_count > 0;
  const target = today?.target?.energy_kcal;

  return (
    <div className="min-h-screen bg-canvas">
      <AppHeader />

      <PageContainer className="space-y-6 pt-2">
        {/* Tiêu đề trang thoáng, đồng bộ phong cách Infographic */}
        <header className="flex flex-wrap items-end justify-between gap-4 border-b border-line/80 pb-5">
          <div>
            <p className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-[#7c5ce6]">
              <span className="h-2 w-2 rounded-full bg-[#7c5ce6]" />
              Tổng quan chỉ số hôm nay
            </p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-ink sm:text-3xl">
              Xin chào, {displayName}
            </h1>
            {today && (
              <p className="mt-1 flex items-center gap-1.5 text-sm text-muted">
                <CalendarDays aria-hidden className="h-4 w-4 text-[#2ebd85]" />
                {weekdayVN(today.date)}, {fullDate(today.date)}
                {hasLog && (
                  <span className="ml-2 font-numeric font-semibold text-ink">
                    · Đã nạp {formatNumber(today.eaten.energy_kcal, 0)}
                    {isValidTarget(target) && ` / ${formatNumber(target, 0)}`} kcal
                  </span>
                )}
              </p>
            )}
          </div>

          <Link
            href="/meals"
            className="inline-flex items-center gap-2 rounded-full border-2 border-[#2ebd85] bg-surface px-4 py-2 text-xs font-bold text-[#1f9668] shadow-2xs transition hover:bg-[#2ebd85] hover:text-white"
          >
            <UtensilsCrossed aria-hidden className="h-3.5 w-3.5" />
            Ghi bữa ăn hôm nay
          </Link>
        </header>

        {error && (
          <div className="flex items-center justify-between rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
            <span>{error}</span>
            <Button size="sm" variant="secondary" onClick={() => load(days)}>
              Thử lại
            </Button>
          </div>
        )}

        {/* 4 Widget cánh hoa chỉ số Macro hôm nay */}
        {loading && !progress ? (
          <p className="text-sm text-muted">Đang tải…</p>
        ) : (
          today && progress && <TodayStats summary={today} />
        )}

        {/* Các bảng phân tích chi tiết */}
        <div className="grid items-stretch gap-6 lg:grid-cols-2">
          {progress && stats && (
            <SectionStage
              className="lg:col-span-2"
              title={`Calo theo ngày (${progress.period_label})`}
              accentColor="#7c5ce6"
              right={
                <div className="flex gap-1.5" role="group" aria-label="Chọn khoảng thời gian">
                  {PROGRESS_DAYS.map((d) => (
                    <button
                      key={d}
                      onClick={() => setDays(d)}
                      disabled={loading}
                      aria-pressed={d === days}
                      className={cn(
                        "rounded-full px-3.5 py-1 text-xs font-bold transition-colors disabled:opacity-60 cursor-pointer",
                        d === days
                          ? "bg-[#7c5ce6] text-white"
                          : "border border-line bg-surface text-muted hover:text-ink"
                      )}
                    >
                      {d} ngày
                    </button>
                  ))}
                </div>
              }
            >
              <CalorieChart series={progress.series} target={progress.target?.energy_kcal ?? null} />
              <div className="mt-4 space-y-1 rounded-2xl border border-line/70 bg-canvas/60 px-4 py-3 text-sm text-ink">
                <p>
                  Có nhật ký <strong>{stats.logged_days}/{stats.days_count}</strong> ngày
                  {stats.incomplete_days > 0 && `, ${stats.incomplete_days} ngày tổng chưa đầy đủ`}.
                </p>
                {stats.average.energy_kcal !== null && (
                  <p>
                    Calo trung bình: <strong>{formatNumber(stats.average.energy_kcal, 0)} kcal/ngày</strong>
                    {kcalComparison &&
                      (kcalComparison.diff === 0
                        ? ", bằng mục tiêu"
                        : `, ${kcalComparison.diff < 0 ? "thấp hơn" : "cao hơn"} mục tiêu ` +
                          `${formatNumber(Math.abs(kcalComparison.diff), 0)} kcal (${formatNumber(
                            Math.abs(kcalComparison.diff_pct)
                          )}%)`)}
                    .
                  </p>
                )}
                {stats.average.energy_kcal !== null && <p className="text-muted">{stats.calorie_note}</p>}
              </div>
              {!progress.is_complete && (
                <div className="mt-3">
                  <ProfileInvite missing={progress.missing_fields} />
                </div>
              )}
            </SectionStage>
          )}

          {progress && stats && (
            <SectionStage title={`Cân nặng (${progress.period_label})`} accentColor="#d9822b">
              <p className="mb-3 text-sm text-muted">
                Cân nặng gần nhất:{" "}
                {progress.latest_weight ? (
                  <strong className="text-ink">
                    {formatNumber(progress.latest_weight.weight_kg)} kg (
                    {fullDate(progress.latest_weight.measured_on)})
                  </strong>
                ) : (
                  "chưa có lần đo"
                )}
              </p>
              <WeightChart series={progress.series} />
              <p className="mt-2 text-sm text-ink">
                {stats.weight_change
                  ? `Thay đổi ${
                      stats.weight_change.change_kg > 0
                        ? "+"
                        : stats.weight_change.change_kg < 0
                        ? "−"
                        : ""
                    }` +
                    `${formatNumber(Math.abs(stats.weight_change.change_kg))} kg: từ ${formatNumber(
                      stats.weight_change.first_kg
                    )} kg ` +
                    `(${fullDate(stats.weight_change.first_date)}) đến ${formatNumber(
                      stats.weight_change.last_kg
                    )} kg ` +
                    `(${fullDate(stats.weight_change.last_date)}), ${stats.weight_change.measurements_count} lần đo.`
                  : "Chưa đủ 2 lần đo trong khoảng này để tính thay đổi."}
              </p>
            </SectionStage>
          )}

          {progress && stats && (
            <SectionStage title="Ghi cân nặng" accentColor="#2ebd85">
              <BodyMetricsPanel
                items={metrics}
                onChanged={refreshAll}
                onUnauthorized={handleUnauthorized}
              />
            </SectionStage>
          )}

          {weeklyError && (
            <div className="flex items-center justify-between rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 lg:col-span-2">
              <span>{weeklyError}</span>
              <Button size="sm" variant="secondary" onClick={() => loadWeekly(weekStart)}>
                Thử lại
              </Button>
            </div>
          )}
          {weekly && (
            <WeeklyReportCard
              report={weekly}
              busy={weeklyLoading}
              canGoNext={weekStart < currentMonday}
              onPrev={() => setWeekStart(addDays(weekStart, -7))}
              onNext={() => setWeekStart(addDays(weekStart, 7))}
            />
          )}

          <TrainingWeekCard onUnauthorized={handleUnauthorized} />
        </div>
      </PageContainer>
    </div>
  );
}
