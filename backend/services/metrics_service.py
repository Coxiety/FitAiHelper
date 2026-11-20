"""Service tính toán chỉ số cơ thể (BMI, BMR, TDEE, Calo mục tiêu, Macro).

Đây là service thuần túy (pure functions): không phụ thuộc database,
không gọi mô hình AI/LLM. Nhận số liệu vào và tính toán trả về số liệu.
"""
from dataclasses import dataclass
from typing import Optional


# ── 1. Hệ số mức độ vận động (Activity Multipliers) ───────────────────────────
# Dựa trên công thức chuẩn tính TDEE từ BMR
ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,       # Ít vận động (ngồi nhiều, làm việc văn phòng)
    "light": 1.375,         # Vận động nhẹ (tập 1–3 ngày/tuần)
    "moderate": 1.55,       # Vận động vừa (tập 3–5 ngày/tuần)
    "active": 1.725,        # Năng động / vận động nặng (tập thể thao 6–7 ngày/tuần)
    "very_active": 1.9,     # Rất năng động / rất nặng (vận động viên, lao động thể lực nặng)
}

# ── 2. Tỷ lệ điều chỉnh calo theo mục tiêu (Goal Calorie Factors) ──────────────
GOAL_CALORIE_ADJUSTMENTS = {
    "weight_loss": 0.85,    # Giảm cân: thâm hụt 15% calo (TDEE * 0.85)
    "muscle_gain": 1.10,    # Tăng cơ: thặng dư 10% calo (TDEE * 1.10)
    "maintenance": 1.00,    # Duy trì: giữ nguyên calo tiêu thụ (TDEE * 1.00)
    # QUY ƯỚC ĐƠN GIẢN HÓA: Với mục tiêu sức bền (endurance), calo mục tiêu
    # được tính tương đương mức duy trì năng lượng (TDEE * 1.00)
    "endurance": 1.00,
}

# ── 3. Calo sàn tối thiểu (Calorie Floors) ────────────────────────────────────
# Chặn dưới an toàn y tế: không để calo mục tiêu quá thấp gây suy dinh dưỡng
CALORIE_FLOORS = {
    "male": 1500,           # Nam tối thiểu 1500 kcal
    "female": 1200,         # Nữ tối thiểu 1200 kcal
    # QUY ƯỚC XẤP XỈ: Với giới tính khác ("other"), lấy xấp xỉ mức trung bình (1350 kcal)
    # (đây là quy ước xấp xỉ hệ thống, không phải công thức y khoa chuẩn)
    "other": 1350,
}

# ── 4. Hằng số điều chỉnh BMR theo giới tính (Mifflin-St Jeor Gender Constant) ──
BMR_GENDER_CONSTANTS = {
    "male": 5.0,            # Nam: +5
    "female": -161.0,       # Nữ: -161
    # QUY ƯỚC XẤP XỈ: Lấy trung bình cộng giữa nam và nữ ((+5 + (-161)) / 2 = -78)
    # (đây là quy ước xấp xỉ hệ thống, không phải công thức y khoa chuẩn)
    "other": -78.0,
}

# ── 5. Nhu cầu Protein theo mục tiêu (Protein g/kg body weight) ────────────────
PROTEIN_GRAMS_PER_KG = {
    "weight_loss": 2.0,     # Giảm cân: 2.0 g/kg (bảo toàn khối cơ khi thâm hụt calo)
    "muscle_gain": 2.0,     # Tăng cơ: 2.0 g/kg (tối ưu hóa tổng hợp protein cơ)
    "maintenance": 1.6,     # Duy trì: 1.6 g/kg
    # QUY ƯỚC ĐƠN GIẢN HÓA: Với mục tiêu sức bền (endurance), protein tính 1.6 g/kg
    "endurance": 1.6,
}

# ── 6. Phân bổ Chất béo & Tỷ lệ năng lượng vi chất (Macronutrients) ───────────
FAT_CALORIE_PERCENT = 0.25      # 25% tổng calo mục tiêu đến từ chất béo
CALORIES_PER_GRAM_PROTEIN = 4  # 1g Protein = 4 kcal
CALORIES_PER_GRAM_FAT = 9      # 1g Fat = 9 kcal
CALORIES_PER_GRAM_CARB = 4     # 1g Carb = 4 kcal


@dataclass
class BodyMetricsResult:
    bmi: float
    bmi_category: str
    bmi_asia_category: str
    bmr: float
    tdee: float
    target_calories: int
    calorie_floor_applied: bool
    protein_g: int
    fat_g: int
    carb_g: int


