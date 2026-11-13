"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";
import { authApi } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { BackgroundSettingsButton } from "./BackgroundLayer";

let meSyncedInSession = false;

interface PetalNavItem {
  id: string;
  href: string;
  label: string;
  sublabel: string;
  color: string;
  /** Góc trên vòng tròn (0° = 3h, 90° = 6h, -90° = 12h) */
  angleDeg: number;
  /** Vị trí nhãn chữ so với cánh hoa */
  labelPosition: "left" | "right" | "top" | "bottom";
  icon: React.ReactNode;
}

const BASE_PETALS: PetalNavItem[] = [
  {
    id: "dashboard",
    href: "/dashboard",
    label: "Tổng quan",
    sublabel: "Phân tích dữ liệu thực tế",
    color: "#7c5ce6",
    angleDeg: -142,
    labelPosition: "left",
    icon: (
      <svg className="h-9 w-9" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="8" y1="40" x2="40" y2="40" />
        <rect x="11" y="29" width="4.5" height="11" rx="1" />
        <rect x="19" y="24" width="4.5" height="16" rx="1" />
        <rect x="27" y="27" width="4.5" height="13" rx="1" />
        <rect x="35" y="18" width="4.5" height="22" rx="1" />
        <circle cx="13" cy="20" r="2.2" fill="#fffaf8" />
        <circle cx="21" cy="14" r="2.2" fill="#fffaf8" />
        <circle cx="29" cy="18" r="2.2" fill="#fffaf8" />
        <circle cx="37" cy="10" r="2.2" fill="#fffaf8" />
        <path d="M14.8 18.7 L19.2 15.3 M23 15 L27 17 M30.6 16.4 L35.4 11.6" />
      </svg>
    ),
  },
  {
    id: "meals",
    href: "/meals",
    label: "Nhật ký ăn uống",
    sublabel: "Ghi bữa ăn & Macro",
    color: "#2ebd85",
    angleDeg: -38,
    labelPosition: "right",
    icon: (
      <svg className="h-9 w-9" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="24,8 25.6,11.4 29.3,11.9 26.6,14.5 27.3,18.2 24,16.4 20.7,18.2 21.4,14.5 18.7,11.9 22.4,11.4" />
        <polygon points="13,12 14.2,14.6 17,15 15,17 15.5,19.8 13,18.4 10.5,19.8 11,17 9,15 11.8,14.6" />
        <polygon points="35,12 36.2,14.6 39,15 37,17 37.5,19.8 35,18.4 32.5,19.8 33,17 31,15 33.8,14.6" />
        <circle cx="24" cy="27" r="5" />
        <path d="M15 39 C15 34.5, 19 32, 24 32 C29 32, 33 34.5, 33 39" />
      </svg>
    ),
  },
  {
    id: "training",
    href: "/training",
    label: "Tập luyện",
    sublabel: "Lịch tập & Vận động",
    color: "#8ab833",
    angleDeg: 26,
    labelPosition: "right",
    icon: (
      <svg className="h-9 w-9" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M24 22 C24 22, 17 17.5, 17 13.5 C17 11, 19 9.5, 21.2 9.5 C22.6 9.5, 23.5 10.3, 24 11.3 C24.5 10.3, 25.4 9.5, 26.8 9.5 C29 9.5, 31 11, 31 13.5 C31 17.5, 24 22, 24 22 Z" />
        <circle cx="16.5" cy="27.5" r="3.8" />
        <path d="M10.5 38.5 C10.5 34.5, 13 32.5, 16.5 32.5 C20 32.5, 22.5 34.5, 22.5 38.5 Z" />
        <circle cx="31.5" cy="27.5" r="3.8" />
        <path d="M25.5 38.5 C25.5 34.5, 28 32.5, 31.5 32.5 C35 32.5, 37.5 34.5, 37.5 38.5 Z" />
      </svg>
    ),
  },
  {
    id: "chat",
    href: "/chat",
    label: "Cố vấn AI",
    sublabel: "Hỗ trợ dinh dưỡng ISSN",
    color: "#1ca8d4",
    angleDeg: 90,
    labelPosition: "bottom",
    icon: (
      <svg className="h-9 w-9" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 26 V22 C14 15.9, 18.5 11, 24 11 C29.5 11, 34 15.9, 34 22 V26" />
        <path d="M14 23 C11.8 23, 10 24.8, 10 27 V29 C10 31.2, 11.8 33, 14 33" />
        <path d="M34 23 C36.2 23, 38 24.8, 38 27 V29 C38 31.2, 36.2 33, 34 33" />
        <path d="M34 33 C34 36.5, 30.5 38.5, 25 38.5" />
        <rect x="20" y="36.8" width="6" height="3.4" rx="1.7" />
      </svg>
    ),
  },
  {
    id: "onboarding",
    href: "/onboarding",
    label: "Hồ sơ cơ thể",
    sublabel: "Mục tiêu & Chỉ số TDEE",
    color: "#d9822b",
    angleDeg: 154,
    labelPosition: "left",
    icon: (
      <svg className="h-9 w-9" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M16 15 C20 10.5, 28 10.5, 32 15" />
        <polyline points="28,11 32.5,15 28,17.5" />
        <circle cx="24" cy="31" r="7" />
        <path d="M24 27.5 L24 34.5 M21.5 29.5 C21.5 28.3, 26.5 28.3, 26.5 30 C26.5 31.5, 21.5 31, 21.5 32.8 C21.5 34.2, 26.5 34.2, 26.5 32.8" />
        <circle cx="15" cy="23" r="3" />
        <circle cx="33" cy="23" r="3" />
      </svg>
    ),
  },
];

