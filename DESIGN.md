# Tài liệu Thiết kế Giao diện (DESIGN.md) - MoneyManagement

## 1. Hệ thống Màu sắc & Token Thiết kế (Dark Theme)
Ứng dụng MoneyManagement sử dụng phong cách Dark Theme hiện đại với nền tối sâu, lớp phủ kính mờ (glassmorphism/backdrop-filter) và điểm nhấn xanh ngọc lục bảo (Emerald Green):

- **Nền chính (Background Default)**: `#080808`
- **Nền phụ / Khối nổi (Background Paper)**: `#2b2b2b`
- **Nền Sidebar & Drawer**: `#0d0e12` (với lớp phủ mờ `backdrop-filter: blur(14px)`)
- **Nền TopBar**: `rgba(13, 14, 18, 0.85)` (kèm `backdrop-filter: blur(14px)`)
- **Màu chủ đạo (Primary)**: `#00863A` (dùng cho nút chính, focus ring)
- **Màu điểm nhấn trạng thái chọn (Active Accent)**: `#48cc90` (chữ & viền chỉ báo)
- **Nền mục đang chọn (Active Background)**: `rgba(0, 134, 58, 0.22)`
- **Viền mục đang chọn (Active Border)**: `1px solid rgba(72, 204, 144, 0.35)`
- **Văn bản chính (text.primary)**: `#ffffff`
- **Văn bản phụ (text.secondary)**: `#9e9e9e` (đạt tỷ lệ tương phản >= 5.28:1 trên paper và >= 7.48:1 trên nền tối)

---

## 2. Bố cục Trang (Page Layout Architecture)

### 2.1. Breakpoint chuẩn
- **Màn hình lớn (`>= md`, >= 900px)**: Sidebar cố định bên trái, TopBar thu gọn nằm phía trên bên phải nội dung.
- **Màn hình di động & tablet nhỏ (`< md`, < 900px)**: Sidebar desktop ẩn; TopBar chiếm toàn chiều rộng có nút hamburger mở Drawer tạm thời (`temporary`).

### 2.2. Kích thước & Trạng thái Sidebar
- **Trạng thái Mở rộng (Expanded)**: Chiều rộng cố định `240px`.
  - Hiển thị logo, tên ứng dụng "MoneyManager", icon và nhãn đầy đủ của các mục điều hướng.
- **Trạng thái Thu gọn (Collapsed)**: Chiều rộng cố định `72px`.
  - Đầu sidebar: Logo căn giữa (`mx: auto`, 28x28px), ẩn dòng chữ "MoneyManager".
  - Các mục điều hướng: Icon căn giữa trong ô vuông bo góc (`width: 44px, height: 44px, borderRadius: 10px, mx: auto`).
  - Mục đang chọn: Nền nhạt xanh `rgba(0, 134, 58, 0.22)`, viền xanh `rgba(72, 204, 144, 0.35)` và chỉ báo bên trái `3px solid #48cc90`.
  - Tên mục hiển thị qua `Tooltip` (`placement="right"`) hỗ trợ cả khi di chuột (hover) và khi điều hướng bàn phím (focus).
  - Khoảng cách giữa các mục đều nhau (`mb: 1`).
  - **Không còn nút thu gọn ở đáy**: Đã xóa bỏ hoàn toàn nút chữ và vùng viền ở đáy sidebar, không để lại khoảng trống thừa.
- **Khởi tạo trạng thái**: Luôn mặc định **MỞ** (`collapsed = false`) khi tải trang. **Không lưu vào `localStorage`** để người dùng luôn có trải nghiệm nhất quán, trực quan mỗi lần mở ứng dụng.

### 2.3. Nút Hamburger Điều hướng Thống nhất ở Thanh trên (TopBar)
- **Vị trí**: Nằm ở góc trái thanh trên (`TopBar`), cố định trước phần tiêu đề.
- **Chức năng duy nhất theo breakpoint**:
  - Từ `md` trở lên: Bật/tắt trạng thái sidebar mở (240px) và thu gọn (72px).
  - Dưới `md`: Mở/đóng Mobile Drawer tạm thời.
