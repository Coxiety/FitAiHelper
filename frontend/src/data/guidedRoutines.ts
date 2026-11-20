export type GuidedRoutineKind = "breathing" | "mobility";

export type PoseKey =
  | "neck_roll"
  | "shoulder_roll"
  | "hip_circle"
  | "knee_bend"
  | "ankle_raise"
  | "neck_tilt"
  | "overhead_reach"
  | "cat_cow"
  | "child_pose";

export interface BreathingPhase {
  key: "inhale" | "hold" | "exhale" | "rest";
  label: string;
  instruction: string;
  seconds: number;
  color: string;
}

export interface GuidedStep {
  title: string;
  durationSec: number;
  pose: PoseKey;
  instructions: string[];
  breathingCue: string;
  safetyTip: string;
}

export interface GuidedRoutine {
  id: string;
  kind: GuidedRoutineKind;
  title: string;
  subtitle: string;
  durationLabel: string;
  logMinutes: number;
  badge: string;
  accentColor: string;
  benefit: string;
  setupSteps: string[];
  cycles?: number;
  phases?: BreathingPhase[];
  steps?: GuidedStep[];
}

export const GUIDED_ROUTINES: GuidedRoutine[] = [
  {
    id: "box-breathing",
    kind: "breathing",
    title: "Tập thở Hộp (Box Breathing 4–4–4–4)",
    subtitle: "Điều hòa nhịp tim, giảm căng thẳng tức thì bằng nhịp 4 giây đều đặn",
    durationLabel: "6 chu kỳ · ~2 phút",
    logMinutes: 2,
    badge: "Tập thở trực quan",
    accentColor: "#2ebd85",
    benefit: "Giúp làm dịu hệ thần kinh giao cảm, ổn định nhịp thở trước khi làm việc hoặc sau vận động.",
    setupSteps: [
      "Ngồi thẳng lưng trên ghế hoặc xếp bằng thoải mái, thả lỏng hai vai.",
      "Đặt một tay lên bụng dưới để cảm nhận cơ hoành phồng lên khi hít vào.",
      "Thở hết hơi cũ nhẹ nhàng qua miệng trước khi bấm Bắt đầu.",
    ],
    cycles: 6,
    phases: [
      {
        key: "inhale",
        label: "Hít vào chậm",
        instruction: "Hít sâu bằng mũi, cảm nhận bụng dưới phồng đều theo vòng tròn mở rộng.",
        seconds: 4,
        color: "#2ebd85",
      },
      {
        key: "hold",
        label: "Giữ hơi",
        instruction: "Giữ nhẹ lồng ngực và vai thả lỏng, không gồng cổ.",
        seconds: 4,
        color: "#7c5ce6",
      },
      {
        key: "exhale",
        label: "Thở ra đều",
        instruction: "Thở ra từ từ qua miệng hoặc mũi, bụng xẹp xuống tự nhiên.",
        seconds: 4,
        color: "#1ca8d4",
      },
      {
        key: "rest",
        label: "Nghỉ nhẹ",
        instruction: "Giữ trạng thái tĩnh lặng 4 giây trước chu kỳ tiếp theo.",
        seconds: 4,
        color: "#64748b",
      },
    ],
  },
  {
    id: "breathing-478",
    kind: "breathing",
    title: "Tập thở Thư giãn 4–7–8",
    subtitle: "Kéo dài thì thở ra giúp hạ nhịp tim và dễ vào giấc ngủ",
    durationLabel: "5 chu kỳ · ~2 phút",
    logMinutes: 2,
    badge: "Tập thở thư giãn",
    accentColor: "#7c5ce6",
    benefit: "Thì thở ra dài gấp đôi thì hít vào kích hoạt phản xạ thư giãn tự nhiên của cơ thể.",
    setupSteps: [
      "Ngồi dựa lưng thoải mái hoặc nằm ngửa duỗi chân tay tự nhiên.",
      "Đầu lưỡi chạm nhẹ mặt sau răng cửa trên trong suốt bài tập.",
      "Nếu mới tập thấy hơi hụt ở thì giữ 7 giây, có thể chuyển sang bước kế tiếp bất cứ lúc nào.",
    ],
    cycles: 5,
    phases: [
      {
        key: "inhale",
        label: "Hít vào mũi",
        instruction: "Hít nhẹ nhàng qua mũi trong 4 giây, không nhún vai.",
        seconds: 4,
        color: "#2ebd85",
      },
      {
        key: "hold",
        label: "Giữ hơi",
        instruction: "Giữ hơi nhẹ nhàng, giữ cơ mặt và hàm thư giãn.",
        seconds: 7,
        color: "#7c5ce6",
      },
      {
        key: "exhale",
        label: "Thở ra miệng",
        instruction: "Chu nhẹ môi, thở ra êm và dài trọn vẹn 8 giây.",
        seconds: 8,
        color: "#1ca8d4",
      },
    ],
  },
  {
    id: "joint-warmup",
    kind: "mobility",
    title: "Khởi động khớp cơ bản toàn thân",
    subtitle: "5 bước làm nóng từ cổ đến cổ chân cho người mới, không động tác nhảy",
    durationLabel: "5 bước · ~3 phút",
    logMinutes: 3,
    badge: "Hướng dẫn từng bước",
    accentColor: "#d9822b",
    benefit: "Bôi trơn dịch khớp, tăng lưu thông máu nhẹ nhàng trước khi tập hoặc giữa giờ ngồi làm việc.",
    setupSteps: [
      "Đứng thẳng hai chân mở rộng bằng vai, đầu gối hơi thả lỏng (không khóa khớp).",
      "Thực hiện chậm rãi trong biên độ thoải mái, dừng lại ngay nếu thấy đau nhói.",
    ],
    steps: [
      {
        title: "Xoay cổ nửa vòng trước",
        durationSec: 30,
        pose: "neck_roll",
        instructions: [
          "Giữ hai vai cố định và hạ thấp tự nhiên.",
          "Cúi nhẹ cằm về phía ngực, lăn đầu chậm sang vai trái rồi sang vai phải theo hình chữ U.",
          "Lặp lại đều đặn 4–5 lần mỗi bên.",
        ],
        breathingCue: "Hít vào khi đầu ở giữa, thở ra chậm khi nghiêng sang hai bên.",
        safetyTip: "Tránh ngửa cổ quá sâu ra sau để không chèn ép đốt sống cổ.",
      },
      {
        title: "Xoay vai mở lồng ngực",
        durationSec: 30,
        pose: "shoulder_roll",
        instructions: [
          "Đặt nhẹ đầu ngón tay lên hai mỏm vai (hoặc buông tay dọc thân).",
          "Vẽ vòng tròn lớn bằng khuỷu tay: nâng lên trước → kéo ra sau → hạ xuống.",
          "Đổi chiều xoay sau 15 giây.",
        ],
        breathingCue: "Hít sâu khi mở ngực ra sau, thở ra khi khép tay về trước.",
        safetyTip: "Giữ lưng thẳng, không ưỡn thắt lưng quá mức.",
      },
      {
        title: "Xoay hông vòng tròn",
        durationSec: 30,
        pose: "hip_circle",
        instructions: [
          "Hai tay chống hông, hai chân rộng bằng vai.",
          "Đẩy hông vẽ vòng tròn rộng mượt mà theo chiều kim đồng hồ 15 giây.",
          "Đổi chiều ngược lại 15 giây còn lại.",
        ],
        breathingCue: "Thở đều tự nhiên theo chuyển động vòng tròn.",
        safetyTip: "Giữ phần thân trên ổn định, chuyển động tập trung vào khớp hông.",
      },
      {
        title: "Gập duỗi khớp gối nhẹ",
        durationSec: 40,
        pose: "knee_bend",
        instructions: [
          "Hai chân song song rộng bằng hông, tay đặt nhẹ lên đùi hoặc trước ngực.",
          "Chùng nhẹ gối hạ hông khoảng 10–15 cm như sắp ngồi ghế rồi đứng thẳng lại.",
          "Thực hiện chậm có kiểm soát.",
        ],
        breathingCue: "Hít vào khi chùng gối xuống, thở ra khi đứng lên.",
        safetyTip: "Hướng đầu gối theo hướng mũi chân, không để hai gối chụm vào trong.",
      },
      {
        title: "Kiễng gót & xoay cổ chân",
        durationSec: 40,
        pose: "ankle_raise",
        instructions: [
          "Nhón nhẹ hai gót chân lên khỏi sàn 1 giây rồi hạ xuống êm ái (10 lần).",
          "Sau đó nhấc nhẹ từng mũi chân xoay tròn cổ chân 10 giây mỗi bên.",
        ],
        breathingCue: "Nhịp thở chậm đều, giữ mắt nhìn một điểm cố định để thăng bằng.",
        safetyTip: "Có thể vịn nhẹ vào tường hoặc lưng ghế nếu cần hỗ trợ thăng bằng.",
      },
    ],
  },
  {
    id: "desk-stretch",
    kind: "mobility",
    title: "Giãn cơ Cổ – Vai – Lưng (Chống mỏi ngồi lâu)",
    subtitle: "4 động tác giải tỏa căng cứng vai gáy và thắt lưng từng bước rõ ràng",
    durationLabel: "4 bước · ~3 phút",
    logMinutes: 3,
    badge: "Giãn cơ từng bước",
    accentColor: "#1ca8d4",
    benefit: "Giảm áp lực cột sống và cơ thang trên sau nhiều giờ ngồi máy tính.",
    setupSteps: [
      "Chuẩn bị một khoảng sàn êm (hoặc thảm) cho 2 động tác cuối; 2 bước đầu có thể tập ngồi hoặc đứng.",
      "Giữ cảm giác căng dễ chịu, tuyệt đối không giật mạnh.",
    ],
    steps: [
      {
        title: "Nghiêng cổ giãn cơ thang",
        durationSec: 30,
        pose: "neck_tilt",
        instructions: [
          "Giữ lưng thẳng, nghiêng nhẹ tai phải về phía vai phải.",
          "Dùng tay phải đặt hờ lên thái dương trái (không kéo mạnh), vai trái hạ thấp xuống.",
          "Giữ 15 giây rồi đổi sang bên trái.",
        ],
        breathingCue: "Mỗi nhịp thở ra, thả lỏng thêm vai đối diện xuống dưới.",
        safetyTip: "Chỉ tựa nhẹ trọng lượng bàn tay, không bẻ hoặc giật cổ.",
      },
      {
        title: "Đan tay vươn cao mở ngực",
        durationSec: 30,
        pose: "overhead_reach",
        instructions: [
          "Đan hai bàn tay trước ngực, xoay lòng bàn tay hướng ra ngoài.",
          "Vươn thẳng hai tay lên cao qua đầu, kéo dài nhẹ hai bên lườn.",
          "Giữ tư thế trong 30 giây.",
        ],
        breathingCue: "Hít vào nâng cao lồng ngực, thở ra giữ nguyên tay nhưng thả mềm cổ.",
        safetyTip: "Không nhún vai chạm sát tai; giữ bụng hơi siết nhẹ để bảo vệ thắt lưng.",
      },
      {
        title: "Tư thế Mèo – Bò (Cat–Cow)",
        durationSec: 45,
        pose: "cat_cow",
        instructions: [
          "Chống hai tay và hai đầu gối xuống sàn (bàn tay dưới vai, gối dưới hông).",
          "Thì 1 (Bò): Hít vào, hạ nhẹ bụng, mở ngực và ngẩng nhẹ mặt nhìn về trước.",
          "Thì 2 (Mèo): Thở ra, đẩy lòng bàn tay xuống sàn, cuộn tròn lưng lên cao và thu cằm.",
        ],
        breathingCue: "Chuyển động chậm khớp hoàn toàn theo 1 nhịp hít vào — 1 nhịp thở ra.",
        safetyTip: "Lót khăn dưới đầu gối nếu sàn cứng; không ép cong lưng quá đau.",
      },
      {
        title: "Tư thế Em bé (Child’s Pose)",
        durationSec: 45,
        pose: "child_pose",
        instructions: [
          "Từ tư thế chống gối, mở nhẹ hai đầu gối rộng hơn hông, hai ngón chân cái chạm nhau.",
          "Đẩy mông ngồi về gót chân, vươn dài hai tay về phía trước và hạ trán xuống thảm.",
          "Nhắm mắt thả lỏng toàn bộ lưng dưới và vai.",
        ],
        breathingCue: "Hít sâu phồng nhẹ bụng chạm đùi, thở ra buông lỏng hoàn toàn.",
        safetyTip: "Nếu gối căng, đặt một chiếc gối mỏng giữa đùi và bắp chân.",
      },
    ],
  },
];
