"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/auth";
import { useAuthStore } from "@/store/auth-store";
import { Button } from "@/components/ui/Button";
import { BackgroundSettingsButton } from "@/components/layout/BackgroundLayer";

export function RegisterForm() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Mật khẩu xác nhận không khớp");
      return;
    }
    if (password.length < 8) {
      setError("Mật khẩu phải có ít nhất 8 ký tự");
      return;
    }

    setLoading(true);
    try {
      await authApi.register({ email, password, full_name: fullName || undefined });
      const loginRes = await authApi.login({ username: email, password });
      localStorage.setItem("access_token", loginRes.access_token);
      const me = await authApi.me();
      setAuth(me, loginRes.access_token);
      router.push("/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng ký thất bại");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-canvas px-4 py-8 sm:px-6 lg:px-8 flex flex-col justify-between">
      {/* Top Bar */}
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between">
        <Link href="/login" className="flex items-center gap-3">
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
          <span className="font-serif text-xl font-semibold tracking-tight text-ink">
            FitAI
          </span>
        </Link>
        <BackgroundSettingsButton />
      </div>

      {/* Centered Editorial Registration Card */}
      <div className="mx-auto my-auto w-full max-w-md py-8">
        <div className="rounded-card border border-line bg-surface p-7 sm:p-8 shadow-raised">
          <div className="mb-6">
            <p className="text-xs font-semibold uppercase tracking-widest text-brand-700">
              Khởi tạo hồ sơ
            </p>
            <h1 className="mt-1 font-serif text-2xl font-semibold text-ink">
              Tạo sổ tay dinh dưỡng mới
            </h1>
            <p className="mt-1 text-xs text-muted">
              Thiết lập tài khoản để lưu trữ chỉ số BMR, TDEE và lịch sử tư vấn.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="full-name"
                className="block text-xs font-semibold uppercase tracking-wider text-muted mb-1.5"
              >
                Họ và tên <span className="font-normal text-subtle">(tuỳ chọn)</span>
              </label>
              <input
                id="full-name"
                type="text"
                autoComplete="name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Nguyễn Văn A"
                className="w-full rounded-control border border-line bg-surface px-3.5 py-2.5 text-sm text-ink placeholder:text-subtle shadow-xs focus:border-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              />
            </div>

            <div>
              <label
                htmlFor="email"
                className="block text-xs font-semibold uppercase tracking-wider text-muted mb-1.5"
              >
                Email <span className="text-red-500">*</span>
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
                Mật khẩu <span className="text-red-500">*</span>
              </label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Tối thiểu 8 ký tự"
                className="w-full rounded-control border border-line bg-surface px-3.5 py-2.5 text-sm text-ink placeholder:text-subtle shadow-xs focus:border-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              />
            </div>

            <div>
              <label
                htmlFor="confirm-password"
                className="block text-xs font-semibold uppercase tracking-wider text-muted mb-1.5"
              >
                Xác nhận mật khẩu <span className="text-red-500">*</span>
              </label>
              <input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Nhập lại mật khẩu"
                className="w-full rounded-control border border-line bg-surface px-3.5 py-2.5 text-sm text-ink placeholder:text-subtle shadow-xs focus:border-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              />
            </div>

            {error && (
              <p className="rounded-control bg-red-50 px-3.5 py-2.5 text-sm text-red-600 ring-1 ring-red-200">
                {error}
              </p>
            )}

            <Button type="submit" loading={loading} className="w-full" size="lg">
              Đăng ký
            </Button>
          </form>

          <p className="mt-6 border-t border-line pt-5 text-center text-sm text-muted">
            Đã có tài khoản?{" "}
            <Link
              href="/login"
              className="font-semibold text-brand-700 underline decoration-brand-700/30 underline-offset-4 hover:text-brand-800"
            >
              Đăng nhập
            </Link>
          </p>
        </div>
      </div>

      <div className="mx-auto flex w-full max-w-5xl items-center justify-between text-xs text-muted">
        <span>© FitAI — Sổ tay Dinh dưỡng &amp; Thể hình Khoa học</span>
        <span>Chuẩn hóa theo Mifflin-St Jeor &amp; ISSN</span>
      </div>
    </div>
  );
}

export default RegisterForm;
