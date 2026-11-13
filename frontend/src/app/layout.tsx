import type { Metadata } from "next";
import { Be_Vietnam_Pro } from "next/font/google";
import "./globals.css";
import { BackgroundLayer } from "@/components/layout/BackgroundLayer";

const beVietnamPro = Be_Vietnam_Pro({
  variable: "--font-be-vietnam-pro",
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  fallback: ["system-ui", "-apple-system", "Segoe UI", "Roboto", "Arial", "sans-serif"],
});

export const metadata: Metadata = {
  title: "FitAI — Sổ tay Dinh dưỡng & Thể hình Khoa học",
  description:
    "Nền tảng tư vấn dinh dưỡng thực phẩm Việt Nam và lộ trình tập luyện đối chiếu chuẩn khoa học thể thao ISSN",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className={`${beVietnamPro.variable} antialiased selection:bg-brand-200 selection:text-brand-900`}>
        <BackgroundLayer />
        <div className="relative z-10 min-h-screen">{children}</div>
      </body>
    </html>
  );
}