const ADMIN_PETAL: PetalNavItem = {
  id: "admin",
  href: "/admin",
  label: "Quản trị",
  sublabel: "Thực phẩm & Tài liệu",
  color: "#e04f5f",
  angleDeg: -90,
  labelPosition: "top",
  icon: (
    <svg className="h-9 w-9" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M24 9 L36 14 V23 C36 31.5 30.8 37.8 24 40 C17.2 37.8 12 31.5 12 23 V14 L24 9 Z" />
      <polyline points="19,24.5 22.5,28 29.5,20.5" />
    </svg>
  ),
};

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

/**
 * Hub Điều Hướng Vòng Tròn Cánh Hoa (Radial Petal Hub) ở góc trên bên trái.
 * - Bình thường: Là một vòng tròn tinh gọn ở góc trên bên trái.
 * - Khi click vào: Bung ra sơ đồ vòng tròn 5–6 cánh hoa y hệt thiết kế Infographic mẫu
 *   để người dùng nhấp chọn điều hướng sang các trang chức năng.
 */
export function AppHeader() {
  const router = useRouter();
  const pathname = usePathname() ?? "";
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const logout = useAuthStore((s) => s.logout);

  const [open, setOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    const rawToken = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (!isAuthenticated && !rawToken) return;
    if (meSyncedInSession && user) return;
    meSyncedInSession = true;
    authApi
      .me()
      .then((me) => {
        const { token, setAuth } = useAuthStore.getState();
        const activeToken = token || rawToken;
        if (activeToken) setAuth(me, activeToken);
      })
      .catch(() => {
        meSyncedInSession = false;
      });
  }, [hydrated, isAuthenticated, user]);

  // Prefetch tất cả các trang trong vòng tròn điều hướng để chuyển trang tức thì
  useEffect(() => {
    if (!hydrated) return;
    const allRoutes =
      user?.role === "admin" ? [...BASE_PETALS, ADMIN_PETAL] : BASE_PETALS;
    allRoutes.forEach((p) => {
      router.prefetch(p.href);
    });
  }, [hydrated, user?.role, router]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const petals =
    hydrated && user?.role === "admin" ? [...BASE_PETALS, ADMIN_PETAL] : BASE_PETALS;

  const currentItem = petals.find((p) => isActive(pathname, p.href));

  const handleLogout = () => {
    meSyncedInSession = false;
    setOpen(false);
    logout();
    router.replace("/login");
  };

  // Tọa độ tâm của sơ đồ cánh hoa khi bung ra ở góc trên bên trái
  const centerX = 330;
  const centerY = 265;
  const ringRadius = 100;
  const petalDistance = 148;

  return (
    <>
      {/* Nút chỉnh Hình nền nhỏ gọn ở góc trên bên phải */}
      <div className="fixed right-5 top-5 z-40 flex items-center gap-2">
        <BackgroundSettingsButton />
      </div>

      {/* Lớp bắt click ra ngoài để thu gọn — hoàn toàn trong suốt, không làm mờ trang */}
      {open && (
        <div
          aria-hidden
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-40 bg-transparent"
        />
      )}

      {/* ── NÚT VÒNG TRÒN GÓC TRÊN BÊN TRÁI (Khi đang thu gọn) ──────────── */}
      <div className="fixed left-5 top-5 z-50 flex items-center gap-3 select-none">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label="Mở vòng tròn điều hướng chức năng"
          className={cn(
            "group relative flex h-15 w-15 items-center justify-center rounded-full border-[2.3px] border-[#45413e] bg-[#fffaf8] text-[#45413e] shadow-raised transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] hover:scale-105 cursor-pointer",
            open && "scale-75 rotate-45 opacity-0 pointer-events-none"
          )}
        >
          {currentItem && (
            <span
              aria-hidden
              style={{ borderColor: currentItem.color }}
              className="pointer-events-none absolute -inset-1 rounded-full border-2 opacity-75 transition-transform group-hover:scale-105"
            />
          )}

          {/* Biểu tượng 3 ô vuông + 1 ngôi sao 4 cánh chuẩn ảnh mẫu */}
          <svg
            className="h-8 w-8 transition-transform duration-300 group-hover:rotate-12"
            viewBox="0 0 80 80"
            fill="none"
            stroke="currentColor"
            strokeWidth="3.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="12" y="12" width="22" height="22" rx="4" />
            <path d="M57 10 C57 19, 60 22, 69 22 C60 22, 57 25, 57 34 C57 25, 54 22, 45 22 C54 22, 57 19, 57 10 Z" />
            <rect x="12" y="44" width="22" height="22" rx="4" />
            <rect x="46" y="44" width="22" height="22" rx="4" />
          </svg>
        </button>

        <button
          type="button"
          onClick={() => setOpen(true)}
          tabIndex={open ? -1 : 0}
          className={cn(
            "hidden sm:flex items-center gap-2 rounded-full border border-line/80 bg-[#fffaf8]/95 px-3.5 py-1.5 text-xs font-semibold text-ink shadow-sm transition-all duration-200 hover:bg-white cursor-pointer",
            open && "opacity-0 -translate-x-2 pointer-events-none"
          )}
        >
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: currentItem?.color ?? "#45413e" }}
          />
          <span>{currentItem?.label ?? "Chọn chức năng"}</span>
        </button>
      </div>

      {/* ── SƠ ĐỒ VÒNG TRÒN CÁNH HOA KHI CLICK BUNG RA (Giữ mount để chạy animation mở/đóng) ──── */}
      <nav
        aria-label="Vòng tròn điều hướng chức năng"
        aria-hidden={!open}
        className={cn(
          "fixed left-0 top-0 z-50 h-[560px] w-[680px] max-w-full select-none",
          open ? "pointer-events-auto" : "pointer-events-none"
        )}
      >
        {/* Vòng tròn trung tâm kết nối các cánh hoa + nút thu gọn */}
        <div
          style={{
            left: `${centerX}px`,
            top: `${centerY}px`,
            width: `${ringRadius * 2 + 16}px`,
            height: `${ringRadius * 2 + 16}px`,
            transform: open ? "translate(-50%, -50%) scale(1)" : "translate(-50%, -50%) scale(0.45)",
            opacity: open ? 1 : 0,
            transitionDelay: open ? "0ms" : `${Math.max(0, petals.length - 1) * 20}ms`,
          }}
          className="absolute flex items-center justify-center transition-all duration-400 ease-[cubic-bezier(0.22,1,0.36,1)]"
        >
          <svg
            aria-hidden
            viewBox={`0 0 ${ringRadius * 2 + 16} ${ringRadius * 2 + 16}`}
            className="pointer-events-none absolute inset-0 h-full w-full drop-shadow-md"
          >
            <circle
              cx={ringRadius + 8}
              cy={ringRadius + 8}
              r={ringRadius}
              fill="rgba(255, 250, 248, 0.96)"
              stroke="#45413e"
              strokeWidth="2.3"
            />
          </svg>

          {/* Nút Trung Tâm Vòng Tròn (3 ô vuông + ngôi sao 4 cánh) — bấm để thu gọn */}
          <button
            type="button"
            tabIndex={open ? 0 : -1}
            onClick={() => setOpen(false)}
            aria-label="Đóng vòng tròn điều hướng"
            className="group relative flex flex-col items-center justify-center rounded-full p-5 text-[#45413e] transition-transform hover:scale-105 cursor-pointer"
          >
            <svg
              className={cn(
                "h-18 w-18 transition-transform duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:rotate-[102deg]",
                open ? "rotate-90" : "rotate-0"
              )}
              viewBox="0 0 80 80"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="12" y="12" width="22" height="22" rx="4" />
              <path d="M57 10 C57 19, 60 22, 69 22 C60 22, 57 25, 57 34 C57 25, 54 22, 45 22 C54 22, 57 19, 57 10 Z" />
              <rect x="12" y="44" width="22" height="22" rx="4" />
              <rect x="46" y="44" width="22" height="22" rx="4" />
            </svg>
            <span className="mt-1 text-[10px] font-bold uppercase tracking-widest text-muted">
              Thu gọn
            </span>
          </button>
        </div>

        {/* Các Cánh Hoa (Petals) bung tỏa từ tâm vòng tròn theo hiệu ứng spring */}
        {petals.map((petal, idx) => {
          const rad = (petal.angleDeg * Math.PI) / 180;
          const dx = Math.round(Math.cos(rad) * petalDistance);
          const dy = Math.round(Math.sin(rad) * petalDistance);
          // Góc xoay để mũi nhọn (góc 45° dưới-phải) luôn chĩa thẳng vào tâm vòng tròn
          const petalRotationDeg = petal.angleDeg + 135;
          const active = isActive(pathname, petal.href);

          return (
            <div
              key={petal.id}
              style={{
                left: `${centerX}px`,
                top: `${centerY}px`,
                transform: open
                  ? `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px)) scale(1)`
                  : "translate(-50%, -50%) scale(0.2)",
                opacity: open ? 1 : 0,
                transitionDelay: open
                  ? `${idx * 45}ms`
                  : `${(petals.length - 1 - idx) * 25}ms`,
              }}
              className="absolute transition-all duration-450 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
            >
              <Link
                href={petal.href}
                prefetch
                tabIndex={open ? 0 : -1}
                onClick={() => setOpen(false)}
                aria-current={active ? "page" : undefined}
                className="group relative flex items-center justify-center focus:outline-none cursor-pointer"
              >
                {/* Cánh hoa giọt nước */}
                <div
                  style={{
                    borderColor: petal.color,
                    color: petal.color,
                    transform: `rotate(${petalRotationDeg}deg)`,
                  }}
                  className={cn(
                    "flex h-22 w-22 shrink-0 items-center justify-center rounded-[50%_50%_4px_50%] border-[2.4px] bg-[#fffaf8] shadow-lg transition-all duration-200 group-hover:scale-110 group-hover:bg-white",
                    active && "ring-4 ring-offset-2 bg-white scale-105"
                  )}
                >
                  <div style={{ transform: `rotate(${-petalRotationDeg}deg)` }}>
                    {petal.icon}
                  </div>
                </div>

                {/* Nhãn chữ nổi gọn, rõ nét trên nền trang không làm mờ */}
                <div
                  className={cn(
                    "pointer-events-auto w-[154px] rounded-2xl border border-line bg-[#fffaf8]/95 px-3 py-1.5 shadow-md transition-transform group-hover:scale-[1.03]",
                    petal.labelPosition === "left" &&
                      "absolute right-full mr-3.5 text-right",
                    petal.labelPosition === "right" &&
                      "absolute left-full ml-3.5 text-left",
                    petal.labelPosition === "bottom" &&
                      "absolute left-1/2 top-full mt-2.5 -translate-x-1/2 w-[178px] text-center",
                    petal.labelPosition === "top" &&
                      "absolute bottom-full left-1/2 mb-2.5 -translate-x-1/2 w-[178px] text-center"
                  )}
                >
                  <p
                    className="text-sm font-bold leading-snug"
                    style={{ color: active ? petal.color : "#3d3937" }}
                  >
                    {petal.label}
                  </p>
                  <p className="mt-0.5 text-[11px] font-medium text-muted leading-tight">
                    {petal.sublabel}
                  </p>
                </div>
              </Link>
            </div>
          );
        })}

        {/* Nút Đăng xuất tinh tế ở góc dưới sơ đồ */}
        <div
          style={{
            left: `${centerX}px`,
            top: `${centerY + petalDistance + 98}px`,
            transform: open
              ? "translate(-50%, 0px) scale(1)"
              : "translate(-50%, -12px) scale(0.9)",
            opacity: open ? 1 : 0,
            transitionDelay: open ? `${petals.length * 40}ms` : "0ms",
          }}
          className="absolute flex items-center gap-2.5 rounded-full border border-line bg-[#fffaf8]/95 px-3 py-1 shadow-md transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]"
        >
          {user?.email && (
            <span className="text-xs font-medium text-muted">{user.email}</span>
          )}
          <button
            type="button"
            tabIndex={open ? 0 : -1}
            onClick={handleLogout}
            className="rounded-full border border-red-200 bg-red-50/70 px-3 py-0.5 text-xs font-semibold text-red-600 transition hover:bg-red-100 cursor-pointer"
          >
            Đăng xuất
          </button>
        </div>
      </nav>

      {/* Khoảng đệm nhỏ đầu trang để nút tròn góc trái không che tiêu đề */}
      <div aria-hidden className="h-18" />
    </>
  );
}
