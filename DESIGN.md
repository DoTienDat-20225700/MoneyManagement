# Tài liệu Thiết kế Giao diện (DESIGN.md) - MoneyManagement

## 1. Hệ thống Màu sắc & Token Thiết kế Tối giản (Quy tắc 90/8/2)

Hệ thống giao diện MoneyManagement được chuẩn hoá theo quy tắc thiết kế tối giản **90/8/2**:
- **~90% Trung tính (Neutral)**: Chiếm phần lớn diện tích giao diện (nền, thẻ card, đường phân chia, chữ và số liệu thông thường).
- **~8% Xanh thương hiệu / Thu nhập (Brand Emerald & Income)**: Điểm nhấn nhận diện thương hiệu, nút hành động chính, dòng tiền dương (+), chỉ báo điều hướng.
- **~2% Cảnh báo & Trạng thái nghiêm trọng (Warning & Danger)**: Chỉ xuất hiện khi có vấn đề cần lưu ý (ngân sách tiệm cận/vượt hạn mức, nợ quá hạn, dự báo cạn dòng tiền).

### 1.1. Bảng Token Theme (Nguồn sự thật duy nhất tại `frontend/src/theme.tsx`)

| Token (`paletteTokens`) | Giá trị Hex | Key trong MUI Theme | Mục đích sử dụng |
|---|---|---|---|
| `bgDefault` | `#080808` | `palette.background.default` | Nền phẳng toàn ứng dụng (Đã loại bỏ hoàn toàn bokeh, glow, radial-gradient) |
| `bgCard` | `#121212` | `palette.background.paper` (Card, Dialog, Drawer) | Nền thẻ bề mặt, khối nội dung, modal và panel |
| `divider` | `#1E1E1E` | `palette.divider` | Viền thẻ, đường kẻ phân chia các khối và hàng bảng |
| `controlBorder` | `#5e5e5e` | `palette.outlinedBorder` | Viền input, controls chưa focus (đạt 3.09:1 WCAG Non-text) |
| `textPrimary` | `#ffffff` | `palette.text.primary` | Tiêu đề chính, nhãn quan trọng, số tiền chi tiêu (kèm dấu `-`) |
| `textSecondary` | `#9e9e9e` | `palette.text.secondary` | Nhãn phụ trợ, mô tả, đơn vị đo, trục biểu đồ (đạt 7.48:1 WCAG AA) |
| `primary` | `#00863A` | `palette.primary.main` | Nút hành động chính đặc (`contained`), focus indicator viền 2px |
| `primaryHover` | `#007030` | `palette.primary.dark` | Trạng thái hover của nút primary |
| `success` | `#48cc90` | `palette.success.main` | Chữ/icon thu nhập dương (kèm dấu `+`), thanh tiến độ bình thường |
| `warning` | `#faad14` | `palette.warning.main` | Cảnh báo mức độ tiệm cận hạn mức (approaching), nợ sắp đến hạn |
| `error` | `#ff8285` | `palette.error.main` | Cảnh báo cạn tiền (CRITICAL), nợ quá hạn (OVERDUE), vượt ngân sách |
| `info` | `#9e9e9e` | `palette.info.main` | Đưa về trung tính để MUI `severity="info"` không bị rơi vào màu xanh dương |

### 1.2. Bảng màu Biểu đồ (Chart Color Palette)
Biểu đồ tròn/phân bổ cơ cấu danh mục (`ProfileChart`) sử dụng 5 màu cố định dịu mắt + 1 màu trung tính cho phần gộp, **cố ý không dùng xanh lá, đỏ hoặc vàng** để người dùng không nhầm lẫn với màu trạng thái cảnh báo:
1. `#60A5FA` (Soft Sky Blue)
2. `#A78BFA` (Soft Purple)
3. `#22D3EE` (Soft Cyan)
4. `#F472B6` (Soft Pink)
5. `#94A3B8` (Slate Grey)
6. `#6B7280` (Màu trung tính cho nhóm gộp "Khác")

### 1.3. Các Quy tắc Bắt buộc & Mẫu thiết kế Bị cấm (Anti-patterns)

1. **Quy tắc "Một màu một nghĩa"**:
   - Màu xanh lá (`#48cc90` / `#00863A`): Chỉ biểu thị tăng trưởng thu nhập hoặc thương hiệu / hành động chính.
   - Màu đỏ (`#ff8285`): Chỉ biểu thị vượt ngân sách, nợ quá hạn, dự báo cạn dòng tiền hoặc lỗi thao tác/xóa dữ liệu. Tuyệt đối không tô đỏ số tiền chi tiêu thông thường.
