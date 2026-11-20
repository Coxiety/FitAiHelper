# Căn cứ Khoa học & Tài liệu Tham chiếu cho Các Chỉ số Sức khỏe FitAI

Tài liệu này tổng hợp đầy đủ các công trình khoa học, hướng dẫn của tổ chức y tế quốc tế và quy ước kỹ thuật được sử dụng để tính toán chỉ số sức khỏe cá nhân trong FitAI (`backend/services/metrics_service.py` và giao diện Dashboard).

---

## 1. Chỉ số khối cơ thể — BMI (Body Mass Index)

**Công thức:**
$$\text{BMI} = \frac{\text{Cân nặng (kg)}}{\left(\text{Chiều cao (m)}\right)^2}$$

FitAI hiển thị đồng thời **2 hệ phân loại** để người dùng Việt Nam vừa đối chiếu chuẩn quốc tế vừa theo dõi ngưỡng nguy cơ chuyển hóa của người châu Á:

### 1.1. Ngưỡng WHO Quốc tế (Global Cut-offs)
- **Phân loại:** `< 18.5` Thiếu cân · `18.5 – 24.9` Bình thường · `25.0 – 29.9` Thừa cân · `≥ 30.0` Béo phì.
- **Tài liệu gốc:** World Health Organization (WHO), *Obesity: Preventing and Managing the Global Epidemic*, WHO Technical Report Series No. 894, Geneva, 2000.

### 1.2. Ngưỡng WHO Châu Á – Thái Bình Dương (Khuyến nghị tham khảo cho người Việt)
- **Phân loại:** `< 18.5` Thiếu cân · `18.5 – 22.9` Bình thường · `23.0 – 24.9` Thừa cân · `≥ 25.0` Béo phì.
- **Căn cứ:** Ở cùng mức BMI, người châu Á thường có tỷ lệ mỡ cơ thể cao hơn và nguy cơ tim mạch–chuyển hóa xuất hiện ở ngưỡng BMI thấp hơn người châu Âu/Bắc Mỹ.
- **Tài liệu gốc:** WHO Regional Office for the Western Pacific (WPRO), International Association for the Study of Obesity (IASO), International Obesity Task Force (IOTF), *The Asia-Pacific Perspective: Redefining Obesity and Its Treatment*, Health Communications Australia, 2000. ISBN: `978-0957708211`.
  - Liên kết lưu trữ WHO IRIS: https://apps.who.int/iris/handle/10665/206936

---

## 2. Tỷ lệ trao đổi chất cơ bản — BMR (Mifflin-St Jeor, 1990)

**Công thức:**
- **Nam:** $\text{BMR} = 10 \times \text{Cân nặng (kg)} + 6.25 \times \text{Chiều cao (cm)} - 5 \times \text{Tuổi} + 5$
- **Nữ:** $\text{BMR} = 10 \times \text{Cân nặng (kg)} + 6.25 \times \text{Chiều cao (cm)} - 5 \times \text{Tuổi} - 161$
- **Giới tính khác (`other`):** Dùng hằng số trung bình cộng `(-161 + 5) / 2 = -78` *(quy ước xấp xỉ kỹ thuật của hệ thống, không phải hằng số lâm sàng gốc)*.

- **Tài liệu gốc:** Mifflin M.D., St Jeor S.T., Hill L.A., Scott B.J., Daugherty S.A., Koh Y.O. (1990), *"A new predictive equation for resting energy expenditure in healthy individuals"*, *The American Journal of Clinical Nutrition*, Vol. 51, Issue 2, pp. 241–247 (PMID: `2305711`).
  - DOI: https://doi.org/10.1093/ajcn/51.2.241

---

## 3. Tổng tiêu hao năng lượng ngày — TDEE & Mức độ vận động

**Công thức:**
$$\text{TDEE} = \text{BMR} \times \text{Hệ số vận động}$$

- **Cơ sở sinh lý học:** Tổng tiêu hao năng lượng hàng ngày (TEE/TDEE) được biểu diễn dưới dạng bội số của chuyển hóa cơ bản ($\text{TEE} = \text{BMR} \times \text{PAL}$ — Physical Activity Level).
- **Tài liệu gốc:** Joint FAO/WHO/UNU Expert Consultation (2004), *Human Energy Requirements*, FAO Food and Nutrition Technical Report Series No. 1, Rome. ISBN: `978-92-5-105212-9`.
  - Toàn văn FAO: https://www.fao.org/4/y5686e/y5686e00.htm
  - Thang PAL tổng quát của FAO/WHO/UNU: `1.40–1.69` (ít/nhẹ), `1.70–1.99` (vừa/năng động), `2.00–2.40` (vận động nặng).