- **Thuộc tính tiếp cận**:
  - `minWidth: 40px, minHeight: 40px` (vùng bấm chuẩn tiếp cận).
  - `aria-label` và `Tooltip` cập nhật theo ngữ cảnh ("Thu gọn thanh điều hướng" / "Mở rộng thanh điều hướng" trên desktop; "Mở menu điều hướng" / "Đóng menu điều hướng" trên mobile).
  - `aria-expanded` phản ánh trạng thái đóng/mở.
  - `aria-controls` trỏ tới `#main-sidebar-nav` (desktop) hoặc `#mobile-nav-drawer` (mobile).
  - Focus ring rõ ràng: `outline: 2px solid #00863A`, `outline-offset: 2px`.

### 2.4. Quy tắc Tự thu gọn khi Thao tác trong Nội dung (Desktop `>= md`)
Khi người dùng tương tác với vùng nội dung chính (`<main id="main-content">`), sidebar tự động thu gọn về 72px nhằm mở rộng tối đa không gian làm việc:
1. **Sự kiện `click`**: Kích hoạt ở sự kiện `click` (sau `mouseup`), đảm bảo phần tử đích đã tiếp nhận thao tác trước khi bố cục dịch chuyển.
2. **Chỉ chuột / chạm**: Kiểm tra `event.detail > 0` và con trỏ chuột/touch. Nhấn phím `Enter`/`Space` hoặc di chuyển tiêu điểm bằng phím `Tab` hoàn toàn **KHÔNG** làm thu gọn sidebar (đáp ứng WCAG 3.2.1 On Focus).
3. **Bôi đen văn bản an toàn**: Khi người dùng kéo chuột chọn văn bản (`window.getSelection()`), việc nhả chuột sẽ không gây thu gọn sidebar ngoài ý muốn.
4. **Phạm vi kiểm soát (DOM Containment)**: Click trong Sidebar, TopBar hoặc các hộp thoại `Dialog`, menu `Popover` (render qua React Portal ra ngoài `<main>`) hoàn toàn không làm sidebar đóng.
5. **Chống nhấp nháy chuyển động**: Không kích hoạt thu gọn khi sidebar đã ở trạng thái đóng hoặc đang trong quá trình chuyển đổi (`isTransitioningRef`).
6. **Thời gian chuyển động**: Thời lượng chuyển động ngắn mượt mà `200ms` (`0.2s cubic-bezier(0.4, 0, 0.2, 1)`). Tự động tắt hoàn toàn khi hệ điều hành kích hoạt `prefers-reduced-motion`.
7. **Đồng bộ vị trí Popover / Select**: Sau khi animation kết thúc (220ms), phát sự kiện `window.dispatchEvent(new Event('resize'))` đúng một lần để kích hoạt bộ tính toán vị trí tự động `updatePosition()` của MUI Popover/Menu, giữ cho menu thả xuống bám khít lại ô nhập.

### 2.5. Chế độ in ấn (`@media print`)
- Sidebar desktop, Mobile Drawer và TopBar đều tự động ẩn hoàn toàn (`display: none !important`).
- Vùng nội dung `<main>` chiếm toàn bộ chiều rộng trang in (`margin: 0 !important; padding: 0 !important; width: 100% !important; max-width: 100% !important;`).

---

## 3. Mẫu Component Điều hướng (Navigation Specification)

### 3.1. Danh sách và Thứ tự các mục
Hệ thống sử dụng một nguồn dữ liệu duy nhất (`navigation.tsx`) với 6 mục theo đúng thứ tự nghiệp vụ:

| Thứ tự | Khóa i18n | Nhãn tiếng Việt | Nhãn tiếng Anh | Đường dẫn | Icon component |
|---|---|---|---|---|---|
| 1 | `dashboard` | Tổng quan | Dashboard | `/` | `DashboardIcon` |
| 2 | `transactions` | Lịch sử giao dịch | Transactions | `/transactions` | `ReceiptIcon` |
| 3 | `budgets` | Ngân sách | Budgets | `/budgets` | `AccountBalanceWalletIcon` |
| 4 | `reports` | Báo cáo tài chính | Reports | `/reports` | `AssessmentIcon` |
| 5 | `saving_plans` | Kế hoạch tiết kiệm | Saving Plans | `/saving-plans` | `SavingsIcon` |
| 6 | `debts` | Vay nợ & Trả góp | Debts & Installments | `/debts` | `HandshakeIcon` |

### 3.2. Quy tắc Nhận diện Mục đang chọn (Active Route Matching)
- Trang chủ `/`: So khớp tuyệt đối `location.pathname === '/'`.
- Các trang khác: So khớp tiền tố `location.pathname.startsWith(item.path)` để nhận diện đúng cả các route con lồng nhau.
