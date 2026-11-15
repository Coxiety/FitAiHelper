"""Dịch máy cục bộ 2 chiều Việt ↔ Anh (Helsinki-NLP/opus-mt) cho tra cứu thực phẩm.

Chỉ được gọi làm tầng dự phòng khi tìm kiếm trực tiếp, từ đồng nghĩa và từ điển Việt–Anh
không cho kết quả. Nạp model lười (lazy singleton), ưu tiên cache cục bộ trước, chạy trong
thread pool để không chặn event loop và bỏ qua các kết quả dịch nhiễu / lặp từ.
"""
from __future__ import annotations

import asyncio
import logging
import math
import re
from functools import lru_cache
from threading import Lock
from typing import Any

from core.config import settings
from services.foods.aliases import COLOR_TOKENS
from services.foods.normalize import normalize_search

logger = logging.getLogger(__name__)

_PUNCT_RE = re.compile(r"[.!?;:\"'()\[\]]+")
_EN_STOPWORDS = frozenset({"a", "an", "the", "of", "in", "on", "with", "for", "and", "or", "to", "more", "some"})
_VI_ACCENTED_STOPWORDS = frozenset({"của", "và", "các", "những", "một", "cái", "với", "cho", "là", "bằng"})
_COLOR_TOKENS_ALL = COLOR_TOKENS | frozenset(
    {"white", "red", "green", "yellow", "black", "purple", "orange", "brown"}
)
_GARBAGE_TOKENS = frozenset(
    {
        "i", "me", "my", "you", "your", "we", "our", "they", "he", "she", "it",
        "this", "that", "name", "ill", "im", "ll", "re", "ve",
    }
)
_VI_ACCENTED_GARBAGE = frozenset({"tôi", "bạn", "chúng", "không", "gì", "nào", "đây", "đó"})

_MODEL_LOCK = Lock()
_MODELS: dict[str, tuple[Any, Any] | None] = {}


def _load_model_pair(model_id: str) -> tuple[Any, Any] | None:
    """Nạp tokenizer + model Seq2Seq một lần; lỗi/thiếu thư viện trả None để tra cứu vẫn chạy."""
    with _MODEL_LOCK:
        if model_id in _MODELS:
            return _MODELS[model_id]
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            try:
                tok = AutoTokenizer.from_pretrained(model_id, local_files_only=True)
                mod = AutoModelForSeq2SeqLM.from_pretrained(model_id, local_files_only=True)
            except OSError:
                tok = AutoTokenizer.from_pretrained(model_id)
                mod = AutoModelForSeq2SeqLM.from_pretrained(model_id)
            mod.eval()
            _MODELS[model_id] = (tok, mod)
        except Exception as exc:  # noqa: BLE001 — fallback an toàn khi thiếu model/mạng/RAM
            logger.warning("Food NMT model '%s' unavailable: %s", model_id, type(exc).__name__)
            _MODELS[model_id] = None
        return _MODELS[model_id]


def _run_model(direction: str, raw_query: str) -> tuple[str | None, float]:
    model_id = settings.FOOD_NMT_VI_EN_MODEL if direction == "vi-en" else settings.FOOD_NMT_EN_VI_MODEL
    pair = _load_model_pair(model_id)
    if pair is None:
        return None, 0.0
    tok, mod = pair
    prompt = f">>vie<< {raw_query}" if direction == "en-vi" else raw_query
    import torch
    import torch.nn.functional as F

    with torch.inference_mode():
        enc = tok(prompt, return_tensors="pt", truncation=True, max_length=64)
        out = mod.generate(
            **enc,
            max_new_tokens=24,
            no_repeat_ngram_size=2,
            return_dict_in_generate=True,
            output_scores=True,
        )
        gen_ids = out.sequences[0, 1:]
        log_probs: list[float] = []
        for step, logits in enumerate(out.scores):
            if step >= len(gen_ids):
                break
            lp = F.log_softmax(logits[0], dim=-1)[gen_ids[step]].item()
            if math.isfinite(lp):
                log_probs.append(lp)
        confidence = math.exp(sum(log_probs) / len(log_probs)) if log_probs else 0.0
        text = tok.decode(out.sequences[0], skip_special_tokens=True).strip()
    return text, confidence


@lru_cache(maxsize=512)
def _cached_translate(direction: str, normalized_key: str, raw_query: str) -> tuple[str | None, float]:
    return _run_model(direction, raw_query)


def _clean_translated_tokens(direction: str, src_tokens: list[str], raw_output: str | None) -> tuple[list[str], str] | None:
    """Làm sạch kết quả dịch và loại bỏ câu giao tiếp / lặp / mất nội dung."""
    if not raw_output:
        return None
    cleaned = _PUNCT_RE.sub(" ", raw_output).strip()
    if not cleaned:
        return None
    words = [w.lower() for w in cleaned.split() if w]
    if direction == "en-vi":
        if any(w in _VI_ACCENTED_GARBAGE for w in words):
            return None
        words = [w for w in words if w not in _VI_ACCENTED_STOPWORDS]
    raw_norm_tokens = normalize_search(" ".join(words)).split()
    if any(t in _GARBAGE_TOKENS for t in raw_norm_tokens):
        return None
    norm_tokens = [t for t in raw_norm_tokens if len(t) >= 2]
    if direction == "vi-en":
        norm_tokens = [t for t in norm_tokens if t not in _EN_STOPWORDS]
    if not norm_tokens or norm_tokens == src_tokens:
        return None
    if len(norm_tokens) > max(len(src_tokens) * 3, 6):
        return None
    if set(norm_tokens) <= _COLOR_TOKENS_ALL and not (set(src_tokens) <= _COLOR_TOKENS_ALL):
        return None
    return norm_tokens, cleaned


def _translate_sync(query: str) -> list[tuple[list[str], str]]:
    clean_query = " ".join(query.strip().split())
    src_tokens = normalize_search(clean_query).split()
    if not src_tokens or len(src_tokens) > 6:
        return []

    has_non_ascii = any(ord(ch) > 127 for ch in clean_query)
    directions = ["vi-en"] if has_non_ascii else ["en-vi", "vi-en"]

    results: list[tuple[list[str], str]] = []
    seen = {tuple(src_tokens)}
    for direction in directions:
        raw_out, conf = _cached_translate(direction, f"{direction}:{' '.join(src_tokens)}", clean_query)
        if conf < settings.FOOD_NMT_MIN_CONFIDENCE:
            continue
        parsed = _clean_translated_tokens(direction, src_tokens, raw_out)
        if parsed is None:
            continue
        out_tokens, display = parsed
        key = tuple(out_tokens)
        if key in seen:
            continue
        seen.add(key)
        results.append((out_tokens, f"dịch NMT ({direction}, {conf:.2f}): '{clean_query}' → '{display}'"))
        # Với câu hỏi tiếng Anh thuần hợp lệ, không cần ép dịch ngược thêm lần vi-en
        if direction == "en-vi":
            break
    return results


async def translate_food_query(query: str) -> list[tuple[list[str], str]]:
    """Dịch truy vấn món ăn Việt ↔ Anh bất đồng bộ (tắt nếu FOOD_NMT_ENABLED=False)."""
    if not settings.FOOD_NMT_ENABLED:
        return []
    return await asyncio.to_thread(_translate_sync, query)
