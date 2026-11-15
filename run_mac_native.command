#!/bin/bash
# ==============================================================================
# FitAI — Script khởi chạy tự động bằng 1 cú nhấp đúp trên macOS (.command)
# Bản Native All-in-One (KHÔNG cần Docker) — tương đương hoàn toàn với run_windows.bat
# ==============================================================================

set -u

# Chuyển về thư mục gốc của project (nơi chứa file .command này)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

TOOLS_DIR="$HOME/.local/share/FitAI_Tools"
mkdir -p "$TOOLS_DIR"

NODE_DIR="$TOOLS_DIR/nodejs"
PG_DIR="$TOOLS_DIR/pgsql"
PG_BIN="$PG_DIR/bin"
CHROMA_ENV="$TOOLS_DIR/chromadb_env"

export PATH="$NODE_DIR/bin:$PG_BIN:/opt/homebrew/opt/postgresql@16/bin:/usr/local/opt/postgresql@16/bin:/Applications/Postgres.app/Contents/Versions/16/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

# Màu sắc hiển thị trên Terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BLUE}${BOLD}==============================================================${NC}"
echo -e "${BLUE}${BOLD}     🚀 FitAI — Khởi động tự động trên macOS (Native)        ${NC}"
echo -e "${BLUE}${BOLD}==============================================================${NC}"
echo ""

# ------------------------------------------------------------------------------
# 1. Kiểm tra & Tự động thiết lập môi trường (Python 3.11, Node.js, PostgreSQL, ChromaDB)
# ------------------------------------------------------------------------------
echo -e "${BLUE}${BOLD}🔍 Đang kiểm tra các thành phần hệ thống...${NC}"

ensure_uv() {
    if ! command -v uv >/dev/null 2>&1; then
        echo -e "${BLUE}⬇️  Đang cài đặt uv (trình quản lý Python siêu nhanh)...${NC}"
        if ! curl -LsSf https://astral.sh/uv/install.sh | sh; then
            echo -e "${RED}❌ Cài đặt uv thất bại. Vui lòng kiểm tra kết nối mạng.${NC}"
            read -r -p "Nhấn Enter để thoát..."
            exit 1
        fi
        export PATH="$HOME/.local/bin:$PATH"
    fi
}

# 1a. Kiểm tra uv & Python 3.11 + backend/.venv
VENV_PY="$SCRIPT_DIR/backend/.venv/bin/python"
ALEMBIC="$SCRIPT_DIR/backend/.venv/bin/alembic"
UVICORN="$SCRIPT_DIR/backend/.venv/bin/uvicorn"

if [ ! -x "$VENV_PY" ]; then
    echo -e "${YELLOW}⚙️  Đang thiết lập môi trường Python 3.11 cho Backend (backend/.venv)...${NC}"
    ensure_uv
    uv python install 3.11
    uv venv --python 3.11 "$SCRIPT_DIR/backend/.venv"
    if ! uv pip install --python "$VENV_PY" -r "$SCRIPT_DIR/backend/requirements.txt"; then
        echo -e "${RED}❌ Lỗi khi cài thư viện Python cho Backend.${NC}"
        read -r -p "Nhấn Enter để thoát..."
        exit 1
    fi
fi

# Trên Apple Silicon (arm64), sqlalchemy==2.0.30 không tự kéo greenlet nếu thiếu extra [asyncio]
if ! "$VENV_PY" -c "import greenlet" >/dev/null 2>&1; then
    echo -e "${YELLOW}⚙️  Đang cài bổ sung greenlet cho SQLAlchemy Async trên macOS (arm64)...${NC}"
    ensure_uv
    if ! uv pip install --python "$VENV_PY" "greenlet>=3.0.0"; then
        echo -e "${RED}❌ Lỗi khi cài greenlet.${NC}"
        read -r -p "Nhấn Enter để thoát..."
        exit 1
    fi
fi

# 1b. Kiểm tra ChromaDB 1.5.9
CHROMA_EXE="$CHROMA_ENV/bin/chroma"
if [ ! -x "$CHROMA_EXE" ]; then
    echo -e "${YELLOW}⚙️  Đang cài đặt ChromaDB 1.5.9 Server...${NC}"
    ensure_uv
    uv venv --python 3.11 "$CHROMA_ENV"
    if ! uv pip install --python "$CHROMA_ENV/bin/python" "chromadb==1.5.9"; then
        echo -e "${RED}❌ Lỗi khi cài ChromaDB 1.5.9.${NC}"
        read -r -p "Nhấn Enter để thoát..."
        exit 1
    fi
