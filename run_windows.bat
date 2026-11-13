@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$f='%~f0'; $c=Get-Content -LiteralPath $f -Encoding UTF8; $p=Join-Path $env:TEMP 'fitai_run.ps1'; Set-Content -LiteralPath $p -Value $c[3..9999] -Encoding UTF8; powershell -NoProfile -ExecutionPolicy Bypass -File $p" & exit /b
# ==============================================================================
# FitAI — Script khởi chạy tự động bằng 1 cú nhấp đúp trên Windows (.bat)
# Tương đương hoàn toàn với run_mac.command (Tự động cài đặt & chạy toàn bộ dịch vụ)
# ==============================================================================

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$SCRIPT_DIR = (Get-Location).Path
$TOOLS_DIR = "D:\Coding Enviroment"
if (-not (Test-Path $TOOLS_DIR)) {
    $TOOLS_DIR = Join-Path $env:LOCALAPPDATA "FitAI_Tools"
    New-Item -ItemType Directory -Force -Path $TOOLS_DIR | Out-Null
}

$NODE_DIR   = Join-Path $TOOLS_DIR "nodejs"
$PG_DIR     = Join-Path $TOOLS_DIR "pgsql"
$PG_BIN     = Join-Path $PG_DIR "bin"
$CHROMA_ENV = Join-Path $TOOLS_DIR "chromadb_env"
$PY313_DIR  = Join-Path $TOOLS_DIR "Python313"

$env:PATH = "$NODE_DIR;$PG_BIN;$CHROMA_ENV\Scripts;$PY313_DIR;$PY313_DIR\Scripts;$env:LOCALAPPDATA\Microsoft\WindowsApps;$env:USERPROFILE\.local\bin;$env:PATH"

$ESC    = [char]27
$GREEN  = "$ESC[0;32m"
$BLUE   = "$ESC[0;34m"
$YELLOW = "$ESC[1;33m"
$RED    = "$ESC[0;31m"
$BOLD   = "$ESC[1m"
$NC     = "$ESC[0m"

Write-Host "${BLUE}${BOLD}==============================================================${NC}"
Write-Host "${BLUE}${BOLD}      🚀 FitAI — Khởi động tự động trên Windows (All-in-One)  ${NC}"
Write-Host "${BLUE}${BOLD}==============================================================${NC}"
Write-Host ""

# ------------------------------------------------------------------------------
# 1. Kiểm tra & Tự động thiết lập môi trường (Python 3.11, Node.js, PostgreSQL, ChromaDB)
# ------------------------------------------------------------------------------
Write-Host "${BLUE}${BOLD}🔍 Đang kiểm tra các thành phần hệ thống...${NC}"

# 1a. Kiểm tra uv & Python 3.11 + backend/.venv
$VENV_PY = Join-Path $SCRIPT_DIR "backend\.venv\Scripts\python.exe"
$ALEMBIC = Join-Path $SCRIPT_DIR "backend\.venv\Scripts\alembic.exe"
$UVICORN = Join-Path $SCRIPT_DIR "backend\.venv\Scripts\uvicorn.exe"

if (-not (Test-Path $VENV_PY)) {
    Write-Host "${YELLOW}⚙️  Đang thiết lập môi trường Python 3.11 cho Backend (backend/.venv)...${NC}"
    $uvCmd = Get-Command uv.exe -ErrorAction SilentlyContinue
    if (-not $uvCmd) {
        python -m pip install uv --quiet
    }
    uv python install 3.11
    uv venv --python 3.11 (Join-Path $SCRIPT_DIR "backend\.venv")
    uv pip install --python $VENV_PY -r (Join-Path $SCRIPT_DIR "backend\requirements.txt")
}

# 1b. Kiểm tra ChromaDB 1.5.9
$CHROMA_EXE = Join-Path $CHROMA_ENV "Scripts\chroma.exe"
if (-not (Test-Path $CHROMA_EXE)) {
    Write-Host "${YELLOW}⚙️  Đang cài đặt ChromaDB 1.5.9 Server...${NC}"
    uv venv --python 3.11 $CHROMA_ENV
    uv pip install --python (Join-Path $CHROMA_ENV "Scripts\python.exe") "chromadb==1.5.9"
}

