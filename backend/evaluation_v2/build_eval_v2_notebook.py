"""Tạo và thực thi notebook FitAI Evaluation v2 (backend/evaluation_v2/fitai_evaluation_v2.ipynb).

Chạy toàn bộ kiểm tra sống trên hệ thống thật:
1. Kiểm tra DB thực phẩm (VN2007 + ADMIN_MANUAL + USDA Full), ChromaDB RAG, Backend Health & Pytest Summary.
2. Đánh giá Intent Classifier v2 (52 câu unseen gồm cả log_workout mới, Guardrail OOS, slot extractor).
3. Kiểm tra tính hợp lý số liệu dinh dưỡng, hồi quy '300g tôm hùm', ngưỡng tự tin OPUS-MT (0.55),
   chỉ số cơ thể (BMI/BMR/TDEE) & tổng hợp tuần WorkoutLog.
4. Kiểm thử End-to-End phản hồi Chatbot (Fast-Path DB + OOS Guard + Live Gemini 2.5 Flash Agent)
   kèm kiểm tra số liệu & trích dẫn nguồn, xuất CSV/JSON và 4 biểu đồ vào charts/.
"""
from __future__ import annotations

from pathlib import Path
import nbformat as nbf


EVAL_V2_DIR = Path(__file__).resolve().parent
NB_PATH = EVAL_V2_DIR / "fitai_evaluation_v2.ipynb"