fi

# 1c. Kiểm tra Node.js & frontend/node_modules
NODE_EXE="$NODE_DIR/bin/node"
NPM_CMD="$NODE_DIR/bin/npm"
if [ ! -x "$NODE_EXE" ]; then
    if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
        NODE_EXE="$(command -v node)"
        NPM_CMD="$(command -v npm)"
    else
        arch="$(uname -m)"
        node_arch="arm64"
        if [ "$arch" = "x86_64" ]; then
            node_arch="x64"
        fi
        node_ver="v22.22.0"
        node_pkg="node-${node_ver}-darwin-${node_arch}"
        node_tgz="/tmp/${node_pkg}.tar.gz"
        echo -e "${BLUE}⬇️  Đang tải Node.js ${node_ver} Portable cho macOS (${node_arch})...${NC}"
        if ! curl -fL --progress-bar "https://nodejs.org/dist/${node_ver}/${node_pkg}.tar.gz" -o "$node_tgz"; then
            echo -e "${RED}❌ Tải Node.js thất bại.${NC}"
            read -r -p "Nhấn Enter để thoát..."
            exit 1
        fi
        tar -xzf "$node_tgz" -C "$TOOLS_DIR"
        rm -rf "$NODE_DIR"
        mv "$TOOLS_DIR/$node_pkg" "$NODE_DIR"
        xattr -dr com.apple.quarantine "$NODE_DIR" 2>/dev/null || true
        rm -f "$node_tgz"
        NODE_EXE="$NODE_DIR/bin/node"
        NPM_CMD="$NODE_DIR/bin/npm"
    fi
fi
export PATH="$(dirname "$NODE_EXE"):$PATH"

if [ ! -d "$SCRIPT_DIR/frontend/node_modules/next" ]; then
    echo -e "${BLUE}📦 Đang cài đặt thư viện Frontend (npm install)...${NC}"
    (cd "$SCRIPT_DIR/frontend" && "$NPM_CMD" install) || {
        echo -e "${RED}❌ Lỗi khi chạy npm install cho Frontend.${NC}"
        read -r -p "Nhấn Enter để thoát..."
        exit 1
    }
fi

# 1d. Kiểm tra PostgreSQL 16 Native / Portable (bỏ qua nếu backend/.env đã trỏ DB ngoài như Neon)
EXISTING_DB_URL=""
if [ -f "$SCRIPT_DIR/backend/.env" ]; then
    EXISTING_DB_URL="$(grep -E "^DATABASE_URL=" "$SCRIPT_DIR/backend/.env" | head -n1 | cut -d'=' -f2- | tr -d '\r' | sed 's/^["'\'']//; s/["'\'']$//' | xargs || true)"
fi

USE_EXTERNAL_DB=0
if [ -n "$EXISTING_DB_URL" ] && ! echo "$EXISTING_DB_URL" | grep -qE "@(127\.0\.0\.1|localhost|db)(:|/)"; then
    USE_EXTERNAL_DB=1
fi

PG_CTL=""
INITDB=""
PG_ISREADY=""
PSQL=""
CREATEDB=""