# 1c. Kiểm tra Node.js & frontend/node_modules
$NODE_EXE = Join-Path $NODE_DIR "node.exe"
$NPM_CMD  = Join-Path $NODE_DIR "npm.cmd"
if (-not (Test-Path $NODE_EXE)) {
    $sysNode = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($sysNode) {
        $NODE_EXE = $sysNode.Source
        $NPM_CMD  = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
    } else {
        Write-Host "${BLUE}⬇️  Đang tải Node.js v22.14.0 Portable cho Windows...${NC}"
        $nodeZip = Join-Path $env:TEMP "node-v22.14.0-win-x64.zip"
        curl.exe -L --progress-bar -o $nodeZip "https://nodejs.org/dist/v22.14.0/node-v22.14.0-win-x64.zip"
        Expand-Archive -Path $nodeZip -DestinationPath $TOOLS_DIR -Force
        if (Test-Path $NODE_DIR) { Remove-Item $NODE_DIR -Recurse -Force }
        Rename-Item (Join-Path $TOOLS_DIR "node-v22.14.0-win-x64") $NODE_DIR
        Remove-Item $nodeZip -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path (Join-Path $SCRIPT_DIR "frontend\node_modules\next"))) {
    Write-Host "${BLUE}📦 Đang cài đặt thư viện Frontend (npm install)...${NC}"
    Push-Location (Join-Path $SCRIPT_DIR "frontend")
    & $NPM_CMD install
    Pop-Location
}

# 1d. Kiểm tra PostgreSQL 16 Portable
$PG_CTL = Join-Path $PG_BIN "pg_ctl.exe"
if (-not (Test-Path $PG_CTL)) {
    Write-Host "${BLUE}⬇️  Đang tải PostgreSQL 16.4 Portable cho Windows...${NC}"
    $pgZip = Join-Path $env:TEMP "postgresql-16.4-1-windows-x64-binaries.zip"
    curl.exe -L --progress-bar -o $pgZip "https://get.enterprisedb.com/postgresql/postgresql-16.4-1-windows-x64-binaries.zip"
    tar.exe -xf $pgZip -C $TOOLS_DIR pgsql/bin pgsql/lib pgsql/share
    Remove-Item $pgZip -Force -ErrorAction SilentlyContinue
}

# 1e. Đảm bảo thư mục dữ liệu & Junction giống Docker (/app/data, /app/uploads, /app/eval_results)
New-Item -ItemType Directory -Force -Path (Join-Path $SCRIPT_DIR "data\knowledge\uploads") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $SCRIPT_DIR "data\eval\results") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $SCRIPT_DIR "chroma_data") | Out-Null

if (-not (Test-Path (Join-Path $SCRIPT_DIR "backend\data"))) {
    cmd.exe /c mklink /J "$SCRIPT_DIR\backend\data" "$SCRIPT_DIR\data" | Out-Null
}
if (-not (Test-Path (Join-Path $SCRIPT_DIR "backend\uploads"))) {
    cmd.exe /c mklink /J "$SCRIPT_DIR\backend\uploads" "$SCRIPT_DIR\data\knowledge\uploads" | Out-Null
}
if (-not (Test-Path (Join-Path $SCRIPT_DIR "backend\eval_results"))) {
    cmd.exe /c mklink /J "$SCRIPT_DIR\backend\eval_results" "$SCRIPT_DIR\data\eval\results" | Out-Null
}

Write-Host "${GREEN}✅ Môi trường thực thi đã sẵn sàng!${NC}"
Write-Host ""

# ------------------------------------------------------------------------------
# 2. Cấu hình biến môi trường (backend/.env)
# ------------------------------------------------------------------------------
$ENV_FILE = Join-Path $SCRIPT_DIR "backend\.env"
$NEED_ENV_SETUP = $false
$EXISTING_SECRET = ""
$EXISTING_API_KEY = ""

if (Test-Path $ENV_FILE) {
    foreach ($line in (Get-Content $ENV_FILE -Encoding UTF8)) {
        if ($line -match "^SECRET_KEY=(.+)$") { $EXISTING_SECRET = $Matches[1].Trim() }
        if ($line -match "^GOOGLE_API_KEY=(.+)$") { $EXISTING_API_KEY = $Matches[1].Trim() }
    }
}

if ([string]::IsNullOrWhiteSpace($EXISTING_SECRET) -or
    [string]::IsNullOrWhiteSpace($EXISTING_API_KEY) -or
    $EXISTING_API_KEY -eq "your-gemini-api-key-here") {
    $NEED_ENV_SETUP = $true
}

