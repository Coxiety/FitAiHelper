"use client";

import { useEffect, useState, useRef } from "react";
import { usePathname } from "next/navigation";
import { Image as ImageIcon, Upload, X, RotateCcw, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface BgConfig {
  /** Đường dẫn ảnh (vd: "/backgrounds/bg.jpg", URL ngoài, hoặc "idb:custom" khi chọn file từ máy) */
  source: string;
  /** Độ đậm lớp phủ kem ấm (0.15 -> 0.92) để chữ luôn dễ đọc */
  overlayOpacity: number;
  /** Độ nhòe nền (px: 0 -> 16) */
  blurPx: number;
}

const STORAGE_KEY = "fitai_bg_config_v1";
const IDB_NAME = "fitai_custom_assets";
const IDB_STORE = "backgrounds";
const IDB_KEY = "user_uploaded_bg";

const DEFAULT_CONFIG: BgConfig = {
  source: "none",
  overlayOpacity: 0.72,
  blurPx: 2,
};

const PRESET_PATHS = [
  { label: "Tự động nhận từ thư mục /backgrounds/", value: "auto" },
  { label: "Nền giấy kem ấm (Không dùng ảnh)", value: "none" },
  { label: "/backgrounds/bg.jpg", value: "/backgrounds/bg.jpg" },
  { label: "/backgrounds/app.jpg", value: "/backgrounds/app.jpg" },
  { label: "/backgrounds/auth.jpg", value: "/backgrounds/auth.jpg" },
];

// ── IndexedDB helpers (cho phép lưu ảnh dung lượng lớn không bị giới hạn 5MB của localStorage) ──
function openBgDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(IDB_STORE)) {
        db.createObjectStore(IDB_STORE);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function saveBlobToIdb(blob: Blob): Promise<void> {
  const db = await openBgDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, "readwrite");
    tx.objectStore(IDB_STORE).put(blob, IDB_KEY);
    tx.oncomplete = () => {
      db.close();
      resolve();
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error);
    };
  });
}

async function loadBlobUrlFromIdb(): Promise<string | null> {
  try {
    const db = await openBgDb();
    return await new Promise((resolve) => {
      const tx = db.transaction(IDB_STORE, "readonly");
      const req = tx.objectStore(IDB_STORE).get(IDB_KEY);
      req.onsuccess = () => {
        db.close();
        if (req.result instanceof Blob) {
          resolve(URL.createObjectURL(req.result));
        } else if (typeof req.result === "string") {
          resolve(req.result);
        } else {
          resolve(null);
        }
      };
      req.onerror = () => {
        db.close();
        resolve(null);
      };
    });
  } catch {
    return null;
  }
}

async function probeImageExists(url: string): Promise<boolean> {
  try {
    const res = await fetch(url, { method: "HEAD", cache: "no-store" });
    return res.ok && (res.headers.get("content-type")?.startsWith("image/") ?? false);
  } catch {
    return false;
  }
}

