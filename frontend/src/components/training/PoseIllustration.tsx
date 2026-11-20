"use client";

import type { PoseKey } from "@/data/guidedRoutines";

/** Minh họa SVG vector từng tư thế bài tập cơ bản (trực quan, không cần ảnh/video ngoài). */
export function PoseIllustration({ pose, accent = "#2ebd85" }: { pose: PoseKey; accent?: string }) {
  return (
    <svg
      viewBox="0 0 200 160"
      className="h-40 w-full max-w-[220px] select-none"
      role="img"
      aria-label={`Minh họa tư thế ${pose}`}
    >
      <rect x="8" y="8" width="184" height="144" rx="20" fill="#fbfaf8" stroke="#e5e0d8" strokeWidth="1.5" />
      {/* Đường mặt sàn */}
      <line x1="28" y1="134" x2="172" y2="134" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" />

      {pose === "neck_roll" && (
        <g stroke="#334155" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" fill="none">
          <circle cx="100" cy="48" r="14" fill="#fff" />
          <path d="M100 62 V102 M72 78 H128 M84 102 L78 134 M116 102 L122 134" />
          {/* Mũi tên cong hướng dẫn xoay cổ chữ U */}
          <path d="M78 54 C84 68, 116 68, 122 54" stroke={accent} strokeWidth="2.6" />
          <polyline points="118,50 123,54 119,59" stroke={accent} strokeWidth="2.4" />
          <polyline points="82,50 77,54 81,59" stroke={accent} strokeWidth="2.4" />
        </g>
      )}

      {pose === "shoulder_roll" && (
        <g stroke="#334155" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" fill="none">
          <circle cx="100" cy="40" r="12" fill="#fff" />
          <path d="M100 52 V102 M78 68 L122 68 M84 102 L80 134 M116 102 L120 134" />
          {/* Hai tay đặt vai */}
          <path d="M78 68 L64 78 L78 64 M122 68 L136 78 L122 64" />
          {/* Vòng tròn xoay ở 2 vai */}
          <circle cx="66" cy="70" r="12" stroke={accent} strokeWidth="2.2" strokeDasharray="4 3" />
          <circle cx="134" cy="70" r="12" stroke={accent} strokeWidth="2.2" strokeDasharray="4 3" />
        </g>
      )}

      {pose === "hip_circle" && (
        <g stroke="#334155" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" fill="none">
          <circle cx="100" cy="34" r="11" fill="#fff" />
          <path d="M100 45 V86 M74 58 L64 76 L88 84 M126 58 L136 76 L112 84 M74 58 H126" />
          <path d="M88 84 L78 134 M112 84 L122 134" />
          {/* Vòng xoay hông */}
          <ellipse cx="100" cy="84" rx="34" ry="10" stroke={accent} strokeWidth="2.5" strokeDasharray="5 3" />
          <polyline points="128,79 135,84 128,89" stroke={accent} strokeWidth="2.3" />
        </g>
      )}

      {pose === "knee_bend" && (
        <g stroke="#334155" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" fill="none">
          <circle cx="96" cy="36" r="11" fill="#fff" />
          {/* Thân hơi gập nhẹ & tay đưa trước */}
          <path d="M96 47 L88 86 L114 106 L104 134" />
          <path d="M93 60 L126 64" />
          <path d="M114 106 L118 134" strokeOpacity="0.45" />
          {/* Mũi tên lên xuống ở hông */}
          <path d="M62 72 V102" stroke={accent} strokeWidth="2.5" />
          <polyline points="57,78 62,71 67,78" stroke={accent} strokeWidth="2.3" />
          <polyline points="57,96 62,103 67,96" stroke={accent} strokeWidth="2.3" />
        </g>
      )}

      {pose === "ankle_raise" && (
        <g stroke="#334155" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" fill="none">
          <circle cx="100" cy="34" r="11" fill="#fff" />
          <path d="M100 45 V88 M78 60 L122 60 M88 88 L86 124 L94 134 M112 88 L114 124 L122 134" />
          {/* Điểm nhấn nhón gót ở bàn chân */}
          <path d="M78 122 C72 130, 82 136, 92 134" stroke={accent} strokeWidth="2.4" />
          <path d="M122 122 C128 130, 118 136, 108 134" stroke={accent} strokeWidth="2.4" />
          <path d="M142 128 V110" stroke={accent} strokeWidth="2.4" />
          <polyline points="137,116 142,109 147,116" stroke={accent} strokeWidth="2.2" />
        </g>
      )}

      {pose === "neck_tilt" && (
        <g stroke="#334155" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" fill="none">
          {/* Đầu nghiêng sang phải */}
          <circle cx="109" cy="48" r="13" fill="#fff" />
          <path d="M100 60 V106 M76 74 H124 M84 106 L80 134 M116 106 L120 134" />
          {/* Tay phải đặt hờ lên đầu */}
          <path d="M124 74 L134 52 L116 36" />
          {/* Cung mũi tên nghiêng đầu */}
          <path d="M88 32 C98 24, 114 26, 122 36" stroke={accent} strokeWidth="2.5" />
          <polyline points="116,37 123,37 122,30" stroke={accent} strokeWidth="2.2" />
        </g>
      )}

      {pose === "overhead_reach" && (
        <g stroke="#334155" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" fill="none">
          <circle cx="100" cy="54" r="11" fill="#fff" />
          <path d="M100 65 V102 M86 102 L82 134 M114 102 L118 134" />
          {/* Hai tay vươn thẳng lên đan nhau */}
          <path d="M82 68 L84 32 L100 24 L116 32 L118 68 Z" fill="none" />
          <path d="M62 56 V28 M138 56 V28" stroke={accent} strokeWidth="2.4" />
          <polyline points="57,34 62,27 67,34" stroke={accent} strokeWidth="2.2" />
          <polyline points="133,34 138,27 143,34" stroke={accent} strokeWidth="2.2" />
        </g>
      )}

      {pose === "cat_cow" && (
        <g stroke="#334155" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" fill="none">
          {/* Tư thế bò/mèo chống 4 điểm */}
          <circle cx="144" cy="78" r="11" fill="#fff" />
          {/* Lưng cong (mèo) */}
          <path d="M66 90 C84 62, 118 62, 134 82" />
          {/* Đường cong võng (bò) bằng nét đứt màu nhấn */}
          <path d="M66 90 C88 106, 116 104, 134 86" stroke={accent} strokeWidth="2.5" strokeDasharray="4 3" />
          {/* Chân & tay chống sàn */}
          <path d="M66 90 V134 M134 86 L136 134 M66 124 L52 134" />
          <path d="M100 52 V68" stroke={accent} strokeWidth="2.4" />
          <polyline points="96,57 100,51 104,57" stroke={accent} strokeWidth="2.2" />
        </g>
      )}

      {pose === "child_pose" && (
        <g stroke="#334155" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" fill="none">
          {/* Gập người ngồi trên gót, hai tay duỗi dài phía trước */}
          <path d="M52 134 H84 L74 114 L56 128" />
          <path d="M74 114 C94 98, 120 106, 134 120" />
          <circle cx="140" cy="124" r="10" fill="#fff" />
          <path d="M132 126 L166 134" />
          <path d="M98 88 C108 82, 122 86, 128 94" stroke={accent} strokeWidth="2.4" />
        </g>
      )}
    </svg>
  );
}