if ($NEED_ENV_SETUP) {
    Write-Host "${BLUE}${BOLD}🔧 Cấu hình môi trường lần đầu (backend/.env)${NC}"

    if ([string]::IsNullOrWhiteSpace($EXISTING_SECRET)) {
        $bytes = New-Object byte[] 32
        [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
        $EXISTING_SECRET = ($bytes | ForEach-Object { $_.ToString("x2") }) -join ""
        Write-Host "${GREEN}🔑 Đã tự động sinh SECRET_KEY bảo mật ngẫu nhiên.${NC}"
    }

    while ([string]::IsNullOrWhiteSpace($EXISTING_API_KEY) -or $EXISTING_API_KEY -eq "your-gemini-api-key-here") {
        Write-Host "${YELLOW}👉 Dự án cần GOOGLE_API_KEY (Gemini API Key) lấy tại https://aistudio.google.com/apikey${NC}"
        $INPUT_KEY = (Read-Host "Nhập GOOGLE_API_KEY của bạn (hoặc nhấn Enter để dùng khóa tạm test giao diện)").Trim()
        if (-not [string]::IsNullOrWhiteSpace($INPUT_KEY)) {
            $EXISTING_API_KEY = $INPUT_KEY
        } else {
            $EXISTING_API_KEY = "your-gemini-api-key-here"
            Write-Host "${YELLOW}⚠️  Đang dùng GOOGLE_API_KEY tạm thời (giao diện chạy bình thường, cần điền key thật vào backend/.env để chat AI).${NC}"
            break
        }
    }

    $envContent = @(
        "# Cấu hình tự động sinh bởi run_windows.bat",
        "# Lưu ý: Không để các dòng biến trống (key=) vì pydantic-settings sẽ báo lỗi.",
        "SECRET_KEY=$EXISTING_SECRET",
        "GOOGLE_API_KEY=$EXISTING_API_KEY",
        "DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/fitai_db",
        "CHROMA_HOST=127.0.0.1",
        "CHROMA_PORT=8001",
        'BACKEND_CORS_ORIGINS=["http://localhost:3000"]'
    ) -join "`n"
    [System.IO.File]::WriteAllText($ENV_FILE, $envContent + "`n", (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "${GREEN}✅ Đã lưu cấu hình chuẩn vào backend/.env!${NC}"
    Write-Host ""
} else {
    Write-Host "${GREEN}✅ Đã tìm thấy cấu hình hợp lệ tại backend/.env.${NC}"
    Write-Host ""
}

# ------------------------------------------------------------------------------
# 3. Khởi động các dịch vụ (PostgreSQL, ChromaDB, Backend, Frontend)
# ------------------------------------------------------------------------------
Write-Host "${BLUE}${BOLD}🚀 Đang khởi chạy các dịch vụ (PostgreSQL, ChromaDB, Backend, Frontend)...${NC}"

function Start-DetachedProcess {
    param([string]$CommandLine, [string]$WorkingDirectory = $SCRIPT_DIR)
    $startup = New-CimInstance -ClassName Win32_ProcessStartup -Property @{ ShowWindow = [uint16]0 } -ClientOnly
    Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = $CommandLine
        CurrentDirectory = $WorkingDirectory
        ProcessStartupInformation = $startup
    } | Out-Null
}
# 3a. PostgreSQL (port 5432)
$PG_DATA = Join-Path $SCRIPT_DIR "postgres_data"
$PG_LOG  = Join-Path $env:TEMP "fitai_postgres.log"
if (-not (Test-Path (Join-Path $PG_DATA "PG_VERSION"))) {
    Write-Host "${BLUE}🗄️  Khởi tạo cụm dữ liệu PostgreSQL lần đầu...${NC}"
    $pwFile = Join-Path $env:TEMP "fitai_pgpass.txt"
    [System.IO.File]::WriteAllText($pwFile, "postgres", [System.Text.Encoding]::ASCII)
    & "$PG_BIN\initdb.exe" -D $PG_DATA -U postgres -E UTF8 --locale=C -A scram-sha-256 --pwfile=$pwFile | Out-Null
    Remove-Item $pwFile -Force -ErrorAction SilentlyContinue
}

Write-Host "   [1/4] PostgreSQL (port 5432)..."
& "$PG_BIN\pg_isready.exe" -h 127.0.0.1 -p 5432 -U postgres 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Get-Process postgres -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
    Remove-Item (Join-Path $PG_DATA "postmaster.pid") -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $PG_DATA "postgres.log*") -Force -ErrorAction SilentlyContinue
    Start-DetachedProcess -CommandLine "cmd.exe /c `"`"$PG_BIN\postgres.exe`" -D `"$PG_DATA`" -p 5432 > `"$PG_LOG`" 2>&1`"" -WorkingDirectory $SCRIPT_DIR
    for ($w = 0; $w -lt 30; $w++) {
        & "$PG_BIN\pg_isready.exe" -h 127.0.0.1 -p 5432 -U postgres 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { break }
        Start-Sleep -Milliseconds 500
    }
}

$env:PGPASSWORD = "postgres"
$dbExists = & "$PG_BIN\psql.exe" -h 127.0.0.1 -p 5432 -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='fitai_db'" 2>$null
if (($dbExists | Out-String).Trim() -ne "1") {
    & "$PG_BIN\createdb.exe" -h 127.0.0.1 -p 5432 -U postgres fitai_db
}

# 3b. ChromaDB (port 8001)
Write-Host "   [2/4] ChromaDB (port 8001)..."
$CHROMA_LOG = Join-Path $env:TEMP "fitai_chroma.log"
$chromaListening = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
if (-not $chromaListening) {
    $chromaPath = Join-Path $SCRIPT_DIR "chroma_data"
    Start-DetachedProcess -CommandLine "cmd.exe /c `"`"$CHROMA_EXE`" run --path `"$chromaPath`" --port 8001 > `"$CHROMA_LOG`" 2>&1`"" -WorkingDirectory $SCRIPT_DIR
}