2. **Quy tắc hiển thị Chi tiêu**:
   - Số tiền chi tiêu dùng màu trung tính `text.primary` (`#ffffff`) kèm dấu trừ `-` phía trước (ví dụ `-150.000 đ`).
   - Số tiền thu nhập dùng màu `success` (`#48cc90`) kèm dấu cộng `+` phía trước (ví dụ `+5.000.000 đ`).
3. **Quy tắc "Một trạng thái chỉ thể hiện ở MỘT chỗ chính" (Tránh đa lớp màu trùng lặp)**:
   - Nghiêm cấm: Một thẻ ngân sách vừa viền đỏ, vừa nền đỏ nhạt, vừa có chip đỏ, vừa có banner đỏ, vừa có text số tiền đỏ.
   - Chuẩn hoá: Trạng thái vi phạm chỉ thể hiện qua thanh tiến độ (progress bar) + MỘT tín hiệu chữ/biểu tượng không phụ thuộc màu (WCAG 1.4.1). Ví dụ: footnote "Vượt 120.000 đ" hoặc icon cảnh báo nhỏ kèm chữ.
4. **Bỏ toàn bộ Chip và Banner "An toàn / Bình thường"**:
   - Trạng thái hoạt động bình thường là trạng thái mặc định, không cần tô xanh hay gắn chip/badge "An toàn". Giảm tải triệt để nhiễu thị giác.
5. **Chip Danh mục**:
   - Dùng nền xám trung tính với một chấm tròn màu nhỏ (8px) lấy từ `label_color`. Không tô phủ toàn bộ nền chip bằng màu danh mục.
6. **Tối đa 1 nút Primary đặc (`contained`) mỗi màn hình**:
   - Mỗi màn hình chỉ có duy nhất 1 nút chính kích hoạt hành động quan trọng nhất. Các nút phụ trợ, nút lọc (filter) hoặc tab đều là `variant="outlined"` hoặc `variant="text"`.
7. **Nền phẳng (Flat Dark Background)**:
   - Đã loại bỏ 100% các lớp bokeh trang trí, ảnh nền mờ đốm nâu/xanh và gradient overlay. Sử dụng nền phẳng `paletteTokens.bgDefault` (#080808) kết hợp thẻ `bgCard` (#121212) và viền `divider` (#1E1E1E).

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
7. **Đồng bộ vị trí & Xử lý rủi ro Popover**: Lắng nghe sự kiện `transitionend` trên container nội dung chính để phát sự kiện `window.dispatchEvent(new Event('resize'))` đúng MỘT lần duy nhất sau khi animation kết thúc (khi bật `prefers-reduced-motion` thì dispatch ngay lập tức). Đặc biệt, hệ thống chủ động bỏ qua việc tự thu gọn nếu người dùng click vào phần tử kích hoạt Popup/Dropdown/Select/Menu (`[aria-haspopup]`, `[aria-expanded]`, `.MuiSelect-select`, `.MuiAutocomplete-popupIndicator`) hoặc khi đang có Modal/Menu active trong DOM, loại bỏ hoàn toàn rủi ro menu popover bị lệch tọa độ anchor.

### 2.5. Chế độ in ấn (`@media print`)
- Sidebar desktop, Mobile Drawer và TopBar đều tự động ẩn hoàn toàn (`display: none !important`).
- Vùng nội dung `<main>` chiếm toàn bộ chiều rộng trang in (`margin: 0 !important; padding: 0 !important; width: 100% !important; max-width: 100% !important;`).

### 2.6. Khắc phục lỗi cắt đáy "Danh mục cần lưu ý" (Dashboard Budget Summary)
- Danh sách các mục ngân sách cần lưu ý (`atRiskBudgets`) được chuyển sang chiều cao tự động (`height: "auto"`, loại bỏ giới hạn cứng `maxHeight: 220px`).
- **Lý do lựa chọn giải pháp chiều cao tự động**:
  - Đơn giản và tự nhiên: Thường chỉ có 1-3 danh mục tiệm cận/vượt ngưỡng, chiều cao tự động giúp hiển thị đầy đủ thẻ cảnh báo và thanh tiến độ mà không bị cắt lấp lửng ở đáy.
  - Tối ưu Accessibility: Tránh tạo ra vùng cuộn lồng nhau (nested scroll container), loại bỏ nguy cơ bẫy cuộn bàn phím (keyboard scroll trap) và không cần thêm tabIndex phụ.

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