export function BackgroundLayer() {
  const pathname = usePathname() ?? "";
  const isAuthPage = pathname.startsWith("/login") || pathname.startsWith("/register") || pathname.startsWith("/onboarding");

  const [config, setConfig] = useState<BgConfig>(DEFAULT_CONFIG);
  const [resolvedUrl, setResolvedUrl] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [customPathInput, setCustomPathInput] = useState("");
  const [statusMsg, setStatusMsg] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Đọc cấu hình từ localStorage + lắng nghe sự kiện mở modal từ bất kỳ nút "Hình nền" nào
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<BgConfig>;
        const merged: BgConfig = {
          source: parsed.source ?? DEFAULT_CONFIG.source,
          overlayOpacity: typeof parsed.overlayOpacity === "number" ? parsed.overlayOpacity : DEFAULT_CONFIG.overlayOpacity,
          blurPx: typeof parsed.blurPx === "number" ? parsed.blurPx : DEFAULT_CONFIG.blurPx,
        };
        setConfig(merged);
        if (merged.source !== "auto" && merged.source !== "none" && merged.source !== "idb:custom") {
          setCustomPathInput(merged.source);
        }
      }
    } catch {}

    const handleOpen = () => setModalOpen(true);
    window.addEventListener("fitai:open-bg-settings", handleOpen);
    return () => window.removeEventListener("fitai:open-bg-settings", handleOpen);
  }, []);

  // Giải quyết URL ảnh thực tế dựa trên config.source
  useEffect(() => {
    let cancelled = false;
    let revokeUrl: string | null = null;

    async function resolveBg() {
      if (config.source === "none") {
        if (!cancelled) setResolvedUrl(null);
        return;
      }

      if (config.source === "idb:custom") {
        const blobUrl = await loadBlobUrlFromIdb();
        revokeUrl = blobUrl;
        if (!cancelled) setResolvedUrl(blobUrl);
        return;
      }

      if (config.source === "auto") {
        // Thử tìm file người dùng bỏ vào frontend/public/backgrounds/
        const candidates = isAuthPage
          ? [
              "/backgrounds/auth.jpg",
              "/backgrounds/auth.png",
              "/backgrounds/auth.webp",
              "/backgrounds/bg.jpg",
              "/backgrounds/bg.png",
              "/backgrounds/bg.webp",
            ]
          : [
              "/backgrounds/app.jpg",
              "/backgrounds/app.png",
              "/backgrounds/app.webp",
              "/backgrounds/bg.jpg",
              "/backgrounds/bg.png",
              "/backgrounds/bg.webp",
            ];

        for (const candidate of candidates) {
          if (await probeImageExists(candidate)) {
            if (!cancelled) setResolvedUrl(candidate);
            return;
          }
        }
        if (!cancelled) setResolvedUrl(null);
        return;
      }

      // Đường dẫn cụ thể do người dùng nhập (vd: /backgrounds/my-photo.jpg hoặc https://...)
      if (!cancelled) setResolvedUrl(config.source);
    }

    resolveBg();
    return () => {
      cancelled = true;
      if (revokeUrl && revokeUrl.startsWith("blob:")) {
        URL.revokeObjectURL(revokeUrl);
      }
    };
  }, [config.source, isAuthPage]);

  // Gắn thuộc tính data-has-bg lên <html> để các thẻ Card chuyển sang chế độ kính mờ ấm
  useEffect(() => {
    const root = document.documentElement;
    if (resolvedUrl) {
      root.setAttribute("data-has-bg", "true");
    } else {
      root.removeAttribute("data-has-bg");
    }
  }, [resolvedUrl]);

  const updateConfig = (patch: Partial<BgConfig>) => {
    setConfig((prev) => {
      const next = { ...prev, ...patch };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {}
      return next;
    });
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await saveBlobToIdb(file);
      updateConfig({ source: "idb:custom" });
      setStatusMsg(`Đã áp dụng ảnh "${file.name}"`);
      setTimeout(() => setStatusMsg(""), 3000);
    } catch {
      setStatusMsg("Không lưu được ảnh. Vui lòng thử file khác.");
    }
    e.target.value = "";
  };

  const handleApplyPath = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = customPathInput.trim();
    if (!trimmed) return;
    const normalized =
      !trimmed.startsWith("/") && !trimmed.startsWith("http://") && !trimmed.startsWith("https://")
        ? `/backgrounds/${trimmed}`
        : trimmed;
    setCustomPathInput(normalized);
    updateConfig({ source: normalized });
    setStatusMsg(`Đã đặt đường dẫn: ${normalized}`);
    setTimeout(() => setStatusMsg(""), 3000);
  };

  return (
    <>
      {/* ── Lớp nền cố định phía sau toàn bộ ứng dụng ─────────────────────── */}
      {resolvedUrl && (
        <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden select-none">
          <div
            className="absolute inset-0 bg-cover bg-center bg-no-repeat transition-all duration-500"
            style={{
              backgroundImage: `url("${resolvedUrl}")`,
              filter: config.blurPx > 0 ? `blur(${config.blurPx}px)` : undefined,
              transform: config.blurPx > 0 ? "scale(1.03)" : undefined,
            }}
          />
          <div
            className="absolute inset-0 transition-opacity duration-300"
            style={{
              backgroundColor: `rgba(245, 242, 235, ${config.overlayOpacity})`,
            }}
          />
        </div>
      )}

      {/* ── Hộp thoại tuỳ chỉnh hình nền ──────────────────────────────────── */}
      {modalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4 backdrop-blur-xs"
          role="dialog"
          aria-modal="true"
          aria-labelledby="bg-settings-title"
        >
          <div className="w-full max-w-lg rounded-card border border-line bg-[#fdfcfa] p-6 text-ink shadow-xl">
            <div className="flex items-start justify-between gap-3 border-b border-line pb-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-brand-700">
                  Không gian hiển thị
                </p>
                <h2 id="bg-settings-title" className="font-serif text-xl font-semibold text-ink">
                  Tuỳ chỉnh hình nền
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                aria-label="Đóng"
                className="rounded-control p-1.5 text-muted hover:bg-stone-200/60 hover:text-ink"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-5 space-y-5 text-sm">
              {/* Cách 1: Chọn ảnh trực tiếp từ máy */}
              <div>
                <label className="block font-medium text-ink mb-2">
                  1. Chọn ảnh trực tiếp từ máy tính của bạn
                </label>
                <div className="flex flex-wrap items-center gap-2.5">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="inline-flex items-center gap-2 rounded-control bg-brand-700 px-4 py-2 text-sm font-medium text-white shadow-xs transition-colors hover:bg-brand-800"
                  >
                    <Upload className="h-4 w-4" />
                    Tải ảnh từ máy lên
                  </button>
                  {config.source === "idb:custom" && (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-brand-700">
                      <Check className="h-3.5 w-3.5" /> Đang dùng ảnh tải từ máy
                    </span>
                  )}
                </div>
              </div>

              {/* Cách 2: Dùng ảnh trong thư mục frontend/public/backgrounds/ */}
              <div>
                <label htmlFor="bg-custom-path" className="block font-medium text-ink mb-1">
                  2. Hoặc dùng file trong thư mục <code className="rounded bg-stone-200/70 px-1.5 py-0.5 text-xs">frontend/public/backgrounds/</code>
                </label>
                <p className="text-xs text-muted mb-2">
                  Chép ảnh vào thư mục trên (ví dụ <code className="text-ink">bg.jpg</code> hoặc <code className="text-ink">my-photo.png</code>) rồi nhập tên file:
                </p>
                <form onSubmit={handleApplyPath} className="flex gap-2">
                  <input
                    id="bg-custom-path"
                    type="text"
                    value={customPathInput}
                    onChange={(e) => setCustomPathInput(e.target.value)}
                    placeholder="Ví dụ: bg.jpg hoặc /backgrounds/gym.jpg"
                    className="min-w-0 flex-1 rounded-control border border-line bg-white px-3 py-2 text-sm text-ink placeholder-subtle focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/20"
                  />
                  <button
                    type="submit"
                    className="shrink-0 rounded-control border border-line bg-stone-100 px-3.5 py-2 text-sm font-medium text-ink hover:bg-stone-200/70"
                  >
                    Áp dụng
                  </button>
                </form>

                <div className="mt-2.5 flex flex-wrap gap-1.5">
                  {PRESET_PATHS.map((preset) => (
                    <button
                      key={preset.value}
                      type="button"
                      onClick={() => updateConfig({ source: preset.value })}
                      className={cn(
                        "rounded-control border px-2.5 py-1 text-xs font-medium transition-colors",
                        config.source === preset.value
                          ? "border-brand-700 bg-brand-50 text-brand-800"
                          : "border-line bg-white text-muted hover:bg-stone-100 hover:text-ink"
                      )}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Thanh trượt độ phủ mờ & độ nhòe */}
              <div className="grid gap-4 rounded-control border border-line bg-stone-100/70 p-3.5 sm:grid-cols-2">
                <div>
                  <div className="flex justify-between text-xs font-medium text-ink mb-1">
                    <span>Độ phủ nền giấy (để rõ chữ)</span>
                    <span className="tabular-nums">{Math.round(config.overlayOpacity * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min={0.15}
                    max={0.92}
                    step={0.03}
                    value={config.overlayOpacity}
                    onChange={(e) => updateConfig({ overlayOpacity: parseFloat(e.target.value) })}
                    className="w-full accent-brand-700"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-xs font-medium text-ink mb-1">
                    <span>Độ làm dịu ảnh (Blur)</span>
                    <span className="tabular-nums">{config.blurPx}px</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={16}
                    step={1}
                    value={config.blurPx}
                    onChange={(e) => updateConfig({ blurPx: parseInt(e.target.value, 10) })}
                    className="w-full accent-brand-700"
                  />
                </div>
              </div>

              {statusMsg && (
                <p className="rounded-control bg-brand-50 px-3 py-2 text-xs font-medium text-brand-800">
                  {statusMsg}
                </p>
              )}
            </div>

            <div className="mt-6 flex items-center justify-between border-t border-line pt-4">
              <button
                type="button"
                onClick={() => {
                  setCustomPathInput("");
                  updateConfig(DEFAULT_CONFIG);
                  setStatusMsg("Đã khôi phục mặc định.");
                }}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-muted hover:text-ink"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Khôi phục mặc định
              </button>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="rounded-control bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-800"
              >
                Xong
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/** Nút mở nhanh hộp thoại đổi hình nền (dùng ở AppHeader và trang Login/Register) */
export function BackgroundSettingsButton({ className }: { className?: string }) {
  return (
    <button
      type="button"
      onClick={() => window.dispatchEvent(new CustomEvent("fitai:open-bg-settings"))}
      title="Tuỳ chỉnh hình nền"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-control border border-line bg-surface/80 px-2.5 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-stone-200/50 hover:text-ink",
        className
      )}
    >
      <ImageIcon aria-hidden className="h-3.5 w-3.5" />
      <span>Hình nền</span>
    </button>
  );
}