# 3c. FastAPI Backend (port 8000)
Write-Host "   [3/4] FastAPI Backend (port 8000)..."
$BACKEND_LOG = Join-Path $env:TEMP "fitai_backend.log"
$backendListening = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (-not $backendListening) {
    $backendDir = Join-Path $SCRIPT_DIR "backend"
    Start-DetachedProcess -CommandLine "cmd.exe /c `"set PYTHONUTF8=1&& set PYTHONIOENCODING=utf-8&& `"$UVICORN`" main:app --host 0.0.0.0 --port 8000 --reload --reload-dir api --reload-dir core --reload-dir models --reload-dir services > `"$BACKEND_LOG`" 2>&1`"" -WorkingDirectory $backendDir
}

# 3d. Next.js Frontend (port 3000) — kèm DNS shim để http://backend:8000 trong next.config.ts trỏ về 127.0.0.1
Write-Host "   [4/4] Next.js Frontend (port 3000)..."
$FRONTEND_LOG = Join-Path $env:TEMP "fitai_frontend.log"
$dnsShimFile  = Join-Path $env:TEMP "fitai_dns.cjs"
$dnsShimCode  = 'const dns=require("dns"),o=dns.lookup;dns.lookup=function(h,opt,cb){if(h==="backend"||h==="chromadb"||h==="db"||h==="localhost")h="127.0.0.1";return o.call(this,h,opt,cb);};'
[System.IO.File]::WriteAllText($dnsShimFile, $dnsShimCode, (New-Object System.Text.UTF8Encoding($false)))
$dnsShimArg   = $dnsShimFile.Replace('\', '/')
$frontendListening = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if (-not $frontendListening) {
    $frontendDir = Join-Path $SCRIPT_DIR "frontend"
    Start-DetachedProcess -CommandLine "cmd.exe /c `"set PATH=$NODE_DIR;%PATH%&& set NODE_OPTIONS=--require $dnsShimArg&& set NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1&& `"$NPM_CMD`" run dev > `"$FRONTEND_LOG`" 2>&1`"" -WorkingDirectory $frontendDir
}

Write-Host "${BLUE}⏳ Đang đợi Backend khởi động và kết nối Database...${NC}"
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -ErrorAction Stop
        if ($resp.status -eq "ok") { break }
    } catch {}
    Start-Sleep -Seconds 2
}
Write-Host "${GREEN}✅ Các dịch vụ FitAI đã chạy!${NC}"
Write-Host ""

# ------------------------------------------------------------------------------
# 4. Chạy Migration (Alembic)
# ------------------------------------------------------------------------------
Write-Host "${BLUE}${BOLD}🗄️  Đang cập nhật cấu trúc bảng dữ liệu (Alembic migration)...${NC}"
Push-Location (Join-Path $SCRIPT_DIR "backend")
& $ALEMBIC upgrade head
Write-Host ""

# ------------------------------------------------------------------------------
# 5. Kiểm tra & Nạp dữ liệu khởi tạo (Idempotent — chỉ nạp khi chưa có hoặc cần)
# ------------------------------------------------------------------------------
$checkScript = @"
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
"@

