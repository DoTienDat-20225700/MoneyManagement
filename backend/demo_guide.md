# KỊCH BẢN DEMO TỪNG BƯỚC (MONEYMANAGEMENT)

**Ngày chạy dữ liệu:** 17/10/2026  
**Mật khẩu dùng chung:** `Demo@12345`

---

## 1. TÀI KHOẢN CHÍNH (KỊCH BẢN CĂNG THẲNG): `demo@moneymanagement.local`
- **Người dùng:** Minh Anh Nguyễn (Sinh viên năm cuối đi làm thêm)
- **Số dư ví ban đầu:** `17,905,000 đ`

### Bước 1: Tổng quan và Lịch sử Giao dịch
- **Mở trang:** `/` (Home) hoặc `/transactions`
- **Thao tác:** Lướt danh sách giao dịch 180 ngày qua, lọc theo loại hoặc danh mục.
- **Kỳ vọng:** Dữ liệu phong phú, biến động chân thực, có các giao dịch định kỳ (Lương, Tiền nhà, Internet).

### Bước 2: Cảnh báo & Tái cân bằng Ngân sách (F05)
- **Mở trang:** `/budgets`
- **Quan sát:**
  - Danh mục **Mua sắm**: Đã chi `1.250.000 đ / 1.000.000 đ` (VƯỢT NGÂN SÁCH). Nút **"Tái cân bằng"** xuất hiện nổi bật.
  - Danh mục **Ăn uống**: Đã chi `2.750.000 đ / 3.000.000 đ` (~91.7%, TIỆM CẬN NGƯỠNG).
  - Danh mục **Giải trí** & **Sách vở**: Đã chi dưới 40%, còn dư hạn mức.
- **Thao tác 1 (Tái cân bằng):**
  - Bấm nút "Tái cân bằng" trên thẻ Mua sắm.
  - Chọn chuyển 250.000 đ từ Giải trí sang Mua sắm.
  - Xác nhận: Ngân sách Mua sắm tăng lên, Giải trí giảm tương ứng, tổng không đổi.
- **Thao tác 2 (Kiểm tra tác động thời gian thực):**
  - Mở modal thêm giao dịch chi tiêu mới.
  - Chọn danh mục "Ăn uống", nhập số tiền `500.000 đ`.
  - **Kỳ vọng:** Hệ thống hiện thông báo cảnh báo tức thì (vượt ngân sách 250.000 đ).

### Bước 3: Quản lý Sổ nợ & Trả góp (F02)
- **Mở trang:** `/debts`
- **Quan sát Summary:**
  - Khoản quá hạn: **1 khoản** (Hà - 1.500.000 đ quá hạn 5 ngày).
  - Khoản sắp đến hạn trong 7 ngày: **1 khoản** (Anh Hùng - 2.000.000 đ đến hạn sau 6 ngày).
  - Khoản đã trả xong: **Chị Linh** (1.000.000 đ).
  - Các hợp đồng trả góp: **Laptop ASUS** (đã trả 4/12 kỳ) và **iPhone 15** (đã trả 2/6 kỳ).
- **Thao tác:** Bấm xem lịch trả góp chi tiết của Laptop để thấy kỳ tiếp theo đến hạn ngày +20.

### Bước 4: Dự báo Dòng tiền & Cảnh báo Cạn quỹ (F03)
- **Mở trang:** `/reports` -> Chuyển sang Tab **"Dự báo"** (hoặc `/forecast`)
- **Cấu hình:** Khoảng thời gian: **30 ngày**, Ngưỡng an toàn: **1.000.000 đ**.
- **Kỳ vọng:**
  - Mức cảnh báo: **CRITICAL (Báo động đỏ)**.
  - Đáy số dư: Âm `-1,215,186 đ` tại ngày **12/11/2026** (ngày thứ +26).
  - Trạng thái WARNING xuất hiện từ ngày thứ +20 trước khi chạm đáy.
  - Đường dự báo bật tăng mạnh mẽ sau ngày +27 khi nhận lương định kỳ.

---

## 2. TÀI KHOẢN ĐỐI CHỨNG (KỊCH BẢN AN TOÀN): `demo.safe@moneymanagement.local`
- **Người dùng:** Quốc Bảo Trần (Kỹ sư phần mềm thu nhập ổn định)
- **Mở trang:** Đăng xuất và đăng nhập bằng tài khoản `demo.safe@moneymanagement.local`.
- **Vào `/reports` -> Tab "Dự báo":**
  - Mức cảnh báo: **SAFE (An toàn)**.
  - Toàn bộ đường dự báo nằm vững vàng trên ngưỡng an toàn, thể hiện năng lực đối chiếu đa kịch bản của giải pháp.