if [ "$USE_EXTERNAL_DB" -eq 0 ]; then
    find_pg_bin() {
        for candidate in \
            "$PG_BIN" \
            "/opt/homebrew/opt/postgresql@16/bin" \
            "/usr/local/opt/postgresql@16/bin" \
            "/Applications/Postgres.app/Contents/Versions/16/bin" \
            "/Applications/Postgres.app/Contents/Versions/latest/bin"; do
            if [ -x "$candidate/pg_ctl" ] && [ -x "$candidate/initdb" ] && [ -x "$candidate/pg_isready" ]; then
                echo "$candidate"
                return 0
            fi
        done
        if command -v pg_ctl >/dev/null 2>&1 && command -v initdb >/dev/null 2>&1; then
            dirname "$(command -v pg_ctl)"
            return 0
        fi
        return 1
    }

    ACTIVE_PG_BIN="$(find_pg_bin || true)"
    if [ -z "$ACTIVE_PG_BIN" ]; then
        if command -v brew >/dev/null 2>&1; then
            echo -e "${BLUE}🍺 Đang cài đặt PostgreSQL 16 qua Homebrew...${NC}"
            brew install postgresql@16
            ACTIVE_PG_BIN="$(find_pg_bin || true)"
        else
            echo -e "${BLUE}⬇️  Đang tải PostgreSQL 16.4 Portable cho macOS...${NC}"
            pg_zip="/tmp/postgresql-16.4-1-osx-binaries.zip"
            if ! curl -fL --progress-bar "https://get.enterprisedb.com/postgresql/postgresql-16.4-1-osx-binaries.zip" -o "$pg_zip"; then
                echo -e "${RED}❌ Tải PostgreSQL thất bại. Bạn có thể cài Homebrew rồi chạy 'brew install postgresql@16'.${NC}"
                read -r -p "Nhấn Enter để thoát..."
                exit 1
            fi
            rm -rf "$PG_DIR"
            unzip -q -o "$pg_zip" "pgsql/bin/*" "pgsql/lib/*" "pgsql/share/*" -d "$TOOLS_DIR"
            xattr -dr com.apple.quarantine "$PG_DIR" 2>/dev/null || true
            rm -f "$pg_zip"
            ACTIVE_PG_BIN="$PG_BIN"
        fi
    fi

    if [ -z "$ACTIVE_PG_BIN" ] || [ ! -x "$ACTIVE_PG_BIN/pg_ctl" ]; then
        echo -e "${RED}❌ Không tìm thấy PostgreSQL (pg_ctl). Vui lòng cài postgresql@16 rồi thử lại.${NC}"
        read -r -p "Nhấn Enter để thoát..."
        exit 1
    fi

    PG_CTL="$ACTIVE_PG_BIN/pg_ctl"
    INITDB="$ACTIVE_PG_BIN/initdb"
    PG_ISREADY="$ACTIVE_PG_BIN/pg_isready"
    PSQL="$ACTIVE_PG_BIN/psql"
    CREATEDB="$ACTIVE_PG_BIN/createdb"
fi

# 1e. Đảm bảo thư mục dữ liệu & Symlink giống Docker (/app/data, /app/uploads, /app/eval_results)
mkdir -p \
    "$SCRIPT_DIR/data/knowledge/uploads" \
    "$SCRIPT_DIR/data/eval/results" \
    "$SCRIPT_DIR/chroma_data" \
    "$SCRIPT_DIR/postgres_data"

ensure_symlink() {
    local link_path="$1"
    local target_rel="$2"
    if [ -d "$link_path" ] && [ ! -L "$link_path" ]; then
        # Xoá thư mục rỗng nếu trước đó được tạo làm mountpoint cho Docker
        rmdir "$link_path" 2>/dev/null || true
    fi
    if [ ! -e "$link_path" ] && [ ! -L "$link_path" ]; then
        ln -s "$target_rel" "$link_path"
    fi
}

ensure_symlink "$SCRIPT_DIR/backend/data" "../data"
ensure_symlink "$SCRIPT_DIR/backend/uploads" "../data/knowledge/uploads"
ensure_symlink "$SCRIPT_DIR/backend/eval_results" "../data/eval/results"

echo -e "${GREEN}✅ Môi trường thực thi đã sẵn sàng!${NC}"
echo ""

# ------------------------------------------------------------------------------
# 2. Cấu hình biến môi trường (backend/.env)
# ------------------------------------------------------------------------------
ENV_FILE="$SCRIPT_DIR/backend/.env"
NEED_ENV_SETUP=0
EXISTING_SECRET=""
EXISTING_API_KEY=""
EXISTING_BOT_TOKEN=""

if [ -f "$ENV_FILE" ]; then
    EXISTING_SECRET="$(grep -E "^SECRET_KEY=" "$ENV_FILE" | head -n1 | cut -d'=' -f2- | tr -d '\r' | xargs || true)"
    EXISTING_API_KEY="$(grep -E "^GOOGLE_API_KEY=" "$ENV_FILE" | head -n1 | cut -d'=' -f2- | tr -d '\r' | xargs || true)"
    EXISTING_BOT_TOKEN="$(grep -E "^TELEGRAM_BOT_TOKEN=" "$ENV_FILE" | head -n1 | cut -d'=' -f2- | tr -d '\r' | xargs || true)"