# ── 7. Danh mục căn cứ tài liệu khoa học (dùng cho API & giao diện trực quan) ──
HEALTH_METRICS_REFERENCES: tuple[dict[str, str | int], ...] = (
    {
        "key": "bmi_global",
        "metric": "BMI (Chuẩn WHO Quốc tế)",
        "formula": "BMI = Cân nặng (kg) / [Chiều cao (m)]² (<18.5 Thiếu cân; 18.5–24.9 Bình thường; 25.0–29.9 Thừa cân; ≥30 Béo phì)",
        "source_title": "Obesity: Preventing and Managing the Global Epidemic (WHO Technical Report Series 894)",
        "authors_org": "World Health Organization (WHO)",
        "year": 2000,
        "identifier": "WHO TRS 894",
        "url": "https://www.who.int/publications/i/item/9241208945",
        "notes": "Ngưỡng phân loại BMI chuẩn quốc tế cho người trưởng thành.",
    },
    {
        "key": "bmi_asia",
        "metric": "BMI (Chuẩn WHO Châu Á – Thái Bình Dương)",
        "formula": "<18.5 Thiếu cân; 18.5–22.9 Bình thường; 23.0–24.9 Thừa cân; ≥25.0 Béo phì",
        "source_title": "The Asia-Pacific Perspective: Redefining Obesity and Its Treatment",
        "authors_org": "WHO Regional Office for the Western Pacific (WPRO) / IASO / IOTF",
        "year": 2000,
        "identifier": "ISBN 978-0957708211",
        "url": "https://apps.who.int/iris/handle/10665/206936",
        "notes": "Khuyến nghị tham khảo cho người châu Á/Việt Nam do nguy cơ chuyển hóa xuất hiện ở ngưỡng BMI thấp hơn.",
    },
    {
        "key": "bmr",
        "metric": "BMR (Mifflin-St Jeor)",
        "formula": "10 × kg + 6.25 × cm − 5 × tuổi + c (Nam: c = +5, Nữ: c = −161)",
        "source_title": "A new predictive equation for resting energy expenditure in healthy individuals",
        "authors_org": "Mifflin M.D., St Jeor S.T. et al. — Am J Clin Nutr 51(2):241–247",
        "year": 1990,
        "identifier": "DOI 10.1093/ajcn/51.2.241",
        "url": "https://doi.org/10.1093/ajcn/51.2.241",
        "notes": "Với giới tính 'other', hệ thống dùng giá trị trung bình kỹ thuật c = −78 (không phải hằng số lâm sàng gốc).",
    },
    {
        "key": "tdee",
        "metric": "TDEE (Tổng tiêu hao năng lượng ngày)",
        "formula": "TDEE = BMR × Hệ số vận động (1.2 / 1.375 / 1.55 / 1.725 / 1.9)",
        "source_title": "Human Energy Requirements: Report of a Joint FAO/WHO/UNU Expert Consultation",
        "authors_org": "FAO / WHO / UNU (Food and Nutrition Technical Report Series No. 1)",
        "year": 2004,
        "identifier": "ISBN 978-92-5-105212-9",
        "url": "https://www.fao.org/4/y5686e/y5686e00.htm",
        "notes": "Cơ sở sinh lý TEE = BMR × PAL (FAO PAL: 1.40–1.69, 1.70–1.99, 2.00–2.40); 5 mức 1.2–1.9 là thang quy ước thực hành phổ biến.",
    },
    {
        "key": "target_calories",
        "metric": "Calo mục tiêu & Ngưỡng sàn an toàn",
        "formula": "Giảm cân: TDEE × 0.85; Tăng cơ: TDEE × 1.10; Sàn an toàn: ≥1,200 kcal (nữ) / ≥1,500 kcal (nam)",
        "source_title": "Healthy Weight Loss & Dietary Guidelines (Calorie Floors)",
        "authors_org": "Harvard Health Publishing / NIH NIDDK",
        "year": 2024,
        "identifier": "Clinical Safe Floor 1200/1500 kcal",
        "url": "https://www.health.harvard.edu/staying-healthy/calorie-counting-made-easy",
        "notes": "Không hạ calo dưới ngưỡng sàn khi không có giám sát y tế; tỷ lệ ±10–15% giúp giảm cân/tăng cơ bền vững.",
    },
    {
        "key": "macros",
        "metric": "Phân bổ Macro (Protein, Fat, Carb)",
        "formula": "Protein: 1.6–2.0 g/kg; Fat: 25% kcal mục tiêu; Carb: phần calo còn lại (Atwater 4-9-4 kcal/g)",
        "source_title": "ISSN Position Stand: Diets and Body Composition & National Academies DRI AMDR",
        "authors_org": "Aragon A.A. et al. (ISSN, 2017) & National Academies / IOM",
        "year": 2017,
        "identifier": "DOI 10.1186/s12970-017-0174-y",
        "url": "https://doi.org/10.1186/s12970-017-0174-y",
        "notes": "ISSN khuyến nghị 1.4–2.0+ g/kg protein cho người tập luyện; AMDR khuyến nghị Fat 20–35% và Carb 45–65% tổng năng lượng.",
    },
    {
        "key": "physical_activity",
        "metric": "Khuyến nghị vận động cơ bản",
        "formula": "150–300 phút/tuần cường độ vừa (hoặc 75–150 phút mạnh) + ≥2 ngày/tuần tập sức mạnh",
        "source_title": "WHO Guidelines on Physical Activity and Sedentary Behaviour",
        "authors_org": "World Health Organization (WHO)",
        "year": 2020,
        "identifier": "ISBN 978-92-4-001512-8",
        "url": "https://www.who.int/publications/i/item/9789240015128",
        "notes": "Tài liệu gốc đã có trong kho tri thức FitAI (data/knowledge/raw/who_physical_activity_sedentary_2020_en.pdf).",
    },
)


