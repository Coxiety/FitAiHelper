#!/bin/bash
# ==============================================================================
# FitAI — Script khởi chạy tự động bằng 1 cú nhấp đúp trên macOS (.command)
# Bản Docker Compose — đồng bộ tính năng với run_windows.bat.
# ==============================================================================

set -u

# Chuyển về thư mục gốc của project (nơi chứa file .command này)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Bổ sung PATH phổ biến trên macOS (Apple Silicon & Intel & Docker Desktop)
export PATH="/opt/homebrew/bin:/usr/local/bin:/Applications/Docker.app/Contents/Resources/bin:$HOME/.local/bin:$PATH"

# Màu sắc hiển thị trên Terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BLUE}${BOLD}==============================================================${NC}"
echo -e "${BLUE}${BOLD}       🚀 FitAI — Khởi động tự động trên macOS (Docker)       ${NC}"
echo -e "${BLUE}${BOLD}==============================================================${NC}"
echo ""

# ------------------------------------------------------------------------------
# 1. Kiểm tra & cài đặt / khởi động Docker Desktop
# ------------------------------------------------------------------------------
install_docker_mac() {
    local arch
    arch="$(uname -m)"
    local dmg_url="https://desktop.docker.com/mac/main/arm64/Docker.dmg"
    if [ "$arch" = "x86_64" ]; then
        dmg_url="https://desktop.docker.com/mac/main/amd64/Docker.dmg"
    fi

    local dmg_path="/tmp/Docker.dmg"
    echo -e "${BLUE}⬇️  Đang tải Docker Desktop cho macOS ($arch)...${NC}"
    if ! curl -fL --progress-bar "$dmg_url" -o "$dmg_path"; then
        echo -e "${RED}❌ Tải Docker Desktop thất bại. Vui lòng kiểm tra kết nối mạng hoặc tải tại: https://www.docker.com/products/docker-desktop/${NC}"
        return 1
    fi

    echo -e "${BLUE}💿 Đang gắn kết (mount) bộ cài Docker.dmg...${NC}"
    hdiutil attach "$dmg_path" -nobrowse -quiet
    if [ -d "/Volumes/Docker/Docker.app" ]; then
        echo -e "${BLUE}📦 Đang chép Docker.app vào /Applications (có thể hỏi mật khẩu máy Mac)...${NC}"
        cp -R "/Volumes/Docker/Docker.app" /Applications/ 2>/dev/null || sudo cp -R "/Volumes/Docker/Docker.app" /Applications/
        hdiutil detach "/Volumes/Docker" -quiet || true
        rm -f "$dmg_path"
        echo -e "${GREEN}✅ Đã cài đặt Docker Desktop vào /Applications/Docker.app!${NC}"
        return 0
    else
        echo -e "${RED}❌ Không tìm thấy Docker.app trong bộ cài.${NC}"
        return 1
    fi
}

if ! command -v docker >/dev/null 2>&1 && [ ! -d "/Applications/Docker.app" ]; then
    echo -e "${YELLOW}⚠️  Máy Mac của bạn chưa cài đặt Docker Desktop.${NC}"
    read -r -p "Bạn có muốn tự động tải và cài đặt Docker Desktop ngay bây giờ không? (Y/n): " ans
    ans="${ans:-Y}"
    if [[ "$ans" =~ ^[Yy]$ ]]; then
        install_docker_mac || {
            read -r -p "Nhấn Enter để thoát..."
            exit 1
        }
    else
        echo -e "${YELLOW}👉 Vui lòng cài đặt Docker Desktop từ https://www.docker.com/products/docker-desktop/ rồi chạy lại file này.${NC}"
        read -r -p "Nhấn Enter để thoát..."
        exit 1
    fi
fi

# Đảm bảo lệnh docker có trong PATH sau khi cài
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

if ! docker info >/dev/null 2>&1; then
    echo -e "${YELLOW}⏳ Docker daemon chưa chạy. Đang mở ứng dụng Docker Desktop...${NC}"
    open -a Docker
    echo -e "${YELLOW}   (Nếu đây là lần đầu mở Docker Desktop, hãy bấm 'Accept' trên cửa sổ Docker hiện ra)${NC}"
    printf "   Đang đợi Docker sẵn sàng"
    while ! docker info >/dev/null 2>&1; do
        printf "."
        sleep 3
    done
    echo ""
fi
echo -e "${GREEN}✅ Docker đã sẵn sàng!${NC}"
echo ""

# Nếu trước đó đã chạy bản Native (run_mac_native.command), dọn symlink mountpoint để Docker mount sạch
for link_dir in "backend/data" "backend/uploads" "backend/eval_results"; do
    if [ -L "$link_dir" ]; then
        rm -f "$link_dir"
    fi
done

