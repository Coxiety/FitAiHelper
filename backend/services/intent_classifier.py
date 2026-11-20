"""Bộ phân loại ý định (Intent Classifier) song ngữ Việt–Anh & Fast-Path tra cứu thực phẩm.

Mục tiêu:
- Sử dụng encoder ngữ nghĩa đa ngữ đóng băng (`BAAI/bge-m3`, CLS pooling + chuẩn hoá L2)
  kết hợp lớp đầu ra Softmax Multinomial Logistic Regression (NumPy) để hiểu đồng nghĩa và
  câu hỏi song ngữ Việt ↔ Anh mà không cần thêm nhiều câu mẫu thủ công hay fine-tune GPU.
- Tự động fallback sang TF-IDF + Softmax Logistic Regression khi tắt embedding hoặc môi trường
  thiếu model/RAM, giúp test nhẹ và hệ thống luôn sẵn sàng.
- Khi câu hỏi là tra cứu dinh dưỡng MỘT thực phẩm cụ thể với độ tin cậy cao, tách `(food_query, grams)`
  và tra thẳng PostgreSQL — KHÔNG gọi LLM; các câu ghép, so sánh, tư vấn, ghi nhật ký rơi về
  `FitnessAdvisorAgent` (Gemini + tool calling).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Iterable

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings

from services.ai_agents.fitness_advisor import (
    preparation_label,
    serving_line,
    source_name,
)
from services.foods.lookup import (
    AmbiguousFoodQuery,
    FoodLookupError,
    FoodMatch,
    FoodQueryError,
    RawOnlyFoodQuery,
    nutrient_line,
    search_foods,
    validate_grams,
)
from services.foods.normalize import normalize_search
from services.foods.sources import (
    ADMIN_MANUAL,
    USDA_SR,
    VN2007,
    citation,
    short_note,
    source_code,
)

logger = logging.getLogger(__name__)

INTENT_FOOD_LOOKUP = "food_lookup"
INTENT_LOG_ACTION = "log_action"
INTENT_DAILY_PROGRESS = "daily_progress"
INTENT_COACHING_GENERAL = "coaching_general"
INTENT_OUT_OF_SCOPE = "out_of_scope"

FAST_PATH_CONFIDENCE_THRESHOLD = 0.65
OUT_OF_SCOPE_CONFIDENCE_THRESHOLD = 0.48
EMBEDDING_OUT_OF_SCOPE_CONFIDENCE_THRESHOLD = 0.55

_EMBEDDING_MAX_LENGTH = 128
_EMBEDDING_HEAD_LR = 2.0
_EMBEDDING_HEAD_REG = 5e-4
_EMBEDDING_HEAD_STEPS = 500
_PRED_CACHE_MAX = 256

OUT_OF_SCOPE_REPLY = (
    "Mình là **FitAI** — trợ lý chuyên về **thể dục, thể hình, dinh dưỡng và nhật ký ăn uống**. "
    "Câu hỏi này nằm ngoài phạm vi hỗ trợ của mình nên mình xin phép không trả lời nhé. "
    "Bạn có thể hỏi mình về calo thực phẩm, thực đơn, chỉ số BMI/TDEE hoặc lịch tập luyện!"
)

# Từ khoá trong phạm vi FitAI: chỉ cần có mặt thì KHÔNG BAO GIỜ chặn nhầm là ngoài phạm vi
_IN_DOMAIN_GUARD_RE = re.compile(
    r"\b(?:"
    r"calo|kcal|calories|calorie|protein|dam|carb|carbs|glucid|lipid|fat|xo|fiber|macro|macros|"
    r"dinh duong|thuc pham|mon an|bua an|thuc don|nhat ky|an uong|"
    r"can nang|chieu cao|vong eo|bmi|bmr|tdee|body fat|"
    r"giam can|tang can|tang co|giam mo|giu dang|diet|nutrition|weight|fitness|gym|"
    r"tap luyen|chuong trinh|bai tap|the duc|the hinh|van dong|cardio|squat|deadlift|pushup|"
    r"chay bo|dap xe|boi loi|yoga|gym|workout|training|exercise|health|suc khoe|who|issn|nasm|usda|"
    r"xin chao|chao fitai|fitai|chon muc"
    r")\b"
)

# Dấu hiệu rõ ràng ngoài phạm vi (chỉ kích hoạt khi KHÔNG có từ khoá trong phạm vi ở trên)
_EXPLICIT_OFF_TOPIC_RE = re.compile(
    r"\b(?:"
    r"thoi tiet|du bao thoi tiet|gia ve|world cup|bong da|xo so|chung khoan|gia vang|bitcoin|crypto|"
    r"viet tho|bai tho|lam tho|ke chuyen|chuyen cuoi|loi bai hat|phim hay|choi game|du lich|"
    r"lap trinh|python|javascript|typescript|react|sql|html|css|code giup|sua loi|debug|"
    r"giai phuong trinh|toan hoc|lich su viet nam|dia ly|dich tieng|tieng anh giao tiep|"
    r"cach nau|cong thuc nau|nau an ngon|"
    r"weather|forecast|world cup|ticket price|write a poem|poem|poetry|joke|stock price|lottery|"
    r"programming|recipe|how to cook|movie|song lyrics"
    r")\b"
)

# Từ khoá xác nhận đúng là câu hỏi tra cứu dinh dưỡng/calo thực phẩm (tránh chặn câu hỏi nối tiếp dạng "200g món X?")
_FOOD_LOOKUP_CUE_RE = re.compile(
    r"\b(?:"
    r"calo|kcal|calories|calorie|protein|dam|carb|carbs|glucid|lipid|fat|xo|fiber|macro|macros|"
    r"chat dam|chat beo|chat xo|tinh bot|nang luong|dinh duong|gia tri dinh duong|"
    r"thong tin dinh duong|thanh phan dinh duong|tra cuu|tim thuc pham|nutrition|food details|bn"
    r")\b"
)

# Tập huấn luyện song ngữ Việt / Anh cho bộ phân loại ý định FitAI
TRAINING_SAMPLES: tuple[tuple[str, str], ...] = (
    # ── food_lookup ──
    ("100g ức gà bao nhiêu calo", INTENT_FOOD_LOOKUP),
    ("150g cơm trắng có bao nhiêu kcal", INTENT_FOOD_LOOKUP),
    ("calo của phở bò", INTENT_FOOD_LOOKUP),
    ("trứng gà luộc bao nhiêu đạm và chất béo", INTENT_FOOD_LOOKUP),
    ("thông tin dinh dưỡng thịt bò thăn", INTENT_FOOD_LOOKUP),
    ("tra cứu cá hồi 200g", INTENT_FOOD_LOOKUP),
    ("yến mạch có bao nhiêu carb và chất xơ", INTENT_FOOD_LOOKUP),
    ("200g khoai lang bao nhiêu calo", INTENT_FOOD_LOOKUP),
    ("bánh mì thịt bao nhiêu kcal", INTENT_FOOD_LOOKUP),
    ("hạnh nhân 30g bao nhiêu protein", INTENT_FOOD_LOOKUP),
    ("sữa chua không đường có bao nhiêu calo", INTENT_FOOD_LOOKUP),
    ("giá trị dinh dưỡng bơ", INTENT_FOOD_LOOKUP),
    ("dinh dưỡng 100g bông cải xanh", INTENT_FOOD_LOOKUP),
    ("50g đậu phộng bn calo", INTENT_FOOD_LOOKUP),
    ("tìm thực phẩm thịt heo nạc", INTENT_FOOD_LOOKUP),
    ("how many calories in 100g chicken breast", INTENT_FOOD_LOOKUP),
    ("nutrition of 150g avocado", INTENT_FOOD_LOOKUP),
    ("macros for greek yogurt", INTENT_FOOD_LOOKUP),
    ("calories in salmon 200g", INTENT_FOOD_LOOKUP),
    ("food details for oatmeal", INTENT_FOOD_LOOKUP),
    ("check macros banana 120g", INTENT_FOOD_LOOKUP),
    ("what is the nutrition in 100g brown rice", INTENT_FOOD_LOOKUP),
    # ── log_action ──
    ("ghi 150g ức gà bữa trưa", INTENT_LOG_ACTION),
    ("lưu 200g cơm trắng vào bữa tối", INTENT_LOG_ACTION),
    ("vừa ăn 1 tô phở bò", INTENT_LOG_ACTION),
    ("mới ăn 2 quả trứng luộc bữa sáng", INTENT_LOG_ACTION),
    ("thêm 100g cá hồi vào nhật ký", INTENT_LOG_ACTION),
    ("hôm nay mình nặng 68.5kg", INTENT_LOG_ACTION),
    ("cập nhật cân nặng 70kg vòng eo 80cm", INTENT_LOG_ACTION),
    ("log 150g chicken breast for lunch", INTENT_LOG_ACTION),
    ("record weight 67kg today", INTENT_LOG_ACTION),
    ("nhập cân nặng 65 kg", INTENT_LOG_ACTION),
    ("chạy bộ 30 phút mức vừa", INTENT_LOG_ACTION),
    ("hôm nay tập gym 45 phút", INTENT_LOG_ACTION),
    ("mới tập chân 50 phút xong", INTENT_LOG_ACTION),
    ("vừa đạp xe 40 phút", INTENT_LOG_ACTION),
    ("ghi nhận bơi lội 30 phút", INTENT_LOG_ACTION),
    ("log 40 min cycling moderate", INTENT_LOG_ACTION),
    # ── daily_progress ──
    ("hôm nay tôi đã ăn bao nhiêu calo rồi", INTENT_DAILY_PROGRESS),
    ("tổng kết dinh dưỡng hôm nay", INTENT_DAILY_PROGRESS),
    ("còn bao nhiêu calo nữa cho hôm nay", INTENT_DAILY_PROGRESS),
    ("tiến độ 7 ngày gần nhất ra sao", INTENT_DAILY_PROGRESS),
    ("30 ngày qua trung bình ăn bao nhiêu calo", INTENT_DAILY_PROGRESS),
    ("tuần này tập được mấy buổi rồi", INTENT_DAILY_PROGRESS),
    ("xem nhật ký ăn uống hôm qua", INTENT_DAILY_PROGRESS),
    ("how many calories have i eaten today", INTENT_DAILY_PROGRESS),
    ("show my progress this week", INTENT_DAILY_PROGRESS),
    # ── coaching_general ──
    ("150g ức gà có đủ đạm cho mục tiêu giảm cân của mình không", INTENT_COACHING_GENERAL),
    ("ăn cơm trắng có mập không nên ăn bao nhiêu", INTENT_COACHING_GENERAL),
    ("so sánh phở bò và bún bò huế món nào ít calo hơn", INTENT_COACHING_GENERAL),
    ("tính bmi bmr và tdee của tôi", INTENT_COACHING_GENERAL),
    ("tôi muốn giảm mỡ tăng cơ thì nên ăn thế nào", INTENT_COACHING_GENERAL),
    ("gợi ý chương trình tập luyện phù hợp với tôi", INTENT_COACHING_GENERAL),
    ("kỹ thuật squat đúng cách theo nasm", INTENT_COACHING_GENERAL),
    ("tổ chức y tế thế giới khuyến nghị vận động bao nhiêu phút", INTENT_COACHING_GENERAL),
    ("xin chào bạn có thể giúp gì cho tôi", INTENT_COACHING_GENERAL),
    ("chọn mục 1", INTENT_COACHING_GENERAL),
    ("should i eat oats before workout", INTENT_COACHING_GENERAL),
    ("compare chicken breast vs salmon for fat loss", INTENT_COACHING_GENERAL),
    # ── out_of_scope ──
    ("giá vé world cup bao nhiêu", INTENT_OUT_OF_SCOPE),
    ("viết giúp tôi một bài thơ về mùa thu", INTENT_OUT_OF_SCOPE),
    ("thời tiết hôm nay ở sài gòn thế nào", INTENT_OUT_OF_SCOPE),
    ("hướng dẫn tôi cách nấu canh chua cá lóc ngon", INTENT_OUT_OF_SCOPE),
    ("công thức nấu bún riêu cua chuẩn vị", INTENT_OUT_OF_SCOPE),
    ("kể cho mình nghe một câu chuyện cười", INTENT_OUT_OF_SCOPE),
    ("viết code python sắp xếp mảng giúp tôi", INTENT_OUT_OF_SCOPE),
    ("sửa lỗi javascript react giúp mình", INTENT_OUT_OF_SCOPE),
    ("giá bitcoin và chứng khoán hôm nay sao rồi", INTENT_OUT_OF_SCOPE),
    ("ai vô địch bóng đá ngoại hạng anh năm nay", INTENT_OUT_OF_SCOPE),
    ("giải phương trình bậc hai giúp em", INTENT_OUT_OF_SCOPE),
    ("gợi ý địa điểm du lịch đà lạt 3 ngày", INTENT_OUT_OF_SCOPE),
    ("write a poem about autumn", INTENT_OUT_OF_SCOPE),
    ("what is the weather forecast tomorrow", INTENT_OUT_OF_SCOPE),
    ("write a python script to sort a list", INTENT_OUT_OF_SCOPE),
    ("how much is a bitcoin worth today", INTENT_OUT_OF_SCOPE),
    ("recommend a good action movie to watch", INTENT_OUT_OF_SCOPE),
    ("how to cook beef pho recipe", INTENT_OUT_OF_SCOPE),
)

# Từ khoá chặn fast-path để câu ghép/hỏi tư vấn/ghi nhật ký luôn đi qua LLM Agent
GUARD_BLOCK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(ghi|luu|nhap|them|log|record|add|save|track)\b"),
    re.compile(r"\b(vua an|moi an|da an|an xong|just ate|ate)\b"),
    re.compile(r"\b(so sanh|khac nhau|tot hon|it hon|nhieu hon|compare|versus|vs)\b"),
    re.compile(r"\b(co nen|nen an|co map|co beo|co tot|du khong|du chua|phu hop|should i|can i)\b"),
    re.compile(r"\b(muc tieu|giam can|tang can|tang co|giam mo|tdee|bmr|bmi|goal|lose weight|bulk|cut)\b"),
    re.compile(r"\b(hom nay|hom qua|tuan nay|thang nay|tien do|nhat ky|tong ket|today|yesterday|progress)\b"),
    re.compile(r"\b(tap luyen|chuong trinh|bai tap|workout|program|training)\b"),
    re.compile(r"\b(chay bo|dap xe|boi loi|tap gym|vua tap|moi tap|da tap|phut|minutes|mins)\b"),
    re.compile(r"\b(hay la|hoac|versus|vs)\b"),
)

_GRAMS_RE = re.compile(r"(?<!\w)(\d+(?:[.,]\d+)?)\s*(?:g|gam|gram|grams)\b", re.IGNORECASE)

# Cụm hỏi tiếng Việt có dấu chính xác (tránh nhầm "của" với "cua", "là" với "lá"...)
_ACCENTED_BOILERPLATE_RE = re.compile(
    r"(?<!\w)(?:"
    r"giá\s+trị\s+dinh\s+dưỡng|thông\s+tin\s+dinh\s+dưỡng|thành\s+phần\s+dinh\s+dưỡng|"
    r"bao\s+nhiêu|cho\s+(?:mình|tôi|em)\s+hỏi|cho\s+hỏi|"
    r"chất\s+béo|chất\s+xơ|tinh\s+bột|năng\s+lượng|dinh\s+dưỡng|thành\s+phần|"
    r"tra\s+cứu|tìm\s+kiếm|kiểm\s+tra|thực\s+phẩm|"
    r"của|trong|món|có|là|gì|không|đạm|xơ|béo|trên|mỗi|một"
    r")(?!\w)",
    re.IGNORECASE,
)

# Cụm hỏi tiếng Anh / từ không dấu rõ nghĩa (không trùng từ thực phẩm thông dụng)
_UNACCENTED_BOILERPLATE_PHRASES: tuple[str, ...] = (
    "gia tri dinh duong",
    "thong tin dinh duong",
    "thanh phan dinh duong",
    "how many calories in",
    "how much protein in",
    "nutrition facts for",
    "nutrition facts of",
    "nutrition info for",
    "nutrition of",
    "macros for",
    "macros in",
    "calories in",
    "calories of",
    "food details for",
    "details for",
    "what is the",
    "bao nhieu",
    "dinh duong",
    "nang luong",
    "tra cuu",
    "tim kiem",
    "kiem tra",
    "cho hoi",
    "chat beo",
    "chat xo",
    "tinh bot",
    "carbohydrate",
    "calories",
    "calorie",
    "protein",
    "glucid",
    "lipid",
    "check",
    "lookup",
    "kcal",
    "calo",
    "carb",
    "carbs",
    "macro",
    "macros",
    "fat",
    "fiber",
    "bn",
    "for",
    "of",
    "in",
    "the",
    "is",
    "are",
    "what",
    "show",
    "me",
    "tell",
    "100",
    "per",
)


@dataclass(frozen=True)
class IntentPrediction:
    intent: str
    confidence: float
    probs: dict[str, float]


@dataclass(frozen=True)
class FoodLookupSlot:
    query: str
    grams: float | None = None


def _tokenize_for_classifier(text: str) -> list[str]:
    norm = normalize_search(text)
    words = norm.split()
    grams_replaced = [("<NUM_G>" if re.fullmatch(r"\d+(?:g)?", w) else w) for w in words]
    unigrams = grams_replaced
    bigrams = [f"{a}_{b}" for a, b in zip(grams_replaced, grams_replaced[1:])]
    return unigrams + bigrams


_ENCODER_LOCK = Lock()
_ENCODERS: dict[str, tuple[Any, Any] | None] = {}


def _fit_softmax_head(
    X: np.ndarray,
    Y: np.ndarray,
    *,
    lr: float,
    reg: float,
    steps: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Huấn luyện đầu phân loại Softmax Logistic Regression (NumPy) bằng gradient descent."""
    n_docs, n_feat = X.shape
    n_cls = Y.shape[1]
    W = np.zeros((n_feat, n_cls), dtype=np.float64)
    b = np.zeros(n_cls, dtype=np.float64)
    for _ in range(steps):
        logits = X @ W + b
        logits -= logits.max(axis=1, keepdims=True)
        exp_logits = np.exp(logits)
        probs = exp_logits / exp_logits.sum(axis=1, keepdims=True)
        diff = (probs - Y) / n_docs
        W -= lr * (X.T @ diff + reg * W)
        b -= lr * diff.sum(axis=0)
    return W, b