fi

if [ -z "$EXISTING_SECRET" ] || [ -z "$EXISTING_API_KEY" ] || [ "$EXISTING_API_KEY" = "your-gemini-api-key-here" ]; then
    NEED_ENV_SETUP=1
fi

if [ "$NEED_ENV_SETUP" -eq 1 ]; then
    echo -e "${BLUE}${BOLD}🔧 Cấu hình môi trường lần đầu (backend/.env)${NC}"

    if [ -z "$EXISTING_SECRET" ]; then
        EXISTING_SECRET="$(openssl rand -hex 32)"
        echo -e "${GREEN}🔑 Đã tự động sinh SECRET_KEY bảo mật ngẫu nhiên.${NC}"
    fi

    while [ -z "$EXISTING_API_KEY" ] || [ "$EXISTING_API_KEY" = "your-gemini-api-key-here" ]; do
        echo -e "${YELLOW}👉 Dự án cần GOOGLE_API_KEY (Gemini API Key) lấy tại https://aistudio.google.com/apikey${NC}"
        read -r -p "Nhập GOOGLE_API_KEY của bạn (hoặc nhấn Enter để dùng khóa tạm test giao diện): " INPUT_KEY
        INPUT_KEY="$(echo "$INPUT_KEY" | xargs)"
        if [ -n "$INPUT_KEY" ]; then
            EXISTING_API_KEY="$INPUT_KEY"
        else
            EXISTING_API_KEY="your-gemini-api-key-here"
            echo -e "${YELLOW}⚠️  Đang dùng GOOGLE_API_KEY tạm thời (giao diện chạy bình thường, cần điền key thật vào backend/.env để chat AI).${NC}"
            break
        fi
    done

    {
        echo "# Cấu hình tự động sinh bởi run_mac_native.command"
        echo "# Lưu ý: Không để các dòng biến trống (key=) vì pydantic-settings sẽ báo lỗi."
        echo "SECRET_KEY=${EXISTING_SECRET}"
        echo "GOOGLE_API_KEY=${EXISTING_API_KEY}"
        echo 'BACKEND_CORS_ORIGINS=["http://localhost:3000"]'
        if [ -n "$EXISTING_BOT_TOKEN" ]; then
            echo "TELEGRAM_BOT_TOKEN=${EXISTING_BOT_TOKEN}"
        fi
    } > "$ENV_FILE"
    echo -e "${GREEN}✅ Đã lưu cấu hình chuẩn vào backend/.env!${NC}"
    echo ""
else
    echo -e "${GREEN}✅ Đã tìm thấy cấu hình hợp lệ tại backend/.env.${NC}"
    echo ""
fi

# Ghi đè cấu hình kết nối trong phiên chạy Native (chỉ ép Postgres cục bộ nếu backend/.env chưa dùng DB ngoài)
if [ "$USE_EXTERNAL_DB" -eq 0 ]; then
    export DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/fitai_db"
fi
export CHROMA_HOST="127.0.0.1"
export CHROMA_PORT="8001"

# Kiểm tra nếu Docker FitAI đang chạy và chiếm cổng
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^fitai_'; then
        echo -e "${YELLOW}⚠️  Phát hiện các container Docker FitAI đang chạy (có thể trùng cổng 3000, 8000, 8001).${NC}"
        read -r -p "Bạn có muốn dừng các container Docker FitAI trước khi chạy bản Native không? (Y/n): " STOP_DOCKER_ANS
        STOP_DOCKER_ANS="${STOP_DOCKER_ANS:-Y}"
        if [[ "$STOP_DOCKER_ANS" =~ ^[Yy]$ ]]; then
            docker compose down
            echo ""
        fi
    fi
fi

# ------------------------------------------------------------------------------
# 3. Khởi động các dịch vụ (PostgreSQL, ChromaDB, Backend, Frontend)
# ------------------------------------------------------------------------------
echo -e "${BLUE}${BOLD}🚀 Đang khởi chạy các dịch vụ (PostgreSQL, ChromaDB, Backend, Frontend)...${NC}"