$DB_COUNTS = ($checkScript | & $VENV_PY - 2>$null | Select-Object -Last 1)
$parts = "$DB_COUNTS".Split("|")
$FOOD_COUNT  = if ($parts.Count -ge 1 -and $parts[0] -match '^\d+$') { [int]$parts[0] } else { 0 }
$PROG_COUNT  = if ($parts.Count -ge 2 -and $parts[1] -match '^\d+$') { [int]$parts[1] } else { 0 }
$ADMIN_EMAIL = if ($parts.Count -ge 3) { $parts[2].Trim() } else { "" }

if ($FOOD_COUNT -eq 0) {
    Write-Host "${BLUE}${BOLD}🥗 Đang nạp dữ liệu thực phẩm Việt Nam 2007 & USDA...${NC}"
    & $VENV_PY scripts/ingest_foods.py
    & $VENV_PY scripts/ingest_usda_foods.py
    Write-Host ""
} else {
    Write-Host "${GREEN}✅ Bảng thực phẩm đã có dữ liệu ($FOOD_COUNT món). Bỏ qua nạp lại.${NC}"
}

if ($PROG_COUNT -eq 0) {
    Write-Host "${BLUE}${BOLD}🏋️  Đang nạp chương trình tập luyện mẫu...${NC}"
    & $VENV_PY scripts/seed_training.py
    Write-Host ""
} else {
    Write-Host "${GREEN}✅ Chương trình tập luyện đã có dữ liệu ($PROG_COUNT chương trình). Bỏ qua nạp lại.${NC}"
}

# Kiểm tra tài khoản Admin và 70 món ăn chế biến (ADMIN_MANUAL)
if ([string]::IsNullOrWhiteSpace($ADMIN_EMAIL)) {
    Write-Host ""
    Write-Host "${YELLOW}👤 Chưa có tài khoản Quản trị viên (Admin).${NC}"
    $MAKE_ADMIN_ANS = Read-Host "Bạn có muốn tạo nhanh tài khoản Admin & nạp thêm 70 món ăn chế biến sẵn không? (Y/n)"
    if ([string]::IsNullOrWhiteSpace($MAKE_ADMIN_ANS)) { $MAKE_ADMIN_ANS = "Y" }
    if ($MAKE_ADMIN_ANS -match "^[Yy]$") {
        $INPUT_ADMIN_EMAIL = Read-Host "   Nhập email Admin (mặc định: admin@fitai.local)"
        if ([string]::IsNullOrWhiteSpace($INPUT_ADMIN_EMAIL)) { $INPUT_ADMIN_EMAIL = "admin@fitai.local" }
        $INPUT_ADMIN_PASS = Read-Host "   Nhập mật khẩu Admin (mặc định: Admin@123456)"
        if ([string]::IsNullOrWhiteSpace($INPUT_ADMIN_PASS)) { $INPUT_ADMIN_PASS = "Admin@123456" }

        $env:FITAI_INIT_ADMIN_EMAIL = $INPUT_ADMIN_EMAIL
        $env:FITAI_INIT_ADMIN_PASS  = $INPUT_ADMIN_PASS
        $ensureUserScript = @"
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
"@
        $ensureUserScript | & $VENV_PY -
        & $VENV_PY scripts/make_admin.py $INPUT_ADMIN_EMAIL
        Write-Host "${BLUE}🍲 Đang nạp 70 món ăn chế biến, đồ uống và thực phẩm cơ bản...${NC}"
        & $VENV_PY scripts/import_admin_foods.py --admin-email $INPUT_ADMIN_EMAIL
        & $VENV_PY scripts/import_admin_foods.py --admin-email $INPUT_ADMIN_EMAIL --file data/foods/manual/dishes_all.csv --update-existing
        Write-Host "${GREEN}✅ Đã tạo tài khoản Admin ($INPUT_ADMIN_EMAIL) và nạp đủ 70 món ăn!${NC}"
    }
} else {
    Write-Host "${GREEN}✅ Đã có tài khoản Admin ($ADMIN_EMAIL).${NC}"
}

# Kiểm tra dữ liệu RAG trong ChromaDB
$chromaCheckScript = @"
from core.config import settings
from services.knowledge.vector_store import get_client, open_collection
try:
    col = open_collection(get_client(), settings.CHROMA_COLLECTION_NAME, settings.EMBEDDING_MODEL, reset=False)
    print(col.count())
except Exception:
    print(0)