def _predict_from_logits(logits: np.ndarray, labels: list[str]) -> IntentPrediction:
    shifted = logits - logits.max()
    exp_l = np.exp(shifted)
    probs_arr = exp_l / exp_l.sum()
    best_idx = int(np.argmax(probs_arr))
    probs = {lbl: float(probs_arr[i]) for i, lbl in enumerate(labels)}
    return IntentPrediction(
        intent=labels[best_idx],
        confidence=float(probs_arr[best_idx]),
        probs=probs,
    )


def _load_embedding_encoder(model_id: str) -> tuple[Any, Any] | None:
    """Nạp lười tokenizer + encoder đa ngữ (mặc định BAAI/bge-m3), ưu tiên cache cục bộ."""
    if not settings.INTENT_EMBEDDING_ENABLED or not model_id.strip():
        return None
    with _ENCODER_LOCK:
        if model_id in _ENCODERS:
            return _ENCODERS[model_id]
        try:
            from transformers import AutoModel, AutoTokenizer

            try:
                tok = AutoTokenizer.from_pretrained(model_id, local_files_only=True)
                mod = AutoModel.from_pretrained(model_id, local_files_only=True)
            except OSError:
                tok = AutoTokenizer.from_pretrained(model_id)
                mod = AutoModel.from_pretrained(model_id)
            mod.eval()
            _ENCODERS[model_id] = (tok, mod)
            logger.info("Loaded intent embedding encoder '%s'", model_id)
        except Exception as exc:  # noqa: BLE001 — tự động rơi về TF-IDF khi thiếu model/mạng/RAM
            logger.warning("Intent embedding encoder '%s' unavailable (%s); using TF-IDF fallback", model_id, type(exc).__name__)
            _ENCODERS[model_id] = None
        return _ENCODERS[model_id]