# 3a. PostgreSQL (port 5432 hoặc DB ngoài như Neon)
PG_DATA="$SCRIPT_DIR/postgres_data"
PG_LOG="/tmp/fitai_postgres.log"
if [ "$USE_EXTERNAL_DB" -eq 1 ]; then
    echo "   [1/4] PostgreSQL: Dùng database ngoài từ backend/.env (Neon/Cloud)..."
else
    if [ ! -f "$PG_DATA/PG_VERSION" ]; then
        echo -e "${BLUE}🗄️  Khởi tạo cụm dữ liệu PostgreSQL lần đầu...${NC}"
        PW_FILE="/tmp/fitai_pgpass_$$.txt"
        printf "postgres" > "$PW_FILE"
        if ! "$INITDB" -D "$PG_DATA" -U postgres -E UTF8 --locale=C -A scram-sha-256 --pwfile="$PW_FILE" >/dev/null; then
            rm -f "$PW_FILE"
            echo -e "${RED}❌ Khởi tạo PostgreSQL thất bại.${NC}"
            read -r -p "Nhấn Enter để thoát..."
            exit 1
        fi
        rm -f "$PW_FILE"
    fi

    echo "   [1/4] PostgreSQL (port 5432)..."
    if ! "$PG_ISREADY" -h 127.0.0.1 -p 5432 -U postgres >/dev/null 2>&1; then
        if [ -f "$PG_DATA/postmaster.pid" ]; then
            PID_PG="$(head -n1 "$PG_DATA/postmaster.pid" 2>/dev/null || true)"
            if [ -z "$PID_PG" ] || ! kill -0 "$PID_PG" 2>/dev/null; then
                rm -f "$PG_DATA/postmaster.pid"
            fi
        fi
        "$PG_CTL" -D "$PG_DATA" -l "$PG_LOG" -o "-p 5432 -h 127.0.0.1" start >/dev/null 2>&1 || true
        for _ in {1..30}; do
            if "$PG_ISREADY" -h 127.0.0.1 -p 5432 -U postgres >/dev/null 2>&1; then
                break
            fi
            sleep 0.5
        done
    fi

    export PGPASSWORD="postgres"
    DB_EXISTS="$("$PSQL" -h 127.0.0.1 -p 5432 -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='fitai_db'" 2>/dev/null | xargs || true)"
    if [ "$DB_EXISTS" != "1" ]; then
        "$CREATEDB" -h 127.0.0.1 -p 5432 -U postgres fitai_db
    fi
fi

# 3b. ChromaDB (port 8001)
echo "   [2/4] ChromaDB (port 8001)..."
CHROMA_LOG="/tmp/fitai_chroma.log"
if ! lsof -iTCP:8001 -sTCP:LISTEN -n -P >/dev/null 2>&1; then
    nohup "$CHROMA_EXE" run --host 127.0.0.1 --port 8001 --path "$SCRIPT_DIR/chroma_data" > "$CHROMA_LOG" 2>&1 < /dev/null &
fi

# 3c. FastAPI Backend (port 8000)
echo "   [3/4] FastAPI Backend (port 8000)..."
BACKEND_LOG="/tmp/fitai_backend.log"
if ! lsof -iTCP:8000 -sTCP:LISTEN -n -P >/dev/null 2>&1; then
    (
        cd "$SCRIPT_DIR/backend" || exit 1
        nohup "$UVICORN" main:app --host 0.0.0.0 --port 8000 --reload --reload-dir api --reload-dir core --reload-dir models --reload-dir services > "$BACKEND_LOG" 2>&1 < /dev/null &
    )
fi

# 3d. Next.js Frontend (port 3000)
echo "   [4/4] Next.js Frontend (port 3000)..."
FRONTEND_LOG="/tmp/fitai_frontend.log"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
export NEXT_PUBLIC_API_URL="http://localhost:8000/api/v1"
if ! lsof -iTCP:3000 -sTCP:LISTEN -n -P >/dev/null 2>&1; then
    if [ ! -f "$FRONTEND_DIR/.next/BUILD_ID" ]; then
        echo -e "${BLUE}   🔨 Đang biên dịch bản tối ưu Frontend lần đầu (chỉ mất ~15 giây)...${NC}"
        (cd "$FRONTEND_DIR" && "$NPM_CMD" run build >/dev/null)
    fi
    (
        cd "$FRONTEND_DIR" || exit 1
        nohup "$NPM_CMD" run start > "$FRONTEND_LOG" 2>&1 < /dev/null &
    )
