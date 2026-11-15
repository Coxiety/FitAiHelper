# Hướng dẫn sử dụng & vận hành FitAI

Tài liệu này hướng dẫn đầy đủ cách khởi chạy FitAI bằng 1 cú nhấp đúp trên **macOS** và **Windows**, cách dùng chung dữ liệu qua **Neon Cloud PostgreSQL**, kết nối **Telegram Bot**, và xử lý các lỗi thường gặp.

---

## 1. Tổng quan địa chỉ truy cập

Sau khi khởi động thành công, bạn truy cập các địa chỉ sau:

| Thành phần | Địa chỉ | Ghi chú |
|---|---|---|
| **Giao diện Web (Frontend)** | `http://localhost:3000` | Đăng ký, đăng nhập, chat AI, nhật ký ăn uống, tập luyện, quản trị |
| **Tài liệu API (Swagger)** | `http://localhost:8000/api/v1/docs` | Kiểm thử trực tiếp các endpoint REST API |
| **Kiểm tra trạng thái (Health)** | `http://localhost:8000/health` | Trả về `{"status":"ok","version":"1.0.0"}` khi Backend sẵn sàng |
| **ChromaDB (Vector Store)** | `http://127.0.0.1:8001` | Cổng truy cập từ máy host (kho tri thức RAG) |

---

## 2. Lựa chọn cách khởi chạy

Dự án cung cấp 3 script khởi chạy tự động (tự cài đặt môi trường, chạy migration, nạp dữ liệu món ăn/tập luyện, tạo tài khoản Admin nếu chưa có):

| Script | Hệ điều hành | Kiến trúc | Khi nào nên dùng |
|---|---|---|---|
| [run_mac.command](../run_mac.command) | macOS | **Docker Compose** | Đã có Docker Desktop, muốn môi trường cô lập chuẩn production/dev |
| [run_mac_native.command](../run_mac_native.command) | macOS | **Native (Không cần Docker)** | Muốn chạy trực tiếp trên macOS, tiết kiệm RAM, không bật Docker Desktop |
| [run_windows.bat](../run_windows.bat) | Windows | **Native (Không cần Docker)** | Chạy 1 cú nhấp đúp trên Windows 10/11 |

> **Lưu ý trên macOS nếu báo lỗi không đủ quyền (`appropriate access privileges`):**
> Mở Terminal tại thư mục gốc dự án và cấp quyền thực thi một lần:
> ```bash
> chmod +x run_mac.command run_mac_native.command
> ```
> *(Nếu dự án nằm trong Google Drive / iCloud, đôi khi đồng bộ file có thể làm mất quyền `x`; chỉ cần chạy lại lệnh `chmod +x` trên.)*

---

## 3. Cấu hình môi trường (`backend/.env`)

File cấu hình nằm tại `backend/.env` (tuyệt đối **không commit** lên Git). Lần đầu chạy bất kỳ script nào ở trên, nếu chưa có `backend/.env`, script sẽ tự sinh `SECRET_KEY` và hỏi `GOOGLE_API_KEY`:

* **`SECRET_KEY`** *(bắt buộc)*: Chuỗi bí mật ký JWT, được script tự động sinh ngẫu nhiên (`openssl rand -hex 32`).
* **`GOOGLE_API_KEY`** *(bắt buộc để dùng AI/RAG)*: Khóa Gemini API lấy tại [Google AI Studio](https://aistudio.google.com/apikey).
  * Nếu chưa có key và chỉ muốn xem giao diện, bạn có thể **nhấn `Enter` để bỏ qua** — script sẽ đặt khóa tạm `your-gemini-api-key-here` (web vẫn chạy bình thường, chỉ tính năng chat AI/Vision/RAG cần key thật).
* **`BACKEND_CORS_ORIGINS`**: Mặc định `["http://localhost:3000"]`.
* **`DATABASE_URL` & `DATABASE_URL_UNPOOLED`** *(tùy chọn)*:
  * Nếu **không khai báo**, bản Docker sẽ dùng container `db` (`fitai_postgres`), còn bản Native sẽ tự khởi chạy PostgreSQL 16 cục bộ trên máy.
  * Nếu **khai báo URL Cloud PostgreSQL** (ví dụ **Neon**), cả bản Docker, macOS Native và Windows đều tự nhận diện và dùng chung database đó.
* **`TELEGRAM_BOT_TOKEN`** *(tùy chọn)*: Token bot lấy từ `@BotFather`. Nếu có giá trị, các script sẽ tự động khởi chạy Telegram Bot kèm theo.

> **Quy tắc định dạng `backend/.env`:** Không để biến ở dạng `KEY=` (giá trị rỗng) vì `pydantic-settings` sẽ báo lỗi khi khởi động. Biến nào không dùng hãy xoá hẳn dòng hoặc thêm dấu `#` ở đầu dòng.

---

## 4. Hướng dẫn chi tiết theo từng nền tảng

### 4.1. Chạy bằng Docker trên macOS (`run_mac.command`)
1. Nhấp đúp vào [run_mac.command](../run_mac.command) (hoặc chạy `./run_mac.command` trong Terminal).
2. Nếu chưa cài Docker Desktop, script sẽ hỏi tải và cài tự động; nếu Docker chưa mở, script tự mở Docker Desktop và đợi sẵn sàng.
3. Script tự kiểm tra xung đột cổng (`3000`, `8000`, `8001`), dọn symlink từ bản Native (nếu có), chạy `docker compose up -d --build`, chạy `alembic upgrade head`, nạp dữ liệu mẫu và mở trình duyệt tới `http://localhost:3000`.
4. Ở menu cuối màn hình, bạn có các lựa chọn nhanh:
   * **`Enter`**: Đóng cửa sổ Terminal (các container vẫn tiếp tục chạy ngầm).
   * **`admin`**: Nhập email tài khoản để cấp quyền Quản trị viên (`scripts/make_admin.py`).
   * **`logs`**: Xem log trực tiếp (`docker compose logs -f`).
   * **`stop`**: Tắt toàn bộ các container FitAI (`docker compose down`).

### 4.2. Chạy Native trên macOS (`run_mac_native.command`)
1. Nhấp đúp vào [run_mac_native.command](../run_mac_native.command).
2. Script tự cài mọi công cụ cần thiết vào `~/.local/share/FitAI_Tools` và `backend/.venv`:
   * `uv` + Python 3.11 + thư viện trong `backend/requirements.txt` (tự bổ sung `greenlet` cho Apple Silicon `arm64`).
   * ChromaDB `1.5.9` (chạy ở cổng `8001`).
   * Node.js `v22.22.0` + `npm install` + `next build` (nếu chưa có).
   * PostgreSQL 16 (chỉ cài/chạy cục bộ nếu `backend/.env` **chưa** trỏ tới database ngoài như Neon).
3. Menu cuối có đầy đủ `[Enter/admin/logs/stop]`:
   * Gõ `logs` để theo dõi `/tmp/fitai_backend.log`.
   * Gõ `stop` để tắt sạch tiến trình Backend (`uvicorn`), Frontend (`next`), ChromaDB, Telegram Bot và PostgreSQL cục bộ.

### 4.3. Chạy Native trên Windows (`run_windows.bat`)
1. Nhấp đúp vào [run_windows.bat](../run_windows.bat).
2. Script tự chuẩn bị `Python 3.11` (`backend/.venv`), `ChromaDB 1.5.9`, `Node.js v22.14.0`, và `PostgreSQL 16.4` (bỏ qua Postgres cục bộ nếu `backend/.env` đã trỏ database ngoài như Neon).
3. Menu cuối hỗ trợ `[Enter/admin/logs/stop]` tương tự macOS.

---

## 5. Dùng chung dữ liệu giữa nhiều máy (Neon Cloud PostgreSQL)

Mặc định, dữ liệu ở chế độ cục bộ tách biệt theo từng máy/môi trường (`./postgres_data` ở Native và Docker volume ở Docker). Để đăng nhập cùng tài khoản, giữ nguyên nhật ký và liên kết Telegram giữa **macOS (Docker & Native)** và **Windows**:

1. Đặt cùng một cặp `DATABASE_URL` và `DATABASE_URL_UNPOOLED` của Neon vào `backend/.env` trên các máy bạn sử dụng.
2. Backend ([config.py](../backend/core/config.py)) tự động chuyển tham số `sslmode=require` / `channel_binding=require` sang định dạng tương thích `asyncpg`, và Alembic ([env.py](../backend/alembic/env.py)) tự ưu tiên `DATABASE_URL_UNPOOLED` qua `psycopg2` khi chạy migration.
3. Trên cả `run_mac_native.command` và `run_windows.bat`, khi thấy `DATABASE_URL` trỏ ra ngoài (`neon.tech`...), script sẽ không khởi chạy Postgres cục bộ dư thừa.

> **Lưu ý về ChromaDB (RAG) khi đổi máy:** PostgreSQL lưu trên Neon được đồng bộ giữa các máy, nhưng **ChromaDB** vẫn lưu cục bộ tại thư mục `chroma_data/` của từng máy. Khi mở lần đầu trên máy mới, hãy chọn **`y`** ở bước hỏi nạp tài liệu RAG (`ingest_knowledge.py`) nếu bạn cần chatbot tra cứu tài liệu ISSN & WHO trên máy đó.

---

## 6. Sử dụng Telegram Bot

### 6.1. Kích hoạt Bot
1. Tạo bot (hoặc lấy token) qua `@BotFather` trên Telegram.
2. Thêm dòng sau vào `backend/.env`:
   ```env
   TELEGRAM_BOT_TOKEN=your-bot-token
   ```
3. Khởi động lại FitAI bằng script tương ứng.

> **Quan trọng:** Telegram Long Polling chỉ cho phép **1 tiến trình bot duy nhất** chạy cho mỗi `TELEGRAM_BOT_TOKEN` tại cùng một thời điểm. Nếu bạn chạy đồng thời cả Mac và Windows, hãy chỉ giữ `TELEGRAM_BOT_TOKEN` ở **1 máy** (hoặc dùng 2 bot token riêng cho môi trường dev/prod).

### 6.2. Liên kết tài khoản & Các lệnh hỗ trợ
1. Đăng nhập Web tại `http://localhost:3000`.
2. Trên Dashboard, bấm nút **Lấy mã Telegram** để nhận lệnh dạng `/link XXXXXXXX` (bấm vào nút để sao chép).
3. Mở đúng bot Telegram của bạn, bấm `/start` và gửi lệnh `/link <MÃ>` (hoặc `/link <email> <mật_khẩu>`).
   * Mỗi lần bạn liên kết trên một tài khoản mới, bot sẽ tự động chuyển `telegram_chat_id` sang tài khoản mới đó.
4. Sau khi liên kết thành công, bạn có thể:
   * **Gửi ảnh bữa ăn:** Bot dùng Gemini Vision nhận diện món ăn, đối chiếu bảng calo trong DB và hiện nút `✅ Lưu vào nhật ký` / `❌ Huỷ`.
   * **Nhắn tin tự nhiên:** Ví dụ *"ghi 150g ức gà bữa trưa"*, *"hôm nay mình nặng 68kg"*, *"hôm nay ăn bao nhiêu calo rồi?"*.
   * **Gõ `/today`:** Xem nhanh tổng hợp Calo, Protein, Fat, Carb trong ngày.

---

## 7. Quản trị viên & Nạp dữ liệu

* **Cấp hoặc thu hồi quyền Admin:**
  * Cách nhanh nhất: chọn **`admin`** ở menu cuối khi chạy script khởi động.
  * Hoặc chạy thủ công:
    ```bash
    # Docker:
    docker compose exec backend python scripts/make_admin.py <email>
    docker compose exec backend python scripts/make_admin.py <email> --revoke

    # Native (trong thư mục backend/):
    .venv/bin/python scripts/make_admin.py <email>
    ```
* **Nạp tài liệu RAG (ISSN & WHO — 134 đoạn):**
  * Chú ý bước này gọi Gemini Embedding API nên tốn lượt hạn mức API. Khi script hỏi `Bạn có muốn nạp tài liệu RAG vào ChromaDB ngay bây giờ không? (y/N)`, gõ `y` nếu bạn muốn nạp ngay.

---

## 8. Chạy kiểm thử tự động (Backend Pytest)

Theo quy chuẩn trong [AGENTS.md](../AGENTS.md):

```bash
# Khi đang chạy bằng Docker:
docker compose exec backend pytest -v

# Hoặc chạy file test cụ thể:
docker compose exec backend pytest tests/test_health.py tests/test_security.py -v

# Khi chạy trực tiếp với .venv (Native):
cd backend
.venv/bin/pytest -v
```

---

## 9. Xử lý nhanh các lỗi thường gặp

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| macOS báo *not have appropriate access privileges* khi mở `.command` | File thiếu quyền thực thi (`+x`) | Chạy `chmod +x run_mac.command run_mac_native.command` |
| Đăng nhập lỗi `ConnectionRefusedError` dù đã đổi `backend/.env` | Tiến trình `uvicorn` cũ từ phiên trước vẫn giữ biến môi trường cũ trên cổng `8000` | Chạy tùy chọn `stop` rồi khởi động lại script (hoặc chạy `pkill -f "uvicorn main:app"` trước) |
| Chuyển từ Native sang Docker hoặc ngược lại bị báo trùng cổng `3000`/`8000`/`8001` | Dịch vụ của chế độ trước chưa tắt | Dùng tùy chọn `stop` ở chế độ cũ trước khi bật chế độ mới |
| Telegram Bot không trả lời hoặc báo xung đột | Thiếu `TELEGRAM_BOT_TOKEN`, hoặc đang chạy trùng 1 token ở 2 máy, hoặc chưa `/link` lại khi tạo tài khoản mới | Kiểm tra `TELEGRAM_BOT_TOKEN` chỉ chạy ở 1 nơi và gửi lại `/link <MÃ>` từ tài khoản Web hiện tại |
| Chatbot hoặc nạp RAG báo lỗi quota / 429 | Hết hạn mức miễn phí của Gemini API key trong ngày | Đợi reset hạn mức hoặc đổi `GOOGLE_API_KEY` mới trong `backend/.env` |