def _encode_texts(texts: list[str], tok: Any, mod: Any) -> np.ndarray:
    """Mã hoá câu thành vector chuẩn hoá L2 theo CLS pooling của BGE-M3."""
    import torch
    import torch.nn.functional as F

    with torch.inference_mode():
        enc = tok(
            texts,
            padding=True,
            truncation=True,
            max_length=_EMBEDDING_MAX_LENGTH,
            return_tensors="pt",
        )
        out = mod(**enc)
        emb = out.last_hidden_state[:, 0]
        emb = F.normalize(emb, p=2, dim=-1)
        return emb.cpu().numpy().astype(np.float64)


def _head_cache_dir() -> Path:
    hf_home = os.environ.get("HF_HOME", "").strip()
    if hf_home:
        return Path(hf_home) / "fitai_intent_heads"
    home_dir = Path.home()
    if home_dir.is_dir() and os.access(home_dir, os.W_OK):
        return home_dir / ".cache" / "huggingface" / "fitai_intent_heads"
    return Path(tempfile.gettempdir()) / "fitai_intent_heads"


def _head_cache_path(model_id: str, docs: list[tuple[str, str]]) -> Path:
    h = hashlib.sha256()
    h.update(f"{model_id}|{_EMBEDDING_HEAD_LR}|{_EMBEDDING_HEAD_REG}|{_EMBEDDING_HEAD_STEPS}\n".encode("utf-8"))
    for text, label in docs:
        h.update(f"{label}\t{text}\n".encode("utf-8"))
    return _head_cache_dir() / f"head_{h.hexdigest()[:16]}.npz"