# Kiểm tra xung đột cổng từ tiến trình ngoài Docker (nếu có)
for p in 3000 8000 8001; do
    non_docker_pids="$(lsof -iTCP:"$p" -sTCP:LISTEN -n -P 2>/dev/null | awk 'NR>1 && $1 !~ /^com\.docke/ {print $2}' | sort -u || true)"
    if [ -n "$non_docker_pids" ]; then
        echo -e "${YELLOW}⚠️  Phát hiện tiến trình ngoài Docker đang chiếm cổng ${p} (PID: ${non_docker_pids//$'\n'/, }).${NC}"
        read -r -p "Bạn có muốn dừng tiến trình đó để tránh xung đột cổng với Docker không? (Y/n): " KILL_CONFLICT
        KILL_CONFLICT="${KILL_CONFLICT:-Y}"
        if [[ "$KILL_CONFLICT" =~ ^[Yy]$ ]]; then
            # shellcheck disable=SC2086
            kill $non_docker_pids 2>/dev/null || true
            sleep 1
        fi
    fi
done

# ------------------------------------------------------------------------------
# 2. Cấu hình biến môi trường (backend/.env)
# ------------------------------------------------------------------------------
ENV_FILE="backend/.env"
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
        echo "# Cấu hình tự động sinh bởi run_mac.command"
        echo "# Lưu ý: Không để các dòng biến trống (key=) vì pydantic-settings sẽ báo lỗi."
        echo "SECRET_KEY=${EXISTING_SECRET}"
        echo "GOOGLE_API_KEY=${EXISTING_API_KEY}"
        echo 'BACKEND_CORS_ORIGINS=["http://localhost:3000"]'
        if [ -n "$EXISTING_BOT_TOKEN" ]; then
            echo "TELEGRAM_BOT_TOKEN=${EXISTING_BOT_TOKEN}"
        fi
    } > "$ENV_FILE"
    echo -e "${GREEN}✅ Đã lưu cấu hình chuẩn vào ${ENV_FILE}!${NC}"
    echo ""
else
    echo -e "${GREEN}✅ Đã tìm thấy cấu hình hợp lệ tại ${ENV_FILE}.${NC}"
    echo ""
fi

# ------------------------------------------------------------------------------
# 3. Khởi động các container qua Docker Compose
# ------------------------------------------------------------------------------
echo -e "${BLUE}${BOLD}🐳 Đang dựng và khởi chạy các container (Frontend, Backend, PostgreSQL, ChromaDB)...${NC}"
if ! docker compose up -d --build; then
    echo -e "${RED}❌ Lỗi khi chạy 'docker compose up -d --build'. Vui lòng kiểm tra thông báo lỗi phía trên.${NC}"
    read -r -p "Nhấn Enter để thoát..."
    exit 1
fi

# Khởi chạy Telegram Bot (tùy chọn — chỉ chạy khi có TELEGRAM_BOT_TOKEN trong backend/.env)
if [ -n "$EXISTING_BOT_TOKEN" ]; then
    BOT_RUNNING="$(docker compose exec -T backend python -c "
import glob
found = False
for p in glob.glob('/proc/[0-9]*/cmdline'):
    try:
        with open(p, 'rb') as f:
            if b'scripts.run_telegram_bot' in f.read():
                found = True
                break
    except Exception:
        pass
print('1' if found else '0')
" 2>/dev/null | tail -n 1)"
    if [ "$BOT_RUNNING" != "1" ]; then
        echo -e "${BLUE}🤖 Đang khởi chạy Telegram Bot (Long Polling)...${NC}"
        docker compose exec -d -T backend python -m scripts.run_telegram_bot >/dev/null 2>&1 || true
    fi
fi

echo -e "${BLUE}⏳ Đang đợi Backend khởi động và kết nối Database...${NC}"
for _ in {1..30}; do
    if curl -fsS --max-time 2 http://127.0.0.1:8000/health 2>/dev/null | grep -q '"ok"'; then
        break
    fi
    sleep 2
done
echo -e "${GREEN}✅ Các dịch vụ Docker đã chạy!${NC}"
echo ""

# ------------------------------------------------------------------------------
# 4. Chạy Migration (Alembic)
# ------------------------------------------------------------------------------
echo -e "${BLUE}${BOLD}🗄️  Đang cập nhật cấu trúc bảng dữ liệu (Alembic migration)...${NC}"
docker compose exec -T backend alembic upgrade head
echo ""

# ------------------------------------------------------------------------------
# 5. Kiểm tra & Nạp dữ liệu khởi tạo (Idempotent — chỉ nạp khi chưa có hoặc cần)
# ------------------------------------------------------------------------------
DB_COUNTS="$(docker compose exec -T backend python -c "
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
            print(f'{foods}|{progs}|{admin or \"\"}')
    finally:
        await engine.dispose()

asyncio.run(check())
" 2>/dev/null | tail -n 1)"

FOOD_COUNT="$(echo "$DB_COUNTS" | cut -d'|' -f1)"
PROG_COUNT="$(echo "$DB_COUNTS" | cut -d'|' -f2)"
ADMIN_EMAIL="$(echo "$DB_COUNTS" | cut -d'|' -f3)"