def get_health_metrics_references() -> list[dict[str, str | int]]:
    """Trả về bản sao danh sách căn cứ khoa học của các chỉ số sức khỏe."""
    return [dict(item) for item in HEALTH_METRICS_REFERENCES]


def calculate_bmi_asia_category(bmi: float) -> str:
    """Phân loại BMI theo ngưỡng WHO Châu Á – Thái Bình Dương (WPRO/IDI 2000)."""
    if bmi < 18.5:
        return "Thiếu cân"
    if bmi < 23.0:
        return "Bình thường"
    if bmi < 25.0:
        return "Thừa cân"
    return "Béo phì"


def calculate_bmi(height_cm: float, weight_kg: float) -> tuple[float, str]:
    """Tính chỉ số BMI và phân loại theo chuẩn WHO Quốc tế.

    BMI = cân nặng (kg) / chiều cao (m)^2
    """
    if height_cm <= 0 or weight_kg <= 0:
        raise ValueError("Chiều cao và cân nặng phải lớn hơn 0")
    height_m = height_cm / 100.0
    bmi = weight_kg / (height_m ** 2)
    bmi_rounded = round(bmi, 1)

    if bmi_rounded < 18.5:
        category = "Thiếu cân"
    elif bmi_rounded < 25.0:
        category = "Bình thường"
    elif bmi_rounded < 30.0:
        category = "Thừa cân"
    else:
        category = "Béo phì"

    return bmi_rounded, category


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """Tính BMR theo công thức Mifflin-St Jeor.

    BMR = 10*kg + 6.25*cm - 5*tuổi + constant
    trong đó constant = +5 (nam), -161 (nữ), -78 (other - quy ước xấp xỉ).
    """
    if weight_kg <= 0 or height_cm <= 0 or age <= 0:
        raise ValueError("Cân nặng, chiều cao và tuổi phải lớn hơn 0")
    gender_key = gender.lower()
    if gender_key not in BMR_GENDER_CONSTANTS:
        raise ValueError(
            f"Giới tính không hợp lệ: '{gender}'. Chỉ chấp nhận: {list(BMR_GENDER_CONSTANTS.keys())}"
        )

    constant = BMR_GENDER_CONSTANTS[gender_key]
    bmr = 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age + constant
    return round(bmr, 2)


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """Tính TDEE = BMR * hệ số vận động."""
    level_key = activity_level.lower()
    if level_key not in ACTIVITY_MULTIPLIERS:
        raise ValueError(
            f"Mức vận động không hợp lệ: '{activity_level}'. "
            f"Chỉ chấp nhận: {list(ACTIVITY_MULTIPLIERS.keys())}"
        )
    multiplier = ACTIVITY_MULTIPLIERS[level_key]
    return round(bmr * multiplier, 2)


def calculate_target_calories(
    tdee: float, fitness_goal: str, gender: str
) -> tuple[int, bool]:
    """Tính calo mục tiêu theo mục tiêu rèn luyện và áp dụng chặn dưới an toàn.

    Returns:
        tuple[int, bool]: (target_calories, calorie_floor_applied)
    """
    goal_key = fitness_goal.lower()
    if goal_key not in GOAL_CALORIE_ADJUSTMENTS:
        raise ValueError(
            f"Mục tiêu không hợp lệ: '{fitness_goal}'. "
            f"Chỉ chấp nhận: {list(GOAL_CALORIE_ADJUSTMENTS.keys())}"
        )
    gender_key = gender.lower()
    if gender_key not in CALORIE_FLOORS:
        raise ValueError(
            f"Giới tính không hợp lệ: '{gender}'. Chỉ chấp nhận: {list(CALORIE_FLOORS.keys())}"
        )

    factor = GOAL_CALORIE_ADJUSTMENTS[goal_key]
    raw_target = tdee * factor
    rounded_target = round(raw_target)

    floor = CALORIE_FLOORS[gender_key]
    if rounded_target < floor:
        return floor, True
    return rounded_target, False