class IntentClassifier:
    """Bộ phân loại ý định đa ngữ: BGE-M3 (đóng băng) + Softmax Logistic Regression, fallback TF-IDF."""

    def __init__(
        self,
        samples: Iterable[tuple[str, str]] = TRAINING_SAMPLES,
        *,
        use_embedding: bool = True,
        model_id: str | None = None,
    ) -> None:
        self._docs = list(samples)
        self.labels = sorted({label for _, label in self._docs})
        label_to_idx = {lbl: i for i, lbl in enumerate(self.labels)}
        self._Y = np.eye(len(self.labels), dtype=np.float64)[
            np.array([label_to_idx[lbl] for _, lbl in self._docs], dtype=np.int64)
        ]

        # Luôn khởi tạo sẵn TF-IDF (<2 ms) làm tầng dự phòng tức thời
        tokenized = [_tokenize_for_classifier(text) for text, _ in self._docs]
        vocab_list = sorted({tok for toks in tokenized for tok in toks})
        self.vocab = {tok: i for i, tok in enumerate(vocab_list)}

        n_docs = len(self._docs)
        n_feat = len(self.vocab)
        df = np.zeros(n_feat, dtype=np.float64)
        tf = np.zeros((n_docs, n_feat), dtype=np.float64)
        for i, toks in enumerate(tokenized):
            for t in toks:
                tf[i, self.vocab[t]] += 1.0
            for idx in {self.vocab[t] for t in toks}:
                df[idx] += 1.0

        self.idf = np.log((1.0 + n_docs) / (1.0 + df)) + 1.0
        X_tfidf = self._featurize_matrix(tf)
        self.W, self.b = _fit_softmax_head(X_tfidf, self._Y, lr=0.8, reg=1e-3, steps=350)

        self._use_embedding = use_embedding
        self._model_id = (model_id or settings.INTENT_EMBEDDING_MODEL).strip()
        self._lock = Lock()
        self._embedding_attempted = False
        self._emb_pair: tuple[Any, Any] | None = None
        self._emb_W: np.ndarray | None = None
        self._emb_b: np.ndarray | None = None
        self._pred_cache: OrderedDict[str, IntentPrediction] = OrderedDict()

    @property
    def backend_name(self) -> str:
        if self._emb_pair is not None and self._emb_W is not None and self._emb_b is not None:
            return "bge-m3"
        return "tfidf"

    def _featurize_matrix(self, tf: np.ndarray) -> np.ndarray:
        tfidf = tf * self.idf
        norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return tfidf / norms

    def _ensure_embedding_head(self) -> bool:
        if not self._use_embedding or not settings.INTENT_EMBEDDING_ENABLED:
            return False
        if self._emb_W is not None and self._emb_pair is not None:
            return True
        if self._embedding_attempted:
            return False

        with self._lock:
            if self._emb_W is not None and self._emb_pair is not None:
                return True
            if self._embedding_attempted:
                return False
            self._embedding_attempted = True

            pair = _load_embedding_encoder(self._model_id)
            if pair is None:
                return False

            cache_file = _head_cache_path(self._model_id, self._docs)
            if cache_file.is_file():
                try:
                    data = np.load(cache_file, allow_pickle=False)
                    W_cached = data["W"]
                    b_cached = data["b"]
                    labels_cached = data["labels"].tolist()
                    if labels_cached == self.labels and W_cached.shape[1] == len(self.labels):
                        self._emb_pair = pair
                        self._emb_W = W_cached
                        self._emb_b = b_cached
                        self._pred_cache.clear()
                        return True
                except Exception as exc:  # noqa: BLE001 — hỏng file cache thì tính lại sạch
                    logger.warning("Failed reading intent head cache (%s); recomputing", type(exc).__name__)

            tok, mod = pair
            X_emb = _encode_texts([text for text, _ in self._docs], tok, mod)
            W_emb, b_emb = _fit_softmax_head(
                X_emb,
                self._Y,
                lr=_EMBEDDING_HEAD_LR,
                reg=_EMBEDDING_HEAD_REG,
                steps=_EMBEDDING_HEAD_STEPS,
            )
            self._emb_pair = pair
            self._emb_W = W_emb
            self._emb_b = b_emb
            self._pred_cache.clear()

            try:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                tmp_fd, tmp_name = tempfile.mkstemp(dir=str(cache_file.parent), suffix=".npz")
                os.close(tmp_fd)
                np.savez(
                    tmp_name,
                    W=W_emb,
                    b=b_emb,
                    labels=np.array(self.labels),
                )
                os.replace(tmp_name, cache_file)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not persist intent head cache: %s", type(exc).__name__)
            return True

    def warmup(self) -> str:
        """Khởi tạo trước encoder BGE-M3 (nếu bật) và trả tên backend đang hoạt động."""
        self._ensure_embedding_head()
        return self.backend_name

    def _tfidf_predict(self, text: str) -> IntentPrediction:
        tf = np.zeros((1, len(self.vocab)), dtype=np.float64)
        for tok in _tokenize_for_classifier(text):
            idx = self.vocab.get(tok)
            if idx is not None:
                tf[0, idx] += 1.0
        X = self._featurize_matrix(tf)
        logits = (X @ self.W + self.b)[0]
        return _predict_from_logits(logits, self.labels)

    def predict(self, text: str) -> IntentPrediction:
        raw = (text or "").strip()
        with self._lock:
            cached = self._pred_cache.get(raw)
            if cached is not None:
                self._pred_cache.move_to_end(raw)
                return cached

        use_emb = self._ensure_embedding_head()
        if use_emb and self._emb_pair is not None and self._emb_W is not None and self._emb_b is not None:
            tok, mod = self._emb_pair
            X_emb = _encode_texts([raw], tok, mod)
            logits = (X_emb @ self._emb_W + self._emb_b)[0]
            pred = _predict_from_logits(logits, self.labels)
        else:
            pred = self._tfidf_predict(raw)

        with self._lock:
            self._pred_cache[raw] = pred
            self._pred_cache.move_to_end(raw)
            if len(self._pred_cache) > _PRED_CACHE_MAX:
                self._pred_cache.popitem(last=False)
        return pred