FOOD_COUNT="${FOOD_COUNT:-0}"
PROG_COUNT="${PROG_COUNT:-0}"

if [ "$FOOD_COUNT" -eq 0 ] 2>/dev/null; then
    echo -e "${BLUE}${BOLD}🥗 Đang nạp dữ liệu thực phẩm Việt Nam 2007 & USDA...${NC}"
    docker compose exec -T backend python scripts/ingest_foods.py
    docker compose exec -T backend python scripts/ingest_usda_foods.py
    echo ""
else
    echo -e "${GREEN}✅ Bảng thực phẩm đã có dữ liệu (${FOOD_COUNT} món). Bỏ qua nạp lại.${NC}"
fi

if [ "$PROG_COUNT" -eq 0 ] 2>/dev/null; then
    echo -e "${BLUE}${BOLD}🏋️  Đang nạp chương trình tập luyện mẫu...${NC}"
    docker compose exec -T backend python scripts/seed_training.py
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

        docker compose exec -T \
            -e FITAI_INIT_ADMIN_EMAIL="$INPUT_ADMIN_EMAIL" \
            -e FITAI_INIT_ADMIN_PASS="$INPUT_ADMIN_PASS" \
            backend python -c "
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
"
        docker compose exec -T backend python scripts/make_admin.py "$INPUT_ADMIN_EMAIL"
        echo -e "${BLUE}🍲 Đang nạp 70 món ăn chế biến, đồ uống và thực phẩm cơ bản...${NC}"
        docker compose exec -T backend python scripts/import_admin_foods.py --admin-email "$INPUT_ADMIN_EMAIL"
        docker compose exec -T backend python scripts/import_admin_foods.py --admin-email "$INPUT_ADMIN_EMAIL" --file /app/data/foods/manual/dishes_all.csv --update-existing
        echo -e "${GREEN}✅ Đã tạo tài khoản Admin (${INPUT_ADMIN_EMAIL}) và nạp đủ 70 món ăn!${NC}"
    fi
else
    echo -e "${GREEN}✅ Đã có tài khoản Admin (${ADMIN_EMAIL}).${NC}"
fi

# Kiểm tra dữ liệu RAG trong ChromaDB
CHROMA_COUNT="$(docker compose exec -T backend python -c "
from core.config import settings
from services.knowledge.vector_store import get_client, open_collection
try:
    col = open_collection(get_client(), settings.CHROMA_COLLECTION_NAME, settings.EMBEDDING_MODEL, reset=False)
    print(col.count())
except Exception:
    print(0)
" 2>/dev/null | tail -n 1)"
CHROMA_COUNT="${CHROMA_COUNT:-0}"

if [ "$CHROMA_COUNT" -eq 0 ] 2>/dev/null; then
    echo ""
    echo -e "${YELLOW}📚 Kho tri thức RAG (ChromaDB) hiện đang trống (0 đoạn).${NC}"
    echo -e "   Việc nạp tài liệu ISSN & WHO (134 đoạn) sẽ gọi Gemini Embedding API."
    read -r -p "Bạn có muốn nạp tài liệu RAG vào ChromaDB ngay bây giờ không? (y/N): " RAG_ANS
    RAG_ANS="${RAG_ANS:-N}"
    if [[ "$RAG_ANS" =~ ^[Yy]$ ]]; then
        docker compose exec -T backend python scripts/ingest_knowledge.py || true
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
echo -e "  - Nhấn ${BOLD}Enter${NC} để đóng cửa sổ này (ứng dụng vẫn tiếp tục chạy ngầm trong Docker)."
echo -e "  - Gõ ${BOLD}admin${NC} rồi nhấn Enter để cấp quyền Admin cho một email."
echo -e "  - Gõ ${BOLD}logs${NC} rồi nhấn Enter để xem log trực tiếp."
echo -e "  - Gõ ${BOLD}stop${NC} rồi nhấn Enter để tắt toàn bộ các container FitAI."
read -r -p "Lựa chọn của bạn [Enter/admin/logs/stop]: " ACTION_ANS
ACTION_ANS="$(echo "$ACTION_ANS" | xargs | tr '[:upper:]' '[:lower:]')"

case "$ACTION_ANS" in
    admin)
        read -r -p "Nhập email tài khoản cần cấp quyền Admin: " TARGET_EMAIL
        TARGET_EMAIL="$(echo "$TARGET_EMAIL" | xargs)"
        if [ -n "$TARGET_EMAIL" ]; then
            docker compose exec -T backend python scripts/make_admin.py "$TARGET_EMAIL"
        fi
        read -r -p "Nhấn Enter để thoát..."
        ;;
    logs)
        docker compose logs -f
        ;;
    stop)
        echo -e "${YELLOW}🛑 Đang dừng các container FitAI...${NC}"
        docker compose down
        echo -e "${GREEN}✅ Đã dừng toàn bộ dịch vụ.${NC}"
        ;;
    *)
        echo -e "${GREEN}👋 Chúc bạn trải nghiệm FitAI vui vẻ!${NC}"
        ;;
esac
