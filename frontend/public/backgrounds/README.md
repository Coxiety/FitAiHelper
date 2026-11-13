# Thư mục Hình nền Tuỳ chỉnh (`frontend/public/backgrounds/`)

Bạn có thể chép bất kỳ hình ảnh nào (`.jpg`, `.png`, `.webp`) vào thư mục này để dùng làm hình nền cho FitAI.

## Cách 1: Đặt tên file tự động nhận diện (không cần cấu hình)
Chỉ cần chép ảnh vào thư mục `frontend/public/backgrounds/` với một trong các tên sau:
- **`bg.jpg`** (hoặc `bg.png`, `bg.webp`): Tự động làm hình nền chung cho **toàn bộ ứng dụng** (cả trang Đăng nhập lẫn các trang bên trong).
- **`auth.jpg`**: Chỉ làm hình nền cho trang **Đăng nhập / Đăng ký**.
- **`app.jpg`**: Chỉ làm hình nền cho các trang **Tổng quan, Nhật ký, Chat, Tập luyện, Quản trị**.

## Cách 2: Chọn trực tiếp trên giao diện Web (nút "Hình nền")
Ở góc trên thanh điều hướng (hoặc góc dưới trang Đăng nhập), bấm vào nút **"Hình nền"**:
1. **Tải ảnh từ máy tính:** Chọn bất kỳ file ảnh nào trên máy của bạn (hỗ trợ ảnh độ phân giải cao, lưu trực tiếp trong trình duyệt qua IndexedDB).
2. **Hoặc dùng file trong thư mục này với tên bất kỳ:** Ví dụ bạn chép file `forest.jpg` vào `frontend/public/backgrounds/forest.jpg`, chỉ cần gõ `/backgrounds/forest.jpg` vào ô đường dẫn.
3. **Điều chỉnh lớp phủ mờ (Overlay) & độ nhòe (Blur):** Kéo thanh trượt để các thẻ nội dung nổi bật, dễ đọc trên nền ảnh của bạn.