_CLASSIFIER = IntentClassifier()


def classify_intent(text: str) -> IntentPrediction:
    return _CLASSIFIER.predict(text)


def get_intent_backend() -> str:
    return _CLASSIFIER.backend_name


def warmup_intent_classifier() -> str:
    return _CLASSIFIER.warmup()


def extract_food_lookup_slot(text: str) -> FoodLookupSlot | None:
    """Tách (tên thực phẩm, khối lượng gram) nếu câu hỏi là tra cứu thực phẩm đơn lẻ."""
    raw = (text or "").strip()
    if not raw or len(raw) > 120:
        return None

    norm = normalize_search(raw)
    if any(pat.search(norm) for pat in GUARD_BLOCK_PATTERNS):
        return None

    # Tách grams nếu có (vd "150g", "200 gam")
    grams: float | None = None
    m_grams = _GRAMS_RE.search(raw)
    if m_grams:
        try:
            grams = float(m_grams.group(1).replace(",", "."))
        except ValueError:
            grams = None

    # Làm sạch giữ nguyên dấu trước (của ≠ cua, là ≠ lá) rồi mới lọc cụm không dấu rõ nghĩa
    cleaned = _GRAMS_RE.sub(" ", raw)
    cleaned = _ACCENTED_BOILERPLATE_RE.sub(" ", cleaned)
    cleaned_norm = normalize_search(cleaned)
    for phrase in _UNACCENTED_BOILERPLATE_PHRASES:
        cleaned_norm = re.sub(rf"\b{re.escape(phrase)}\b", " ", cleaned_norm)

    cleaned_words_norm = cleaned_norm.split()
    if not cleaned_words_norm or len(cleaned_words_norm) > 6:
        return None

    # Nếu bản gốc có dấu và các từ còn lại khớp tuần tự từ bản có dấu, ưu tiên giữ dấu cho xếp hạng tìm kiếm
    raw_tokens = re.findall(r"[0-9A-Za-zÀ-ỹ]+", cleaned)
    kept_tokens: list[str] = []
    target_idx = 0
    for tok in raw_tokens:
        if target_idx < len(cleaned_words_norm) and normalize_search(tok) == cleaned_words_norm[target_idx]:
            kept_tokens.append(tok)
            target_idx += 1

    query = " ".join(kept_tokens) if target_idx == len(cleaned_words_norm) and kept_tokens else " ".join(cleaned_words_norm)
    query = query.strip()
    if len(query) < 2:
        return None
    return FoodLookupSlot(query=query, grams=grams)