fi

# 3e. Telegram Bot (tùy chọn — chỉ chạy khi có TELEGRAM_BOT_TOKEN trong backend/.env)
BOT_LOG="/tmp/fitai_telegram_bot.log"
if [ -n "$EXISTING_BOT_TOKEN" ]; then
    echo "   [5/5] Telegram Bot (Long Polling)..."
    if ! pgrep -f "scripts.run_telegram_bot" >/dev/null 2>&1; then
        (
            cd "$SCRIPT_DIR/backend" || exit 1
            nohup "$VENV_PY" -m scripts.run_telegram_bot > "$BOT_LOG" 2>&1 < /dev/null &
        )
    fi
fi

echo -e "${BLUE}⏳ Đang đợi Backend khởi động và kết nối Database...${NC}"
for _ in {1..30}; do
    if curl -fsS --max-time 2 http://127.0.0.1:8000/health 2>/dev/null | grep -q '"ok"'; then
        break
    fi
    sleep 2
done
echo -e "${GREEN}✅ Các dịch vụ FitAI đã chạy!${NC}"
echo ""

# ------------------------------------------------------------------------------
# 4. Chạy Migration (Alembic)
# ------------------------------------------------------------------------------
echo -e "${BLUE}${BOLD}🗄️  Đang cập nhật cấu trúc bảng dữ liệu (Alembic migration)...${NC}"
(cd "$SCRIPT_DIR/backend" && "$ALEMBIC" upgrade head)
echo ""

# ------------------------------------------------------------------------------
# 5. Kiểm tra & Nạp dữ liệu khởi tạo (Idempotent — chỉ nạp khi chưa có hoặc cần)
# ------------------------------------------------------------------------------
DB_COUNTS="$(cd "$SCRIPT_DIR/backend" && "$VENV_PY" - <<'PYEOF' 2>/dev/null | tail -n 1
import asyncio
from sqlalchemy import func, select
from core.database import AsyncSessionLocal, engine
from models.food import Food
from models.training import TrainingProgram
from models.user import User, UserRole

async def check():
    try:
        async with AsyncSessionLocal() as s:
            foods = (await s.execute(select(func.count()).select_from(Food))).scalar_one()
            progs = (await s.execute(select(func.count()).select_from(TrainingProgram))).scalar_one()
            admin = (await s.execute(select(User.email).where(User.role == UserRole.ADMIN).limit(1))).scalar_one_or_none()
            print(f'{foods}|{progs}|{admin or ""}')
    finally:
        await engine.dispose()

asyncio.run(check())
PYEOF
)"

FOOD_COUNT="$(echo "$DB_COUNTS" | cut -d'|' -f1)"
PROG_COUNT="$(echo "$DB_COUNTS" | cut -d'|' -f2)"
ADMIN_EMAIL="$(echo "$DB_COUNTS" | cut -d'|' -f3)"

FOOD_COUNT="${FOOD_COUNT:-0}"
PROG_COUNT="${PROG_COUNT:-0}"

if [ "$FOOD_COUNT" -eq 0 ] 2>/dev/null; then
    echo -e "${BLUE}${BOLD}🥗 Đang nạp dữ liệu thực phẩm Việt Nam 2007 & USDA...${NC}"
    (
        cd "$SCRIPT_DIR/backend" || exit 1
        "$VENV_PY" scripts/ingest_foods.py
        "$VENV_PY" scripts/ingest_usda_foods.py
    )
    echo ""
else
    echo -e "${GREEN}✅ Bảng thực phẩm đã có dữ liệu (${FOOD_COUNT} món). Bỏ qua nạp lại.${NC}"
fi

if [ "$PROG_COUNT" -eq 0 ] 2>/dev/null; then
    echo -e "${BLUE}${BOLD}🏋️  Đang nạp chương trình tập luyện mẫu...${NC}"
    (cd "$SCRIPT_DIR/backend" && "$VENV_PY" scripts/seed_training.py)
    echo ""
else
    echo -e "${GREEN}✅ Chương trình tập luyện đã có dữ liệu (${PROG_COUNT} chương trình). Bỏ qua nạp lại.${NC}"
fi