"@
$CHROMA_COUNT_RAW = ($chromaCheckScript | & $VENV_PY - 2>$null | Select-Object -Last 1)
$CHROMA_COUNT = if ("$CHROMA_COUNT_RAW" -match '^\d+$') { [int]"$CHROMA_COUNT_RAW" } else { 0 }

if ($CHROMA_COUNT -eq 0) {
    Write-Host ""
    Write-Host "${YELLOW}📚 Kho tri thức RAG (ChromaDB) hiện đang trống (0 đoạn).${NC}"
    Write-Host "   Việc nạp tài liệu ISSN & WHO (134 đoạn) sẽ gọi Gemini Embedding API."
    $RAG_ANS = Read-Host "Bạn có muốn nạp tài liệu RAG vào ChromaDB ngay bây giờ không? (y/N)"
    if ([string]::IsNullOrWhiteSpace($RAG_ANS)) { $RAG_ANS = "N" }
    if ($RAG_ANS -match "^[Yy]$") {
        & $VENV_PY scripts/ingest_knowledge.py
    }
} else {
    Write-Host "${GREEN}✅ Kho tri thức RAG (ChromaDB) đã có $CHROMA_COUNT đoạn văn bản.${NC}"
}
Pop-Location

# ------------------------------------------------------------------------------
# 6. Hoàn tất & Mở trình duyệt
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "${GREEN}${BOLD}==============================================================${NC}"
Write-Host "${GREEN}${BOLD}🎉 FitAI đã khởi động thành công trên máy Windows của bạn!${NC}"
Write-Host "${GREEN}${BOLD}==============================================================${NC}"
Write-Host "🌐 Giao diện Web (Frontend): ${BOLD}http://localhost:3000${NC}"
Write-Host "⚙️  Tài liệu API (Swagger):   ${BOLD}http://localhost:8000/api/v1/docs${NC}"
Write-Host "❤️  Kiểm tra Health:          ${BOLD}http://localhost:8000/health${NC}"
Write-Host ""
Write-Host "💡 Đang tự động mở trình duyệt tới ${BOLD}http://localhost:3000${NC} ..."
Start-Process "http://localhost:3000" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "${YELLOW}Tuỳ chọn nhanh:${NC}"
Write-Host "  - Nhấn ${BOLD}Enter${NC} để đóng cửa sổ này (ứng dụng vẫn tiếp tục chạy ngầm)."
Write-Host "  - Gõ ${BOLD}admin${NC} rồi nhấn Enter để cấp quyền Admin cho một email."
Write-Host "  - Gõ ${BOLD}logs${NC} rồi nhấn Enter để xem log trực tiếp của Backend/Frontend."
Write-Host "  - Gõ ${BOLD}stop${NC} rồi nhấn Enter để tắt toàn bộ các dịch vụ FitAI."
$ACTION_ANS = (Read-Host "Lựa chọn của bạn [Enter/admin/logs/stop]").Trim().ToLower()

switch ($ACTION_ANS) {
    "admin" {
        $TARGET_EMAIL = (Read-Host "Nhập email tài khoản cần cấp quyền Admin").Trim()
        if (-not [string]::IsNullOrWhiteSpace($TARGET_EMAIL)) {
            Push-Location (Join-Path $SCRIPT_DIR "backend")
            & $VENV_PY scripts/make_admin.py $TARGET_EMAIL
            Pop-Location
        }
        Read-Host "Nhấn Enter để thoát..."
    }
    "logs" {
        Write-Host "${BLUE}📋 Đang hiển thị log Backend (Nhấn Ctrl+C để thoát)...${NC}"
        if (Test-Path "$BACKEND_LOG.err") {
            Get-Content -Path $BACKEND_LOG, "$BACKEND_LOG.err" -Tail 40 -Wait
        } elseif (Test-Path $BACKEND_LOG) {
            Get-Content -Path $BACKEND_LOG -Tail 40 -Wait
        }
    }
    "stop" {
        Write-Host "${YELLOW}🛑 Đang dừng các dịch vụ FitAI...${NC}"
        foreach ($port in @(3000, 8000, 8001)) {
            Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
                Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
            }
        }
        & $PG_CTL -D $PG_DATA stop -m fast 2>&1 | Out-Null
        Write-Host "${GREEN}✅ Đã dừng toàn bộ dịch vụ.${NC}"
        Start-Sleep -Seconds 2
    }
    default {
        Write-Host "${GREEN}👋 Chúc bạn trải nghiệm FitAI vui vẻ!${NC}"
        Start-Sleep -Seconds 1
    }
}