def _format_source_citation_short(food) -> str:
    code = source_code(food)
    if code == USDA_SR:
        return f"USDA FoodData Central SR Legacy (dữ liệu thực phẩm Mỹ, fdc_id {food.source_ref})"
    if code == ADMIN_MANUAL:
        note = short_note(getattr(food, "source_note", None))
        extra = f" — nguồn: {note}" if note else ""
        return f"Quản trị viên nhập ({food.source_ref}{extra})"
    return f"Bảng thành phần thực phẩm Việt Nam 2007 (tr. PDF {food.source_page})"


def format_fast_food_reply(query: str, matches: list[FoodMatch], grams: float | None) -> str:
    """Định dạng câu trả lời tiếng Việt trực tiếp từ kết quả DB, tuân thủ mọi quy tắc an toàn."""
    if all(m.is_suggestion for m in matches):
        lines = [f"Không có mục trùng đúng tên **\"{query}\"** trong bảng thực phẩm. Các mục gần nhất:"]
        for i, m in enumerate(matches[:5], 1):
            lines.append(f"{i}. {m.food.name_vi} *(nhóm: {m.food.group_name})*")
        lines.append("\nBạn muốn xem chi tiết mục nào?")
        return "\n".join(lines)

    exact = [m for m in matches if m.is_exact]
    display_matches = exact if exact else matches[:4]

    lines = [f"🔎 **Kết quả tra cứu nhanh cho \"{query}\":**"]
    if not exact:
        lines.append("*(Chưa có mục trùng hoàn toàn; dưới đây là các thực phẩm có chứa từ khoá:)*")

    for i, m in enumerate(display_matches[:4], 1):
        f = m.food
        refuse = f"{f.refuse_pct:g}%" if f.refuse_pct is not None else "không rõ"
        lines.append(
            f"\n**{i}. {source_name(f)}**\n"
            f"- Trạng thái: {preparation_label(f)} | Thải bỏ: {refuse}\n"
            f"- Nguồn: {_format_source_citation_short(f)}\n"
            f"- Trên 100 g: {nutrient_line(f)}"
        )
        if m.note:
            lines.append(f"- Ghi chú: {m.note}")
        if grams is None and m.is_exact:
            per_srv = serving_line(f)
            if per_srv:
                lines.append(f"- {per_srv.strip()}")
        if grams is not None:
            unit = "g phần ăn được" if source_code(f) == VN2007 else "g"
            lines.append(f"- **Theo {grams:g} {unit}:** {nutrient_line(f, grams)}")

    return "\n".join(lines)