def calculate_macros(
    target_calories: int, weight_kg: float, fitness_goal: str
) -> tuple[int, int, int]:
    """Tính lượng đạm (protein), chất béo (fat) và tinh bột (carb) hàng ngày (gram).

    - protein = weight_kg * (2.0 nếu giảm cân/tăng cơ, 1.6 nếu duy trì/endurance)
    - fat = 25% target_calories / 9 kcal/g
    - carb = calo còn lại / 4 kcal/g

    Returns:
        tuple[int, int, int]: (protein_g, fat_g, carb_g)
    """
    goal_key = fitness_goal.lower()
    if goal_key not in PROTEIN_GRAMS_PER_KG:
        raise ValueError(
            f"Mục tiêu không hợp lệ: '{fitness_goal}'. "
            f"Chỉ chấp nhận: {list(PROTEIN_GRAMS_PER_KG.keys())}"
        )

    protein_ratio = PROTEIN_GRAMS_PER_KG[goal_key]
    protein_g = round(weight_kg * protein_ratio)

    # Chất béo = 25% calo mục tiêu (chia 9 kcal/g)
    fat_calories = target_calories * FAT_CALORIE_PERCENT
    fat_g = round(fat_calories / CALORIES_PER_GRAM_FAT)

    # Carb = phần calo còn lại chia 4 kcal/g
    remaining_calories = (
        target_calories
        - (protein_g * CALORIES_PER_GRAM_PROTEIN)
        - (fat_g * CALORIES_PER_GRAM_FAT)
    )
    carb_g = round(remaining_calories / CALORIES_PER_GRAM_CARB)
    if carb_g < 0:
        carb_g = 0

    return protein_g, fat_g, carb_g


def calculate_user_metrics(
    age: int,
    gender: str,
    height_cm: float,
    weight_kg: float,
    activity_level: str,
    fitness_goal: str,
) -> BodyMetricsResult:
    """Hàm tổng hợp tính toàn bộ chỉ số thể chất và nhu cầu dinh dưỡng."""
    bmi, bmi_category = calculate_bmi(height_cm=height_cm, weight_kg=weight_kg)
    bmr = calculate_bmr(weight_kg=weight_kg, height_cm=height_cm, age=age, gender=gender)
    tdee = calculate_tdee(bmr=bmr, activity_level=activity_level)
    target_calories, floor_applied = calculate_target_calories(
        tdee=tdee, fitness_goal=fitness_goal, gender=gender
    )
    protein_g, fat_g, carb_g = calculate_macros(
        target_calories=target_calories,
        weight_kg=weight_kg,
        fitness_goal=fitness_goal,
    )

    return BodyMetricsResult(
        bmi=bmi,
        bmi_category=bmi_category,
        bmi_asia_category=calculate_bmi_asia_category(bmi),
        bmr=bmr,
        tdee=tdee,
        target_calories=target_calories,
        calorie_floor_applied=floor_applied,
        protein_g=protein_g,
        fat_g=fat_g,
        carb_g=carb_g,
    )


# ── Tóm tắt chỉ số từ hồ sơ (dùng cho API và công cụ calc_body_metrics của agent) ──
REQUIRED_METRICS_FIELDS = [
    "age",
    "gender",
    "height_cm",
    "weight_kg",
    "activity_level",
    "fitness_goal",
]


def profile_metrics_summary(profile) -> dict:
    """Tính chỉ số từ một đối tượng hồ sơ (có các thuộc tính như UserProfile) hoặc None.

    Hồ sơ chưa đủ trường bắt buộc → {"is_complete": False, "missing_fields": [...]}.
    """
    if profile is None:
        return {"is_complete": False, "missing_fields": list(REQUIRED_METRICS_FIELDS)}
    missing = [f for f in REQUIRED_METRICS_FIELDS if getattr(profile, f, None) is None]
    if missing:
        return {"is_complete": False, "missing_fields": missing}
    m = calculate_user_metrics(
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        activity_level=profile.activity_level,
        fitness_goal=profile.fitness_goal,
    )
    return {
        "is_complete": True,
        "missing_fields": [],
        "bmi": m.bmi,
        "bmi_category": m.bmi_category,
        "bmi_asia_category": m.bmi_asia_category,
        "bmr": m.bmr,
        "tdee": m.tdee,
        "target_calories": m.target_calories,
        "calorie_floor_applied": m.calorie_floor_applied,
        "protein_g": m.protein_g,
        "fat_g": m.fat_g,
        "carb_g": m.carb_g,
    }
