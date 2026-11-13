"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/auth";
import { useAuthStore } from "@/store/auth-store";
import { Button } from "@/components/ui/Button";
import { BackgroundSettingsButton } from "@/components/layout/BackgroundLayer";

export function LoginForm() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.login({ username: email, password });
      localStorage.setItem("access_token", res.access_token);
      const me = await authApi.me();
      setAuth(me, res.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-canvas px-4 py-8 sm:px-6 lg:px-8 flex flex-col justify-between">
      {/* Top Bar */}
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-700 text-surface shadow-xs">
            <svg
              className="h-4.5 w-4.5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
              <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
            </svg>
          </div>
          <div>
            <span className="font-serif text-xl font-semibold tracking-tight text-ink">
              FitAI
            </span>
            <span className="ml-2 rounded-full border border-line bg-surface/80 px-2.5 py-0.5 text-[11px] font-medium text-muted">
              ISSN &amp; Viện Dinh Dưỡng VN
            </span>
          </div>
        </div>
        <BackgroundSettingsButton />
      </div>

      {/* Main Editorial Split Layout */}
      <div className="mx-auto my-auto grid w-full max-w-5xl grid-cols-1 gap-8 py-8 lg:grid-cols-12 lg:items-center lg:gap-12">
        {/* Left Editorial Masthead */}
        <div className="lg:col-span-7 space-y-6 rounded-card border border-line bg-surface p-6 sm:p-8 shadow-card">
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.15em] text-brand-700">
            <span className="h-1.5 w-1.5 rounded-full bg-accent-600" />
            Sổ tay Thể chất &amp; Dinh dưỡng Thực chứng
          </div>

          <h1 className="font-serif text-3xl sm:text-4xl lg:text-[40px] font-semibold tracking-tight text-ink leading-[1.18]">
            Hiểu rõ cơ thể bạn qua từng bữa ăn Việt &amp; chỉ số khoa học.
          </h1>

          <p className="text-sm sm:text-base text-muted leading-relaxed max-w-xl">
            Không còn những lời khuyên chung chung. FitAI tính toán chính xác
            BMR, TDEE theo công thức Mifflin-St Jeor, tra cứu 599 món ăn Việt
            Nam và đối chiếu trực tiếp tài liệu Hiệp hội Dinh dưỡng Thể thao
            Quốc tế (ISSN).
          </p>

          <div className="grid grid-cols-3 gap-4 border-t border-line pt-5">
            <div>
              <p className="font-numeric text-xl font-semibold text-ink">599</p>
              <p className="mt-0.5 text-xs text-muted">
                Thực phẩm &amp; món Việt chuẩn hóa
              </p>
            </div>
            <div>
              <p className="font-numeric text-xl font-semibold text-ink">ISSN</p>
              <p className="mt-0.5 text-xs text-muted">
                Dẫn chứng nghiên cứu lâm sàng
              </p>
            </div>
            <div>
              <p className="font-numeric text-xl font-semibold text-ink">100%</p>
              <p className="mt-0.5 text-xs text-muted">
                Cá nhân hóa theo chỉ số cơ thể
              </p>
            </div>
          </div>
        </div>

        {/* Right Form Card */}
        <div className="lg:col-span-5">
          <div className="rounded-card border border-line bg-surface p-7 sm:p-8 shadow-raised">
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-muted">
                Cổng thành viên
              </p>
              <h2 className="mt-1 font-serif text-2xl font-semibold text-ink">
                Đăng nhập sổ tay
              </h2>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="email"
                  className="block text-xs font-semibold uppercase tracking-wider text-muted mb-1.5"
                >
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full rounded-control border border-line bg-surface px-3.5 py-2.5 text-sm text-ink placeholder:text-subtle shadow-xs focus:border-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
              </div>

              <div>
                <label
                  htmlFor="password"
                  className="block text-xs font-semibold uppercase tracking-wider text-muted mb-1.5"
                >
                  Mật khẩu
                </label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-control border border-line bg-surface px-3.5 py-2.5 text-sm text-ink placeholder:text-subtle shadow-xs focus:border-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
              </div>

              {error && (
                <p className="rounded-control bg-red-50 px-3.5 py-2.5 text-sm text-red-600 ring-1 ring-red-200">
                  {error}
                </p>
              )}

              <Button type="submit" loading={loading} className="w-full" size="lg">
                Đăng nhập
              </Button>
            </form>

            <p className="mt-6 border-t border-line pt-5 text-center text-sm text-muted">
              Chưa có tài khoản?{" "}
              <Link
                href="/register"
                className="font-semibold text-brand-700 underline decoration-brand-700/30 underline-offset-4 hover:text-brand-800"
              >
                Đăng ký ngay
              </Link>
            </p>
          </div>
        </div>
      </div>

      {/* Subtle Editorial Footer */}
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-2 text-xs text-muted">
        <span>© FitAI — Sổ tay Dinh dưỡng &amp; Thể hình Khoa học</span>
        <span>Mẹo: Nhấn nút &ldquo;Hình nền&rdquo; góc phải trên để dùng ảnh riêng của bạn</span>
      </div>
    </div>
  );
}

export default LoginForm;