async def try_fast_food_lookup(db: AsyncSession, message: str) -> tuple[str, list[dict]] | None:
    """Thử định tuyến nhanh nếu là câu hỏi tra cứu thực phẩm đơn lẻ.

    Trả `(reply_text, sources)` khi xử lý xong trực tiếp từ DB;
    trả `None` để chuyển tiếp cho `FitnessAdvisorAgent` (LLM).
    """
    norm = normalize_search(message or "")
    if not _FOOD_LOOKUP_CUE_RE.search(norm):
        return None

    pred = await asyncio.to_thread(classify_intent, message)
    if pred.intent != INTENT_FOOD_LOOKUP or pred.confidence < FAST_PATH_CONFIDENCE_THRESHOLD:
        return None

    slot = extract_food_lookup_slot(message)
    if slot is None:
        return None

    try:
        grams = validate_grams(slot.grams)
        matches = await search_foods(db, slot.query, limit=5)
    except FoodQueryError:
        return None
    except AmbiguousFoodQuery as amb:
        lines = [f"**\"{amb.term}\"** có nhiều loại khác nhau trong bảng thực phẩm. Bạn muốn tra loại nào?"]
        for i, m in enumerate(amb.meanings, 1):
            if m.search:
                lines.append(f"{i}. {m.label} *(gõ \"{m.search}\" để xem chi tiết)*")
            else:
                names = "; ".join(f"{f.name_vi} ({preparation_label(f)})" for f in m.foods)
                lines.append(f"{i}. {m.label}: {names}")
        return "\n".join(lines), []
    except RawOnlyFoodQuery as raw:
        lines = [
            f"Bảng thành phần thực phẩm Việt Nam 2007 chưa có **\"{raw.dish.label}\"** (món đã nấu), "
            f"chỉ có **{raw.dish.raw_label} SỐNG** (không dùng thay trực tiếp cho món đã nấu):"
        ]
        for i, f in enumerate(raw.foods, 1):
            lines.append(f"{i}. {source_name(f)} — Trên 100 g sống: {nutrient_line(f)}")
        return "\n".join(lines), []
    except FoodLookupError:
        return None

    if not matches:
        # Không tìm thấy trong DB → nhường LLM xử lý / gợi ý linh hoạt
        return None

    if all(m.is_suggestion for m in matches):
        sources: list[dict] = []
    else:
        exact = [m for m in matches if m.is_exact]
        displayed = exact[:4] if exact else matches[:4]
        sources = [citation(m.food) for m in displayed]
    reply = format_fast_food_reply(slot.query, matches, grams)
    logger.info("Intent fast-path handled food_lookup (confidence=%.2f)", pred.confidence)
    return reply, sources