- **Ghi chú minh bạch kỹ thuật:** 5 mức hệ số chi tiết FitAI sử dụng (`1.2`, `1.375`, `1.55`, `1.725`, `1.9`) là thang quy ước thực hành phổ biến trong tính toán dinh dưỡng cá nhân (Harris-Benedict / Katch-McArdle activity multipliers) để chia nhỏ mức tập luyện hàng tuần.

---

## 4. Calo mục tiêu & Ngưỡng sàn an toàn (Calorie Floor)

- **Điều chỉnh theo mục tiêu (quy ước thực hành):**
  - Giảm cân (`weight_loss`): `TDEE × 0.85` (thâm hụt vừa phải 15%).
  - Tăng cơ (`muscle_gain`): `TDEE × 1.10` (thặng dư nhẹ 10%).
  - Duy trì / Sức bền (`maintenance` / `endurance`): `TDEE × 1.00`.
- **Ngưỡng sàn calo tối thiểu (`1,200 kcal/ngày` cho nữ · `1,500 kcal/ngày` cho nam · `1,350 kcal/ngày` quy ước trung bình cho `other`):**
  - **Tài liệu căn cứ:** Harvard Health Publishing (*Calorie counting made easy*) và NIH / National Institute of Diabetes and Digestive and Kidney Diseases (NIDDK) khuyến cáo người trưởng thành không tự hạ mức ăn hàng ngày xuống dưới `1,200 kcal` (nữ) hoặc `1,500 kcal` (nam) khi không có giám sát y tế chuyên khoa nhằm phòng ngừa thiếu vi chất, mất khối cơ và rối loạn chuyển hóa.

---

## 5. Phân bổ Đa lượng — Macronutrients (Protein, Fat, Carb)

- **Lượng đạm (`Protein`):**
  - Giảm cân / Tăng cơ: `2.0 g/kg` cân nặng · Duy trì / Sức bền: `1.6 g/kg` cân nặng.
  - **Tài liệu gốc:** Aragon A.A. et al. (2017), *International Society of Sports Nutrition (ISSN) Position Stand: Diets and Body Composition*, *J Int Soc Sports Nutr* 14:16 (khuyến nghị `1.4–2.0 g/kg/ngày` cho người tập luyện và mức cao hơn quanh `~2.0 g/kg` khi thâm hụt năng lượng để bảo toàn khối cơ). *(Đã có file PDF gốc trong `data/knowledge/raw/issn_diets_body_composition_2017_en.pdf`.)*
    - DOI: https://doi.org/10.1186/s12970-017-0174-y
- **Chất béo (`Fat = 25%` calo mục tiêu) & Tinh bột (`Carb = phần calo còn lại`):**
  - **Tài liệu gốc:** National Academies / Institute of Medicine (IOM), *Dietary Reference Intakes (DRIs): Acceptable Macronutrient Distribution Ranges (AMDR)* — khuyến nghị người trưởng thành tiêu thụ chất béo `20–35%`, tinh bột `45–65%`, và protein `10–35%` tổng năng lượng (hệ số quy đổi năng lượng Atwater: Protein `4 kcal/g`, Fat `9 kcal/g`, Carb `4 kcal/g`).

---

## 6. Khuyến nghị Hoạt động Thể chất Cơ bản

- **Mức khuyến nghị cho người trưởng thành (18–64 tuổi):** Tối thiểu `150–300 phút/tuần` vận động hiếu khí cường độ trung bình (hoặc `75–150 phút` cường độ mạnh), kết hợp tập tăng cường sức mạnh cơ bắp `≥ 2 ngày/tuần`.
- **Tài liệu gốc:** World Health Organization (WHO, 2020), *WHO Guidelines on Physical Activity and Sedentary Behaviour*, ISBN `978-92-4-001512-8` *(đã có file PDF gốc trong `data/knowledge/raw/who_physical_activity_sedentary_2020_en.pdf`)*.
