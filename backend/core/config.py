import os
from typing import List
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator, model_validator


def _rewrite_db_url(raw_url: str, *, driver: str) -> str:
    """Chuẩn hoá PostgreSQL URL (bao gồm Neon sslmode/channel_binding) theo driver."""
    url = raw_url.strip()
    if not url:
        return url
    parsed = urlparse(url)
    base_scheme = parsed.scheme.split("+", 1)[0]
    if base_scheme not in ("postgres", "postgresql"):
        return url

    qs = parse_qs(parsed.query, keep_blank_values=True)
    if driver == "asyncpg":
        sslmode = (qs.pop("sslmode", [""])[0] or "").lower()
        qs.pop("channel_binding", None)
        if sslmode in ("require", "verify-ca", "verify-full") and "ssl" not in qs:
            qs["ssl"] = ["require"]
    elif driver == "psycopg2":
        ssl_val = (qs.pop("ssl", [""])[0] or "").lower()
        if ssl_val in ("require", "true", "1") and "sslmode" not in qs:
            qs["sslmode"] = ["require"]

    return urlunparse((
        f"postgresql+{driver}",
        parsed.netloc,
        parsed.path,
        parsed.params,
        urlencode(qs, doseq=True),
        parsed.fragment,
    ))


def build_sync_database_url(raw_url: str) -> str:
    """Chuyển DATABASE_URL sang driver sync psycopg2 cho Alembic."""
    return _rewrite_db_url(raw_url, driver="psycopg2")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",   # ignore vars like POSTGRES_USER used only by docker-compose
    )

    # Application
    APP_NAME: str = "FitAI Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    # In câu SQL ra log (mặc định tắt, tách khỏi DEBUG). Tham số luôn bị ẩn (hide_parameters)
    SQL_ECHO: bool = False
    ENVIRONMENT: str = "development"

    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("SECRET_KEY is required and cannot be empty.")
        return v

    # Database (Docker Compose helpers — kept here for reference)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "fitai_db"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fitai_db"
    DATABASE_URL_UNPOOLED: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str) and v.strip():
            return _rewrite_db_url(v, driver="asyncpg")
        return v

    @model_validator(mode="after")
    def fallback_docker_database_url(self):
        # Khi chạy trong Docker mà backend/.env không khai báo DATABASE_URL thì trỏ về service `db`
        if ("DATABASE_URL" not in self.model_fields_set or not self.DATABASE_URL.strip()) and os.path.exists("/.dockerenv"):
            self.DATABASE_URL = f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@db:5432/{self.POSTGRES_DB}"
        return self

    # Nhà cung cấp LLM chính ("gemini" hoặc "openrouter")
    LLM_PROVIDER: str = "gemini"

    # Google Gemini AI
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    # Đổi model embedding thì phải chạy lại ingest với --reset (vector cũ không còn so sánh được)
    EMBEDDING_MODEL: str = "models/gemini-embedding-001"

    # OpenRouter (OpenAI-compatible API cho chat + tool calling + vision, vd. qwen/qwen3.7-flash)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "qwen/qwen3.7-flash"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_REASONING_EFFORT: str = "low"

    # Dịch máy cục bộ (MarianMT / OPUS-MT) hỗ trợ tra cứu món ăn 2 chiều Việt <-> Anh khi không khớp từ khoá
    FOOD_NMT_ENABLED: bool = True
    FOOD_NMT_VI_EN_MODEL: str = "Helsinki-NLP/opus-mt-vi-en"
    FOOD_NMT_EN_VI_MODEL: str = "Helsinki-NLP/opus-mt-en-vi"
    FOOD_NMT_MIN_CONFIDENCE: float = 0.55

    # Bộ phân loại ý định (BGE-M3 dense embedding + Softmax Logistic Regression, fallback TF-IDF)
    INTENT_EMBEDDING_ENABLED: bool = True
    INTENT_EMBEDDING_MODEL: str = "BAAI/bge-m3"

    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION_NAME: str = "fitai_knowledge"

    # RAG
    KNOWLEDGE_DIR: str = "data/knowledge"
    RAG_TOP_K: int = 5
    # Ngưỡng độ tương đồng cosine (1 - khoảng cách); tạm thời, chốt sau khi chạy rag_smoke
    RAG_SIMILARITY_THRESHOLD: float = 0.65

    # Quản trị tài liệu RAG (lát 8b-1). Thư mục tải lên ghi được, ngoài /app/data (chỉ đọc).
    KNOWLEDGE_UPLOAD_DIR: str = "uploads"
    KNOWLEDGE_MAX_UPLOAD_MB: int = 20
    KNOWLEDGE_MAX_PDF_PAGES: int = 300
    KNOWLEDGE_PDF_TIMEOUT_S: int = 60         # đọc/làm sạch PDF trong tiến trình con, quá hạn thì huỷ
    KNOWLEDGE_PDF_MEMORY_MB: int = 1024       # giới hạn bộ nhớ ảo của tiến trình con đọc PDF
    KNOWLEDGE_MAX_CHUNKS: int = 400           # vượt thì không nhúng (tai_lieu_qua_dai)

    # Xem hội thoại ẩn danh (lát 8b-2) — dữ liệu sức khoẻ, mặc định TẮT
    ADMIN_CONVERSATION_VIEWER_ENABLED: bool = False
    ADMIN_CONVERSATION_VIEW_DAILY_LIMIT: int = 30

    # Telegram Bot (tùy chọn — để trống nếu không chạy bot)
    TELEGRAM_BOT_TOKEN: str = ""

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []


settings = Settings()