def is_out_of_scope(message: str) -> bool:
    """Kiểm tra câu hỏi có rõ ràng nằm ngoài phạm vi FitAI để chặn TRƯỚC khi gọi Gemini."""
    raw = (message or "").strip()
    if not raw:
        return False
    norm = normalize_search(raw)
    if _IN_DOMAIN_GUARD_RE.search(norm):
        return False
    if _EXPLICIT_OFF_TOPIC_RE.search(norm):
        return True
    # Không dùng classifier chặn các câu quá ngắn (< 5 từ) chưa rõ ngữ cảnh (vd. câu hỏi tiếp nối / tin nhắn ngắn)
    if len(norm.split()) < 5:
        return False
    pred = classify_intent(raw)
    threshold = (
        EMBEDDING_OUT_OF_SCOPE_CONFIDENCE_THRESHOLD
        if _CLASSIFIER.backend_name == "bge-m3"
        else OUT_OF_SCOPE_CONFIDENCE_THRESHOLD
    )
    return pred.intent == INTENT_OUT_OF_SCOPE and pred.confidence >= threshold


async def try_fast_route(db: AsyncSession, message: str) -> tuple[str, list[dict]] | None:
    """Định tuyến nhanh trước khi gọi LLM:
    1) Từ chối ngay câu hỏi ngoài phạm vi (`out_of_scope`, 0 DB, 0 LLM token).
    2) Tra cứu nhanh dinh dưỡng thực phẩm (`food_lookup`, PostgreSQL trực tiếp, 0 LLM token).
    3) Còn lại trả `None` để chuyển cho `FitnessAdvisorAgent`.
    """
    if await asyncio.to_thread(is_out_of_scope, message):
        logger.info("Intent classifier blocked out_of_scope query before LLM")
        return OUT_OF_SCOPE_REPLY, []
    return await try_fast_food_lookup(db, message)