# Kiểm tra tài khoản Admin và 70 món ăn chế biến (ADMIN_MANUAL)
if [ -z "$ADMIN_EMAIL" ]; then
    echo ""
    echo -e "${YELLOW}👤 Chưa có tài khoản Quản trị viên (Admin).${NC}"
    read -r -p "Bạn có muốn tạo nhanh tài khoản Admin & nạp thêm 70 món ăn chế biến sẵn không? (Y/n): " MAKE_ADMIN_ANS
    MAKE_ADMIN_ANS="${MAKE_ADMIN_ANS:-Y}"
    if [[ "$MAKE_ADMIN_ANS" =~ ^[Yy]$ ]]; then
        read -r -p "   Nhập email Admin (mặc định: admin@fitai.local): " INPUT_ADMIN_EMAIL
        INPUT_ADMIN_EMAIL="${INPUT_ADMIN_EMAIL:-admin@fitai.local}"
        read -r -p "   Nhập mật khẩu Admin (mặc định: Admin@123456): " INPUT_ADMIN_PASS
        INPUT_ADMIN_PASS="${INPUT_ADMIN_PASS:-Admin@123456}"

        (
            cd "$SCRIPT_DIR/backend" || exit 1
            FITAI_INIT_ADMIN_EMAIL="$INPUT_ADMIN_EMAIL" FITAI_INIT_ADMIN_PASS="$INPUT_ADMIN_PASS" "$VENV_PY" - <<'PYEOF'
import asyncio, os
from sqlalchemy import func, select
from core.database import AsyncSessionLocal, engine
from core.security import get_password_hash
from models.user import User, UserRole
from models.profile import UserProfile

async def ensure_user():
    email = os.environ['FITAI_INIT_ADMIN_EMAIL'].strip()
    pwd = os.environ['FITAI_INIT_ADMIN_PASS']
    try:
        async with AsyncSessionLocal() as s:
            async with s.begin():
                u = (await s.execute(select(User).where(func.lower(User.email) == email.lower()))).scalar_one_or_none()
                if not u:
                    u = User(email=email, hashed_password=get_password_hash(pwd), full_name='FitAI Admin', is_active=True, role=UserRole.USER)
                    s.add(u)
                    await s.flush()
                    s.add(UserProfile(user_id=u.id))
    finally:
        await engine.dispose()

asyncio.run(ensure_user())
PYEOF
            "$VENV_PY" scripts/make_admin.py "$INPUT_ADMIN_EMAIL"
            echo -e "${BLUE}🍲 Đang nạp 70 món ăn chế biến, đồ uống và thực phẩm cơ bản...${NC}"
            "$VENV_PY" scripts/import_admin_foods.py --admin-email "$INPUT_ADMIN_EMAIL"
            "$VENV_PY" scripts/import_admin_foods.py --admin-email "$INPUT_ADMIN_EMAIL" --file data/foods/manual/dishes_all.csv --update-existing
        )
        echo -e "${GREEN}✅ Đã tạo tài khoản Admin (${INPUT_ADMIN_EMAIL}) và nạp đủ 70 món ăn!${NC}"
    fi
else
    echo -e "${GREEN}✅ Đã có tài khoản Admin (${ADMIN_EMAIL}).${NC}"
fi

# Kiểm tra dữ liệu RAG trong ChromaDB
CHROMA_COUNT="$(cd "$SCRIPT_DIR/backend" && "$VENV_PY" - <<'PYEOF' 2>/dev/null | tail -n 1
from core.config import settings
from services.knowledge.vector_store import get_client, open_collection
try:
    col = open_collection(get_client(), settings.CHROMA_COLLECTION_NAME, settings.EMBEDDING_MODEL, reset=False)
    print(col.count())
except Exception:
    print(0)
PYEOF
)"
CHROMA_COUNT="${CHROMA_COUNT:-0}"

if [ "$CHROMA_COUNT" -eq 0 ] 2>/dev/null; then
    echo ""
    echo -e "${YELLOW}📚 Kho tri thức RAG (ChromaDB) hiện đang trống (0 đoạn).${NC}"
    echo -e "   Việc nạp tài liệu ISSN & WHO (134 đoạn) sẽ gọi Gemini Embedding API."
    read -r -p "Bạn có muốn nạp tài liệu RAG vào ChromaDB ngay bây giờ không? (y/N): " RAG_ANS
    RAG_ANS="${RAG_ANS:-N}"
    if [[ "$RAG_ANS" =~ ^[Yy]$ ]]; then
        (cd "$SCRIPT_DIR/backend" && "$VENV_PY" scripts/ingest_knowledge.py) || true
    fi