def build_notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    cells: list = []

    cells.append(nbf.v4.new_markdown_cell(
        "# FitAI System Evaluation v2 — Comprehensive Live Audit & Benchmark\n\n"
        "Notebook này chạy **kiểm thử & đối chiếu trực tiếp** trên hệ thống FitAI hiện tại (Neon Cloud PostgreSQL, ChromaDB RAG, FastAPI, Intent Classifier NumPy, Local OPUS-MT NMT và Google Gemini 2.5 Flash):\n\n"
        "1. **System State, Database Coverage & Full Pytest Audit** (`VN2007`, `ADMIN_MANUAL`, `USDA_SR_LEGACY_2018`, `ChromaDB RAG`, `WorkoutLog`)\n"
        "2. **Intent Classifier v2 Evaluation** (52 câu held-out hoàn toàn mới, gồm cả `log_workout`, `out_of_scope` Guardrail & Food Slot Extractor)\n"
        "3. **Kiểm tra độ hợp lý số liệu trả về (Data & Math Plausibility Audit)** — Hồi quy `300g tôm hùm` (sửa lỗi `Tôm khô`), cân đối Atwater (`4P + 9F + 4C`), ngưỡng tự tin NMT (`FOOD_NMT_MIN_CONFIDENCE = 0.55`), công thức `BMI/BMR/TDEE` và cộng gộp `WorkoutLog` tuần\n"
        "4. **End-to-End Response & Grounding Evaluation (`test respond`)** — Đo độ trễ, tool calling và kiểm tra số liệu trả về giữa Fast-Path DB vs Live Gemini 2.5 Flash Agent"
    ))

    cells.append(nbf.v4.new_code_cell(
        """import asyncio
import csv
import json
import os
import sys
import time
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sqlalchemy import func, select

CWD = Path.cwd().resolve()
BACKEND_DIR = CWD.parent if CWD.name == "evaluation_v2" else (CWD / "backend" if (CWD / "backend").is_dir() else CWD)
REPO_ROOT = BACKEND_DIR.parent
EVAL_V2_DIR = BACKEND_DIR / "evaluation_v2"
CHARTS_DIR = EVAL_V2_DIR / "charts"
RESULTS_DIR = EVAL_V2_DIR / "results"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

os.chdir(BACKEND_DIR)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from core.config import settings
# Trỏ đúng data/ và ChromaDB port (8001 trên host Docker mapping -> 8000 trong container)
if (REPO_ROOT / "data" / "knowledge").is_dir():
    settings.KNOWLEDGE_DIR = str(REPO_ROOT / "data" / "knowledge")
if not os.path.exists("/.dockerenv") and settings.CHROMA_HOST == "localhost" and settings.CHROMA_PORT == 8000:
    settings.CHROMA_PORT = 8001

plt.rcParams.update({
    "figure.dpi": 130,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "font.size": 10,
})
print(f"Backend root : {BACKEND_DIR}")
print(f"Eval v2 out  : {EVAL_V2_DIR}")
print(f"Gemini model : {settings.GEMINI_MODEL} | API key set: {bool(settings.GOOGLE_API_KEY)}")
print(f"NMT threshold: {settings.FOOD_NMT_MIN_CONFIDENCE}")"""
    ))

    cells.append(nbf.v4.new_markdown_cell(
        "## 1. System Runtime Health, Data Inventory & Full Pytest Summary\n"
        "Kiểm tra trạng thái các thành phần đang chạy (Backend API, ChromaDB RAG, Neon PostgreSQL, tổng số bản ghi thực phẩm & buổi tập) cùng kết quả kiểm thử `pytest` toàn bộ hệ thống."
    ))

    cells.append(nbf.v4.new_code_cell(
        """from core.database import AsyncSessionLocal
from models.food import Food
from models.food_source import FoodSource
from models.training_progress import WorkoutLog
from services.knowledge.vector_store import get_client, get_collection

async with AsyncSessionLocal() as db:
    food_rows = (
        await db.execute(
            select(FoodSource.code, func.count(Food.id))
            .join(Food, Food.source_id == FoodSource.id)
            .group_by(FoodSource.code)
        )
    ).all()
    workout_count = (await db.execute(select(func.count(WorkoutLog.id)))).scalar_one()

counts = dict(food_rows)
vn_count = counts.get("VN2007", 0)
admin_count = counts.get("ADMIN_MANUAL", 0)
usda_count = counts.get("USDA_SR_LEGACY_2018", 0)
total_foods = vn_count + admin_count + usda_count

try:
    chroma_count = get_collection(get_client()).count()
except Exception as exc:
    chroma_count = f"Unavailable ({type(exc).__name__})"

try:
    with urllib.request.urlopen("http://localhost:8000/health", timeout=3) as r:
        health_payload = json.loads(r.read().decode("utf-8"))
except Exception as exc:
    health_payload = {"error": str(exc)}

# Đọc tổng kết pytest v2 nếu đã lưu kèm
pytest_summary_path = RESULTS_DIR / "pytest_summary.json"
pytest_stats = json.loads(pytest_summary_path.read_text(encoding="utf-8")) if pytest_summary_path.exists() else {}

print(f"Backend /health : {health_payload}")
print(f"ChromaDB chunks : {chroma_count}")
print(f"Foods in Neon DB: VN2007={vn_count}, ADMIN_MANUAL={admin_count}, USDA={usda_count} -> TOTAL={total_foods}")
print(f"WorkoutLog rows : {workout_count}")
if pytest_stats:
    print("Pytest audit    :", pytest_stats)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.3))

src_labels = ["USDA SR Legacy 2018", "VN Food Composition 2007", "Admin Curated"]
src_vals = [usda_count, vn_count, admin_count]
src_colors = ["#7c5ce6", "#2ebd85", "#f59e0b"]
bars = ax1.barh(src_labels[::-1], src_vals[::-1], color=src_colors[::-1], height=0.55)
for bar, val in zip(bars, src_vals[::-1]):
    pct = val / total_foods * 100 if total_foods else 0
    ax1.text(val + 120, bar.get_y() + bar.get_height() / 2, f"{val:,} ({pct:.1f}%)", va="center", fontweight="bold")
ax1.set_xlim(0, max(src_vals) * 1.25)
ax1.set_xlabel("Records in Neon PostgreSQL")
ax1.set_title(f"FitAI Food Knowledge Base ({total_foods:,} Foods)")

if pytest_stats.get("suites"):
    s_names = [s["name"] for s in pytest_stats["suites"]]
    s_passed = [s["passed"] for s in pytest_stats["suites"]]
    bars2 = ax2.barh(s_names[::-1], s_passed[::-1], color="#10b981", height=0.55)
    for bar, val in zip(bars2, s_passed[::-1]):
        ax2.text(val + 3, bar.get_y() + bar.get_height() / 2, f"{val} passed", va="center", fontweight="bold", fontsize=9)
    ax2.set_xlim(0, max(s_passed) * 1.22)
    ax2.set_xlabel("Passed Test Cases")
    ax2.set_title(f"Pytest Verification Suites ({pytest_stats.get('headline', '')})")
else:
    ax2.text(0.5, 0.5, f"ChromaDB RAG Chunks: {chroma_count}\\nBackend: {health_payload.get('status', 'n/a')}", ha="center", va="center")
    ax2.set_axis_off()

plt.tight_layout()
plt.savefig(CHARTS_DIR / "01_system_data_and_tests_v2.png", bbox_inches="tight")
plt.show()"""
    ))

    cells.append(nbf.v4.new_markdown_cell(
        "## 2. Intent Classifier v2 Evaluation (52 Unseen Queries + Guardrail Safety)\n"
        "Đánh giá bộ phân loại `IntentClassifier` (`TF-IDF unigram+bigram + Softmax Logistic Regression`) trên **52 câu chưa từng thấy trong tập huấn luyện**, gồm thêm nhóm câu hỏi **ghi buổi tập (`log_workout`)**, tra cứu **món Việt–Anh mới (`tôm hùm`, `hạt hướng dương`, `water spinach`)** và kiểm tra an toàn của **Out-of-Scope Guardrail**."
    ))

    cells.append(nbf.v4.new_code_cell(
        """from services.intent_classifier import (
    INTENT_COACHING_GENERAL,
    INTENT_DAILY_PROGRESS,
    INTENT_FOOD_LOOKUP,
    INTENT_LOG_ACTION,
    INTENT_OUT_OF_SCOPE,
    classify_intent,
    extract_food_lookup_slot,
    is_out_of_scope,
)

HELD_OUT_V2 = [
    # food_lookup (12)
    ("tôm hùm 300g bao nhiêu calo?", INTENT_FOOD_LOOKUP),
    ("100g hạt hướng dương bao nhiêu đạm?", INTENT_FOOD_LOOKUP),
    ("trứng vịt lộn 100g có bao nhiêu kcal", INTENT_FOOD_LOOKUP),
    ("thông tin dinh dưỡng cá thu 150g", INTENT_FOOD_LOOKUP),
    ("hạt chia 20g bao nhiêu chất xơ", INTENT_FOOD_LOOKUP),
    ("tra cứu sữa đậu nành", INTENT_FOOD_LOOKUP),
    ("giá trị dinh dưỡng của cua biển", INTENT_FOOD_LOOKUP),
    ("250g ức gà luộc bao nhiêu calo?", INTENT_FOOD_LOOKUP),
    ("nutrition facts for 150g salmon", INTENT_FOOD_LOOKUP),
    ("how many calories in 100g cheddar cheese", INTENT_FOOD_LOOKUP),
    ("macros for 200g broccoli", INTENT_FOOD_LOOKUP),
    ("protein in 180g beef steak", INTENT_FOOD_LOOKUP),
    # log_action: meal + body metric + workout (12)
    ("ghi 200g cá hồi bữa tối", INTENT_LOG_ACTION),
    ("lưu 120g ức gà vào nhật ký", INTENT_LOG_ACTION),
    ("mới ăn 150g bún bò", INTENT_LOG_ACTION),
    ("thêm 50g yến mạch bữa sáng", INTENT_LOG_ACTION),
    ("hôm nay cân nặng 71.2kg", INTENT_LOG_ACTION),
    ("cập nhật cân nặng 64kg vòng eo 75cm", INTENT_LOG_ACTION),
    ("chạy bộ 30 phút mức vừa", INTENT_LOG_ACTION),
    ("mới tập gym 45 phút", INTENT_LOG_ACTION),
    ("vừa đạp xe 40 phút xong", INTENT_LOG_ACTION),
    ("ghi 50 phút bơi lội hôm nay", INTENT_LOG_ACTION),
    ("log 100g oatmeal for breakfast", INTENT_LOG_ACTION),
    ("log 45 min strength workout", INTENT_LOG_ACTION),
    # daily_progress (9)
    ("hôm nay tôi nạp được bao nhiêu calo rồi", INTENT_DAILY_PROGRESS),
    ("xem lượng protein đã ăn hôm nay", INTENT_DAILY_PROGRESS),
    ("bữa giờ trong 7 ngày qua cân nặng tăng hay giảm", INTENT_DAILY_PROGRESS),
    ("trung bình 30 ngày gần nhất ăn bao nhiêu kcal", INTENT_DAILY_PROGRESS),
    ("hôm nay còn được ăn thêm bao nhiêu calo nữa", INTENT_DAILY_PROGRESS),
    ("tuần này mình tập luyện được bao nhiêu phút rồi", INTENT_DAILY_PROGRESS),
    ("kiểm tra tổng kết bữa ăn hôm nay", INTENT_DAILY_PROGRESS),
    ("how much protein did i eat today", INTENT_DAILY_PROGRESS),
    ("what is my calorie average over the last 7 days", INTENT_DAILY_PROGRESS),
    # coaching_general (10)
    ("200g cơm trắng ăn buổi tối có sợ mập không", INTENT_COACHING_GENERAL),
    ("so sánh thịt bò và ức gà món nào nhiều đạm hơn", INTENT_COACHING_GENERAL),
    ("cách tính TDEE cho người tập 4 buổi 1 tuần", INTENT_COACHING_GENERAL),
    ("tư vấn lịch tập cho người mới bắt đầu giảm mỡ", INTENT_COACHING_GENERAL),
    ("hướng dẫn kỹ thuật deadlift đúng form", INTENT_COACHING_GENERAL),
    ("who khuyến cáo người lớn nên tập mấy ngày một tuần", INTENT_COACHING_GENERAL),
    ("tôi muốn tăng cơ nạc thì nên ăn dư bao nhiêu calo", INTENT_COACHING_GENERAL),
    ("chào fitai mình mới dùng app", INTENT_COACHING_GENERAL),
    ("should i eat banana before cardio", INTENT_COACHING_GENERAL),
    ("compare whey protein vs chicken breast", INTENT_COACHING_GENERAL),
    # out_of_scope (9)
    ("dự báo thời tiết hà nội cuối tuần này", INTENT_OUT_OF_SCOPE),
    ("giá vàng sjc hôm nay tăng hay giảm", INTENT_OUT_OF_SCOPE),
    ("viết đoạn code javascript gọi api fetch", INTENT_OUT_OF_SCOPE),
    ("chỉ mình cách nấu món thịt kho tàu ngon", INTENT_OUT_OF_SCOPE),
    ("làm một bài thơ lục bát về biển", INTENT_OUT_OF_SCOPE),
    ("tối nay đội tuyển việt nam đá lúc mấy giờ", INTENT_OUT_OF_SCOPE),
    ("how to install docker on ubuntu", INTENT_OUT_OF_SCOPE),
    ("tell me a funny programming joke", INTENT_OUT_OF_SCOPE),
    ("what is the stock price of apple today", INTENT_OUT_OF_SCOPE),
]

LABELS = [INTENT_FOOD_LOOKUP, INTENT_LOG_ACTION, INTENT_DAILY_PROGRESS, INTENT_COACHING_GENERAL, INTENT_OUT_OF_SCOPE]
SHORT = ["food_lookup", "log_action", "daily_progress", "coaching", "out_of_scope"]
idx_map = {lbl: i for i, lbl in enumerate(LABELS)}
cm = np.zeros((len(LABELS), len(LABELS)), dtype=int)

intent_rows = []
for text, gold in HELD_OUT_V2:
    pred = classify_intent(text)
    cm[idx_map[gold], idx_map[pred.intent]] += 1
    slot = extract_food_lookup_slot(text)
    intent_rows.append({
        "query": text,
        "gold_intent": gold,
        "pred_intent": pred.intent,
        "confidence": round(pred.confidence, 4),
        "correct": pred.intent == gold,
        "slot_query": slot.query if slot else None,
        "slot_grams": slot.grams if slot else None,
        "oos_blocked": is_out_of_scope(text),
    })

df_intent = pd.DataFrame(intent_rows)
df_intent.to_csv(RESULTS_DIR / "eval_v2_intent_results.csv", index=False, encoding="utf-8-sig")

acc = df_intent["correct"].mean()
precisions, recalls, f1s = [], [], []
for i in range(len(LABELS)):
    tp = cm[i, i]
    fp = cm[:, i].sum() - tp
    fn = cm[i, :].sum() - tp
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * p * r / (p + r)) if (p + r) else 0.0
    precisions.append(p); recalls.append(r); f1s.append(f1)

macro_f1 = float(np.mean(f1s))
oos_df = df_intent[df_intent["gold_intent"] == INTENT_OUT_OF_SCOPE]
in_df = df_intent[df_intent["gold_intent"] != INTENT_OUT_OF_SCOPE]
oos_tpr = oos_df["oos_blocked"].mean()
in_fpr = in_df["oos_blocked"].mean()
slot_ok = df_intent[df_intent["gold_intent"] == INTENT_FOOD_LOOKUP]["slot_query"].notna().mean()

print(f"Unseen Held-Out Accuracy ({len(HELD_OUT_V2)} queries): {acc*100:.1f}% ({df_intent['correct'].sum()}/{len(HELD_OUT_V2)})")
print(f"Macro-F1: {macro_f1*100:.1f}% | Food Slot Extraction: {slot_ok*100:.1f}%")
print(f"Guardrail OOS Block Rate (TPR): {oos_tpr*100:.1f}% | In-Domain False Block Rate (FPR): {in_fpr*100:.1f}%")
misses = df_intent[~df_intent["correct"]]
if not misses.empty:
    print("\\nMisclassified cases:")
    for _, row in misses.iterrows():
        print(f"  - {row['query']!r}: gold={row['gold_intent']} -> pred={row['pred_intent']} ({row['confidence']:.3f})")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.8))
cm_norm = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)
im = ax1.imshow(cm_norm, cmap="Purples", vmin=0, vmax=1)
ax1.set_xticks(range(len(SHORT)), SHORT, rotation=25, ha="right")
ax1.set_yticks(range(len(SHORT)), SHORT)
ax1.set_xlabel("Predicted Intent")
ax1.set_ylabel("True Intent")
ax1.set_title(f"Confusion Matrix v2 (Accuracy = {acc*100:.1f}%)")
for r in range(len(LABELS)):
    for c in range(len(LABELS)):
        cnt = cm[r, c]
        txt_color = "white" if cm_norm[r, c] > 0.55 else "#1f2937"
        ax1.text(c, r, f"{cnt}\\n({cm_norm[r, c]*100:.0f}%)", ha="center", va="center", color=txt_color, fontsize=8.5, fontweight="bold")

x = np.arange(len(SHORT))
w = 0.25
ax2.bar(x - w, [v * 100 for v in precisions], w, label="Precision", color="#3b82f6")
ax2.bar(x, [v * 100 for v in recalls], w, label="Recall", color="#10b981")
ax2.bar(x + w, [v * 100 for v in f1s], w, label="F1-Score", color="#7c5ce6")
ax2.set_xticks(x, SHORT, rotation=20, ha="right")
ax2.set_ylim(0, 114)
ax2.set_ylabel("Score (%)")
ax2.set_title(f"Per-Class Metrics (Macro-F1 = {macro_f1*100:.1f}% | In-Domain FPR = {in_fpr*100:.1f}%)")
ax2.legend(loc="lower right", frameon=True, fontsize=8.5)
for xi, f1_v in zip(x, f1s):
    ax2.text(xi + w, f1_v * 100 + 1.8, f"{f1_v*100:.0f}%", ha="center", fontsize=8, fontweight="bold")

plt.tight_layout()
plt.savefig(CHARTS_DIR / "02_intent_confusion_and_f1_v2.png", bbox_inches="tight")
plt.show()"""
    ))

    cells.append(nbf.v4.new_markdown_cell(
        "## 3. Data & Numerical Plausibility Audit (`Kiểm tra số liệu trả về có phù hợp không`)\n"
        "Kiểm tra 4 lớp số liệu thực tế của FitAI:\n"
        "1. **Food Lookup & Auto-Pick (`resolve_best_food` + `scale`)** trên 14 món Việt/Anh phổ biến & ca khó (bao gồm hồi quy `300g tôm hùm`, `tôm khô`, `hạt hướng dương`, `water spinach`, `việt quất`), kiểm tra chuẩn Atwater (`|kcal - (4P + 9F + 4C)|`), chặn lỗi chọn nhầm đồ khô (`DRIED`) và kiểm tra ràng buộc vật lý (`P + F + C <= grams`).\n"
        "2. **Ngưỡng tự tin OPUS-MT (`FOOD_NMT_MIN_CONFIDENCE = 0.55`)**: kiểm tra bản dịch sạch đi qua vs nhiễu bị chặn.\n"
        "3. **Body Metrics (`BMI / BMR / TDEE / Macros`)**: xác minh toán học trên các hồ sơ mẫu.\n"
        "4. **WorkoutLog Weekly Summary (`build_week_summary`)**: kiểm tra gộp buổi tập tự do + giáo án không bịa kcal tiêu hao."
    ))

    cells.append(nbf.v4.new_code_cell(
        """from types import SimpleNamespace
from models.profile import ActivityLevel, FitnessGoal
from services.foods.lookup import resolve_best_food, scale, search_foods
from services.foods.preparation import FoodPreparation
from services.foods.translator import _cached_translate, translate_food_query
from services.metrics_service import profile_metrics_summary
from services.training.progress import build_week_summary

FOOD_AUDIT_CASES = [
    ("tôm hùm", 300.0, False, "Should pick cooked lobster (~267 kcal, 57g P), NOT Tôm khô (226.8g P)"),
    ("tôm hùm hấp", 300.0, False, "Cooked lobster"),
    ("tôm khô", 100.0, True, "Explicit dried request -> Tôm khô allowed"),
    ("ức gà", 150.0, False, "Should prefer grilled/cooked chicken breast"),
    ("cơm trắng", 200.0, False, "USDA cooked white rice"),
    ("phở bò", 500.0, False, "VN dish / Admin bowl"),
    ("hạt hướng dương", 100.0, False, "Translated via OPUS-MT vi-en (sunflower)"),
    ("việt quất", 150.0, False, "Should pick Blueberries, raw (not dried/sweetened)"),
    ("cải xoăn", 100.0, False, "Should pick Kale cooked/raw"),
    ("sò điệp", 150.0, False, "Should pick cooked scallop via VI_EN_PHRASES (block OPUS-MT noise)"),
    ("bạch tuộc", 150.0, False, "Should pick cooked octopus"),
    ("water spinach", 200.0, False, "EN->VI should match Rau muống"),
    ("sweet potato", 200.0, False, "EN->VI should match Khoai lang"),
    ("cá hồi", 150.0, False, "Should prefer cooked Atlantic salmon"),
]

food_audit_rows = []
async with AsyncSessionLocal() as db:
    # Tra riêng Tôm khô để so sánh Before vs After
    dried_shrimp = (await db.execute(select(Food).where(Food.code == 8053))).scalar_one()
    for q, grams, allow_dried, note in FOOD_AUDIT_CASES:
        food, resolve_note = await resolve_best_food(db, q)
        if food is None:
            food_audit_rows.append({"query": q, "grams": grams, "matched": False, "plausible": False, "issue": "No match"})
            continue
        kcal = scale(food.energy_kcal, grams)
        p = scale(food.protein_g, grams)
        f = scale(food.fat_g, grams)
        c = scale(food.carb_g, grams)
        prep = food.preparation.value if hasattr(food.preparation, "value") else str(food.preparation)
        atwater = None if None in (p, f, c) else round(4.0 * p + 9.0 * f + 4.0 * c, 1)
        atwater_diff = None if (atwater is None or kcal is None) else round(abs(kcal - atwater), 1)
        macro_sum_ok = True if None in (p, f, c) else ((p + f + c) <= grams + 1.0)
        dried_ok = True if allow_dried else (prep != FoodPreparation.DRIED.value)
        kcal_ok = (kcal is None) or (0 <= kcal <= grams * 9.2)
        plausible = macro_sum_ok and dried_ok and kcal_ok and (atwater_diff is None or atwater_diff <= max(25.0, kcal * 0.25))
        food_audit_rows.append({
            "query": q,
            "grams": grams,
            "picked_food": food.name_vi,
            "prep": prep,
            "kcal": kcal,
            "protein_g": p,
            "fat_g": f,
            "carb_g": c,
            "atwater_kcal": atwater,
            "atwater_diff": atwater_diff,
            "dried_ok": dried_ok,
            "macro_sum_ok": macro_sum_ok,
            "plausible": plausible,
        })

df_food = pd.DataFrame(food_audit_rows)
df_food.to_csv(RESULTS_DIR / "eval_v2_food_checks.csv", index=False, encoding="utf-8-sig")
print(df_food[["query", "grams", "picked_food", "prep", "kcal", "protein_g", "fat_g", "carb_g", "plausible"]].to_string(index=False))
print(f"\\nFood Numerical Plausibility Pass Rate: {df_food['plausible'].sum()}/{len(df_food)} ({df_food['plausible'].mean()*100:.1f}%)")

# OPUS-MT Confidence Audit
NMT_AUDIT = [
    ("vi-en", "hạt hướng dương"), ("vi-en", "trà xanh"), ("vi-en", "cải xoăn"),
    ("vi-en", "dầu ô liu"), ("vi-en", "nấm rơm"), ("vi-en", "bơ quả"), ("vi-en", "cà rốt"),
    ("en-vi", "grilled salmon"), ("en-vi", "white rice"), ("en-vi", "dragon fruit"),
]
nmt_rows = []
for direction, q in NMT_AUDIT:
    raw_txt, conf = _cached_translate(direction, f"{direction}:{q}", q)
    kept = bool(await translate_food_query(q))
    nmt_rows.append({"query": q, "direction": direction, "raw_nmt": raw_txt, "confidence": conf, "passed_gate": kept})
df_nmt = pd.DataFrame(nmt_rows)
print("\\nOPUS-MT Confidence Gate Audit (threshold = 0.55):")
print(df_nmt.to_string(index=False))

# Body Metrics & WorkoutLog Audit
sample_profile = SimpleNamespace(
    age=26, gender="male", height_cm=175.0, weight_kg=72.0,
    activity_level=ActivityLevel.MODERATE.value, fitness_goal=FitnessGoal.WEIGHT_LOSS.value,
)
bm = profile_metrics_summary(sample_profile)
macro_kcal = 4 * bm["protein_g"] + 9 * bm["fat_g"] + 4 * bm["carb_g"]
wk = build_week_summary(date(2026, 11, 16), [(date(2026, 11, 16), 20)], [(date(2026, 11, 16), 30), (date(2026, 11, 18), 45)])
print(f"\\nBody Metrics Audit -> BMI={bm['bmi']}, BMR={bm['bmr']}, TDEE={bm['tdee']}, Target={bm['target_calories']} kcal (Macro sum={macro_kcal:.0f} kcal)")
print(f"WorkoutLog Weekly Audit -> active_dates={wk['active_dates']}, completed_days={wk['completed_days']}, workout_sessions={wk['workout_sessions']}, total_minutes={wk['total_minutes']}")

# Chart 3
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.5))
old_kcal, old_p = scale(dried_shrimp.energy_kcal, 300), scale(dried_shrimp.protein_g, 300)
new_row = df_food[df_food["query"] == "tôm hùm"].iloc[0]
metrics_lbl = ["Energy (kcal / 10)", "Protein (g)", "Fat (g)", "Carb (g)"]
old_vals = [old_kcal / 10.0, old_p, scale(dried_shrimp.fat_g, 300), scale(dried_shrimp.carb_g, 300)]
new_vals = [new_row["kcal"] / 10.0, new_row["protein_g"], new_row["fat_g"], new_row["carb_g"]]
x = np.arange(len(metrics_lbl))
w = 0.35
ax1.bar(x - w/2, old_vals, w, label="Before: Tôm khô (Bug)", color="#ef4444")
ax1.bar(x + w/2, new_vals, w, label="After: Cooked Lobster (USDA 174209)", color="#10b981")
for xi, ov, nv in zip(x, old_vals, new_vals):
    ax1.text(xi - w/2, ov + 3, f"{ov:.1f}", ha="center", fontsize=8.5, color="#b91c1c", fontweight="bold")
    ax1.text(xi + w/2, nv + 3, f"{nv:.1f}", ha="center", fontsize=8.5, color="#047857", fontweight="bold")
ax1.set_xticks(x, metrics_lbl)
ax1.set_ylim(0, max(old_vals) * 1.18)
ax1.set_title("Regression Fix: 300g 'tôm hùm' Nutrition Accuracy")
ax1.legend(frameon=False, fontsize=8.5)

colors_nmt = ["#10b981" if ok else "#ef4444" for ok in df_nmt["passed_gate"]]
y_pos = np.arange(len(df_nmt))
ax2.barh(y_pos, df_nmt["confidence"], color=colors_nmt, height=0.6)
ax2.axvline(settings.FOOD_NMT_MIN_CONFIDENCE, color="#111827", linestyle="--", linewidth=1.5, label=f"Threshold = {settings.FOOD_NMT_MIN_CONFIDENCE}")
ax2.set_yticks(y_pos, [f"{r['query']} → {r['raw_nmt'][:16]}" for _, r in df_nmt.iterrows()], fontsize=8.5)
ax2.invert_yaxis()
ax2.set_xlim(0, 1.05)
ax2.set_xlabel("OPUS-MT Token Confidence")
ax2.set_title("NMT Confidence Gate (Green=Kept, Red=Blocked Noise)")
ax2.legend(loc="lower right", frameon=False, fontsize=8.5)

plt.tight_layout()
plt.savefig(CHARTS_DIR / "03_nutrition_accuracy_and_nmt_v2.png", bbox_inches="tight")
plt.show()"""
    ))

    cells.append(nbf.v4.new_markdown_cell(
        "## 4. End-to-End Chatbot Response & Grounding Evaluation (`test respond`)\n"
        "Chạy kiểm thử phản hồi thực tế qua cả **Fast-Path (`try_fast_route`)** lẫn **Full Live Gemini 2.5 Flash Agent (`InProcessChat` trên FastAPI + Neon DB + ChromaDB RAG)**, đo độ trễ, vết gọi công cụ (`tool_calls`), tính khớp số liệu từ DB/API và nguồn trích dẫn."
    ))

    cells.append(nbf.v4.new_code_cell(
        """import uuid
from evaluation.accounts import ensure_accounts
from evaluation.checks import FOOD_TOLERANCE, METRIC_TOLERANCE, contains_value
from evaluation.inprocess import InProcessChat, app_client, instrument_agent
from evaluation.questions import ACCOUNT_SAMPLE, Question
from services.intent_classifier import try_fast_route

E2E_CASES = [
    # (id, group, mode, account, prompt, check_cfg)
    ("FP01", "Fast-Path DB", "fast_route", ACCOUNT_SAMPLE, "150g ức gà bao nhiêu calo?", {"expect_sub": "150 g", "expect_num": 180.0}),
    ("FP02", "Fast-Path DB", "fast_route", ACCOUNT_SAMPLE, "tôm hùm 300g bao nhiêu calo?", {"expect_sub": "lobster", "expect_num": 267.0}),
    ("FP03", "Fast-Path DB", "fast_route", ACCOUNT_SAMPLE, "hạt hướng dương 100g bao nhiêu calo?", {"expect_sub": "sunflower", "expect_num": 584.0}),
    ("FP04", "Ambiguity Safety", "fast_route", ACCOUNT_SAMPLE, "100g bơ bao nhiêu calo?", {"expect_sub": "nhiều loại"}),
    ("FP05", "Raw-Only Safety", "fast_route", ACCOUNT_SAMPLE, "150g xôi bao nhiêu calo?", {"expect_sub": "SỐNG"}),
    ("OOS01", "Out-of-Scope Guard", "fast_route", ACCOUNT_SAMPLE, "Giá vé World Cup bao nhiêu?", {"expect_sub": "ngoài phạm vi"}),
    ("OOS02", "Out-of-Scope Guard", "fast_route", ACCOUNT_SAMPLE, "Viết code Python sắp xếp mảng giúp tôi", {"expect_sub": "ngoài phạm vi"}),
    ("RAG01", "Live RAG (WHO)", "live_agent", ACCOUNT_SAMPLE, "Một tuần người lớn nên vận động bao nhiêu phút?", {"req_tool": "search_knowledge", "expect_num": 150.0, "req_source": True}),
    ("RAG02", "Live RAG (ISSN)", "live_agent", ACCOUNT_SAMPLE, "Ăn kiêng keto có đốt mỡ nhanh hơn low-fat khi cùng calo và protein không?", {"req_tool": "search_knowledge", "req_source": True}),
    ("BM01", "Live Body Metrics", "live_agent", ACCOUNT_SAMPLE, "Tính chỉ số BMI, BMR và TDEE của tôi giúp nhé", {"req_tool": "calc_body_metrics", "check_bm": True}),
    ("DM01", "Live Daily Summary", "live_agent", ACCOUNT_SAMPLE, "Hôm nay tôi đã ăn tổng cộng bao nhiêu calo rồi?", {"req_tool": "get_daily_summary", "check_summary": True}),
    ("FD01", "Live Food Compare", "live_agent", ACCOUNT_SAMPLE, "So sánh lượng đạm giữa 150g ức gà và 150g cá hồi", {"req_tool": "lookup_food", "req_source": True}),
    ("WL01", "Live Log Workout", "live_agent", ACCOUNT_SAMPLE, "Hôm nay tôi vừa chạy bộ 30 phút mức vừa, ghi vào nhật ký giúp tôi", {"req_tool": "log_workout", "expect_num": 30.0}),
    ("DP01", "Live Training Summary", "live_agent", ACCOUNT_SAMPLE, "Tuần này tôi đã tập luyện được bao nhiêu phút rồi?", {"req_tool": "get_training_summary", "expect_num": 30.0}),
]

e2e_rows = []
async with app_client() as client:
    accounts = await ensure_accounts(client)
    h_full = accounts.headers(ACCOUNT_SAMPLE)
    ref_metrics = (await client.get("/api/v1/profile/metrics", headers=h_full)).json()
    ref_summary = (await client.get("/api/v1/meals/summary", headers=h_full)).json()
    chat_fn = InProcessChat(client, accounts)

    with instrument_agent():
        first_live = True
        for cid, grp, mode, acct, prompt, cfg in E2E_CASES:
            if mode == "fast_route":
                t0 = time.perf_counter()
                async with AsyncSessionLocal() as db:
                    fast_res = await try_fast_route(db, prompt)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                reply = fast_res[0] if fast_res else ""
                sources = fast_res[1] if fast_res else []
                tools_called = []
                http_status = 200 if fast_res is not None else 500
            else:
                # Free Tier Gemini 2.5 Flash giới hạn 5 req/phút (mỗi câu hỏi agent gọi ~2 req)
                if not first_live:
                    await asyncio.sleep(28.0)
                first_live = False
                q_obj = Question(id=cid, nhom=grp, cau_hoi=prompt, chuan_bi="")
                for attempt in range(3):
                    t0 = time.perf_counter()
                    outcome = await chat_fn(q_obj)
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    if outcome.http_status == 429 or outcome.error_type == "ResourceExhausted":
                        if attempt < 2:
                            await asyncio.sleep(60.0)
                            continue
                    break
                reply = outcome.reply
                sources = outcome.sources
                tools_called = [c["name"] for c in outcome.calls]
                http_status = outcome.http_status

            passed = (http_status == 200 and bool(reply.strip()))
            notes = []
            if cfg.get("expect_sub") and cfg["expect_sub"].lower() not in reply.lower():
                passed = False
                notes.append(f"missing '{cfg['expect_sub']}'")
            if cfg.get("expect_num") is not None and not contains_value(reply, cfg["expect_num"], tol=1.0):
                passed = False
                notes.append(f"missing num {cfg['expect_num']}")
            if cfg.get("req_tool") and cfg["req_tool"] not in tools_called:
                passed = False
                notes.append(f"missing tool {cfg['req_tool']} (got {tools_called})")
            if cfg.get("req_source") and not sources:
                passed = False
                notes.append("missing sources")
            if cfg.get("check_bm"):
                bmi_ok = contains_value(reply, ref_metrics["bmi"], tol=METRIC_TOLERANCE)
                tdee_ok = contains_value(reply, ref_metrics["tdee"], tol=METRIC_TOLERANCE)
                if not (bmi_ok and tdee_ok):
                    passed = False
                    notes.append(f"metrics mismatch (expected BMI={ref_metrics['bmi']}, TDEE={ref_metrics['tdee']})")
            if cfg.get("check_summary"):
                eaten_kcal = (ref_summary.get("eaten") or {}).get("energy_kcal")
                if eaten_kcal is not None and not contains_value(reply, eaten_kcal, tol=1.0):
                    passed = False
                    notes.append(f"daily kcal mismatch (expected {eaten_kcal})")

            e2e_rows.append({
                "id": cid,
                "group": grp,
                "mode": mode,
                "http_status": http_status,
                "latency_ms": round(elapsed_ms, 1),
                "tools": ", ".join(tools_called) if tools_called else "(fast-path / 0 LLM)",
                "sources_count": len(sources),
                "passed": passed,
                "notes": "; ".join(notes) if notes else "OK",
                "reply_preview": reply.replace("\\n", " ")[:160],
            })

df_e2e = pd.DataFrame(e2e_rows)
df_e2e.to_csv(RESULTS_DIR / "eval_v2_responses.csv", index=False, encoding="utf-8-sig")

summary_payload = {
    "foods_total": int(total_foods),
    "foods_by_source": {"VN2007": vn_count, "ADMIN_MANUAL": admin_count, "USDA_SR_LEGACY_2018": usda_count},
    "chroma_chunks": chroma_count,
    "intent_v2_accuracy": round(float(acc), 4),
    "intent_v2_macro_f1": round(float(macro_f1), 4),
    "intent_v2_oos_tpr": round(float(oos_tpr), 4),
    "intent_v2_in_domain_fpr": round(float(in_fpr), 4),
    "food_plausibility_pass": f"{int(df_food['plausible'].sum())}/{len(df_food)}",
    "e2e_pass": f"{int(df_e2e['passed'].sum())}/{len(df_e2e)}",
    "fast_path_p50_ms": round(float(df_e2e[df_e2e["mode"] == "fast_route"]["latency_ms"].median()), 1),
    "live_agent_p50_ms": round(float(df_e2e[df_e2e["mode"] == "live_agent"]["latency_ms"].median()), 1),
}
(RESULTS_DIR / "eval_v2_summary.json").write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")

print(df_e2e[["id", "group", "mode", "latency_ms", "tools", "sources_count", "passed", "notes"]].to_string(index=False))
print(f"\\nE2E Response Pass Rate: {df_e2e['passed'].sum()}/{len(df_e2e)} ({df_e2e['passed'].mean()*100:.1f}%)")
print(f"Median Latency -> Fast-Path/Guard: {summary_payload['fast_path_p50_ms']} ms | Live Gemini Agent: {summary_payload['live_agent_p50_ms']} ms")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.5))
grp_pass = df_e2e.groupby("group")["passed"].agg(["sum", "count"])
labels_g = grp_pass.index.tolist()
rates = (grp_pass["sum"] / grp_pass["count"] * 100).tolist()
colors_g = ["#10b981" if r == 100 else "#f59e0b" for r in rates]
bars = ax1.barh(labels_g[::-1], rates[::-1], color=colors_g[::-1], height=0.55)
for bar, (s, c) in zip(bars, list(zip(grp_pass["sum"], grp_pass["count"]))[::-1]):
    ax1.text(min(bar.get_width() + 2, 102), bar.get_y() + bar.get_height()/2, f"{s}/{c}", va="center", fontweight="bold")
ax1.set_xlim(0, 118)
ax1.set_xlabel("Pass Rate (%)")
ax1.set_title(f"End-to-End Evaluation Results ({df_e2e['passed'].sum()}/{len(df_e2e)} Passed)")

mode_means = df_e2e.groupby("mode")["latency_ms"].median()
ax2.bar(["Fast-Path DB & OOS Guard\\n(0 LLM tokens)", "Live Gemini 2.5 Flash Agent\\n(Tool Calling + RAG)"],
        [mode_means.get("fast_route", 1), mode_means.get("live_agent", 1)],
        color=["#2ebd85", "#7c5ce6"], width=0.45)
ax2.set_yscale("log")
ax2.set_ylabel("Median Latency (ms, log scale)")
speedup = mode_means.get("live_agent", 1) / max(mode_means.get("fast_route", 1), 0.1)
ax2.set_title(f"End-to-End Latency Comparison ({speedup:,.0f}x Faster on Fast-Path)")
for idx, val in enumerate([mode_means.get("fast_route", 0), mode_means.get("live_agent", 0)]):
    ax2.text(idx, val * 1.25, f"{val:,.1f} ms", ha="center", fontweight="bold")

plt.tight_layout()
plt.savefig(CHARTS_DIR / "04_e2e_responses_and_latency_v2.png", bbox_inches="tight")
plt.show()"""
    ))

    nb["cells"] = cells
    nb["metadata"]["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    return nb


if __name__ == "__main__":
    EVAL_V2_DIR.mkdir(parents=True, exist_ok=True)
    nb = build_notebook()
    with open(NB_PATH, "w", encoding="utf-8") as fh:
        nbf.write(nb, fh)
    print(f"Wrote notebook template: {NB_PATH}")