else
    echo -e "${GREEN}✅ Kho tri thức RAG (ChromaDB) đã có ${CHROMA_COUNT} đoạn văn bản.${NC}"
fi

# ------------------------------------------------------------------------------
# 6. Hoàn tất & Mở trình duyệt
# ------------------------------------------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}==============================================================${NC}"
echo -e "${GREEN}${BOLD}🎉 FitAI đã khởi động thành công trên máy Mac của bạn!${NC}"
echo -e "${GREEN}${BOLD}==============================================================${NC}"
echo -e "🌐 Giao diện Web (Frontend): ${BOLD}http://localhost:3000${NC}"
echo -e "⚙️  Tài liệu API (Swagger):   ${BOLD}http://localhost:8000/api/v1/docs${NC}"
echo -e "❤️  Kiểm tra Health:          ${BOLD}http://localhost:8000/health${NC}"
echo ""
echo -e "💡 Đang tự động mở trình duyệt tới ${BOLD}http://localhost:3000${NC} ..."
open "http://localhost:3000" >/dev/null 2>&1 || true

echo ""
echo -e "${YELLOW}Tuỳ chọn nhanh:${NC}"
echo -e "  - Nhấn ${BOLD}Enter${NC} để đóng cửa sổ này (ứng dụng vẫn tiếp tục chạy ngầm)."
echo -e "  - Gõ ${BOLD}admin${NC} rồi nhấn Enter để cấp quyền Admin cho một email."
echo -e "  - Gõ ${BOLD}logs${NC} rồi nhấn Enter để xem log trực tiếp của Backend."
echo -e "  - Gõ ${BOLD}stop${NC} rồi nhấn Enter để tắt toàn bộ các dịch vụ FitAI."
read -r -p "Lựa chọn của bạn [Enter/admin/logs/stop]: " ACTION_ANS
ACTION_ANS="$(echo "$ACTION_ANS" | xargs | tr '[:upper:]' '[:lower:]')"

case "$ACTION_ANS" in
    admin)
        read -r -p "Nhập email tài khoản cần cấp quyền Admin: " TARGET_EMAIL
        TARGET_EMAIL="$(echo "$TARGET_EMAIL" | xargs)"
        if [ -n "$TARGET_EMAIL" ]; then
            (cd "$SCRIPT_DIR/backend" && "$VENV_PY" scripts/make_admin.py "$TARGET_EMAIL")
        fi
        read -r -p "Nhấn Enter để thoát..."
        ;;
    logs)
        echo -e "${BLUE}📋 Đang hiển thị log Backend (Nhấn Ctrl+C để thoát)...${NC}"
        if [ -f "$BACKEND_LOG" ]; then
            tail -n 40 -f "$BACKEND_LOG"
        else
            echo -e "${YELLOW}Chưa có file log tại $BACKEND_LOG${NC}"
        fi
        ;;
    stop)
        echo -e "${YELLOW}🛑 Đang dừng các dịch vụ FitAI...${NC}"
        pkill -f "uvicorn main:app" 2>/dev/null || true
        pkill -f "scripts.run_telegram_bot" 2>/dev/null || true
        for port in 3000 8000 8001; do
            pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
            if [ -n "$pids" ]; then
                # shellcheck disable=SC2086
                kill $pids 2>/dev/null || true
            fi
        done
        sleep 1
        for port in 3000 8000 8001; do
            pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
            if [ -n "$pids" ]; then
                # shellcheck disable=SC2086
                kill -9 $pids 2>/dev/null || true
            fi
        done
        if [ -n "$PG_CTL" ] && [ -f "$PG_DATA/postmaster.pid" ]; then
            "$PG_CTL" -D "$PG_DATA" stop -m fast >/dev/null 2>&1 || true
        fi
        echo -e "${GREEN}✅ Đã dừng toàn bộ dịch vụ.${NC}"
        sleep 1
        ;;
    *)
        echo -e "${GREEN}👋 Chúc bạn trải nghiệm FitAI vui vẻ!${NC}"
        sleep 1
        ;;
esac
