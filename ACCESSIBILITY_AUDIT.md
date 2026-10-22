# Báo cáo Kiểm thử Tiếp cận (ACCESSIBILITY_AUDIT.md) - MoneyManagement

## 1. Mục tiêu & Tiêu chuẩn Kiểm định
Kiểm định toàn diện thành phần điều hướng Sidebar mới theo tiêu chuẩn **WCAG 2.2 Cấp độ AA** (Web Content Accessibility Guidelines 2.2 Level AA).

---

## 2. Kết quả Đo lường Độ tương phản Màu (WCAG 1.4.3 & 1.4.11)
Kết quả trích xuất trực tiếp từ bộ công cụ kiểm thử tự động `npm run a11y:contrast`:

| Thành phần / Cặp màu kiểm tra | Màu tiền cảnh (FG) | Màu hậu cảnh (BG) | Tỷ lệ đo được | Yêu cầu WCAG | Trạng thái |
|---|---|---|---|---|---|
| **Chữ mục chưa chọn** trên nền Sidebar | `#9e9e9e` | `#0d0e12` | **7.20 : 1** | >= 4.5 : 1 (AA Chữ nhỏ) | ✅ ĐẠT (Đạt cả AAA) |
| **Chữ mục đang chọn** trên nền active | `#48cc90` | `rgba(0,134,58,0.14)` trên `#0d0e12` | **8.43 : 1** | >= 4.5 : 1 (AA Chữ nhỏ) | ✅ ĐẠT (Đạt cả AAA) |
| **Chỉ báo mục đang chọn (Indicator bar)** | `#48cc90` | `#0d0e12` | **9.48 : 1** | >= 3.0 : 1 (UI Component) | ✅ ĐẠT |
| **Icon nút hamburger trên thanh trên** | `#e0e0e0` | `#0d0e12` | **14.61 : 1** | >= 3.0 : 1 (UI Component) | ✅ ĐẠT (Đạt cả AAA) |
| **Icon nút hamburger khi hover** | `#ffffff` | `rgba(255,255,255,0.06)` trên `#0d0e12` | **16.99 : 1** | >= 3.0 : 1 (UI Component) | ✅ ĐẠT |
| **Vòng focus nút hamburger (`:focus-visible`)** | `#00863A` | `#0d0e12` | **4.11 : 1** | >= 3.0 : 1 (Focus Indicator) | ✅ ĐẠT |
| **Chữ `text.secondary` trên thẻ `bgCard`** | `#9e9e9e` | `#121212` | **6.67 : 1** | >= 4.5 : 1 (AA Chữ nhỏ) | ✅ ĐẠT |
| **Chữ cảnh báo `error.main` trên `bgCard`** | `#ff8285` | `#121212` | **7.47 : 1** | >= 4.5 : 1 (AA Chữ nhỏ) | ✅ ĐẠT |
| **Chữ thu nhập `success.main` trên `bgCard`** | `#48cc90` | `#121212` | **8.78 : 1** | >= 4.5 : 1 (AA Chữ nhỏ) | ✅ ĐẠT |
| **Các màu biểu đồ Chart (1-5) trên `bgCard`** | `#60A5FA`..`#94A3B8` | `#121212` | **6.89:1 - 10.15:1** | >= 3.0 : 1 (Graphical Object) | ✅ ĐẠT |
| **Màu biểu đồ Khác (`#6B7280`) trên `bgCard`** | `#6B7280` | `#121212` | **3.88 : 1** | >= 3.0 : 1 (Graphical Object) | ✅ ĐẠT |
| **Viền controls OutlinedInput** | `#5e5e5e` | `#080808` | **3.09 : 1** | >= 3.0 : 1 (UI Border) | ✅ ĐẠT |
| **Track LinearProgress** | `rgba(255,255,255,0.36)` | `#2b2b2b` | **3.32 : 1** | >= 3.0 : 1 (Graphical Object) | ✅ ĐẠT |

> **Tổng kết bộ test tương phản**: Đạt **63 / 63** cặp kiểm tra (0 lỗi, 100% đạt chuẩn WCAG 2.2 AA).

### 2.1. Đảm bảo Không Sử dụng Màu sắc Đơn độc (Use of Color - SC 1.4.1)
- **Số tiền**: Chi tiêu mang dấu trừ `-` kèm tiền tệ `đ`; thu nhập mang dấu cộng `+`.
- **Ngân sách vượt mức**: Ngoài thanh tiến độ màu đỏ, hệ thống bổ sung văn bản hiển thị rõ ràng số tiền chênh lệch (ví dụ: `"Vượt 250.000 đ"`).
- **Sổ nợ**: Trạng thái quá hạn (`OVERDUE`) hoặc sắp đến hạn (`ACTIVE`) đi kèm chip chữ và ngày hết hạn cụ thể, không chỉ dựa vào màu sắc.
- **Biểu đồ danh mục**: Bổ sung tooltip chi tiết và nhãn tên danh mục, danh mục "Khác" hiển thị rõ tên thay vì chỉ phụ thuộc vào mã màu xám.

---

## 3. Đánh giá Theo từng Tiêu chuẩn WCAG 2.2 AA

### 3.1. Phím tắt bỏ qua khối điều hướng (Bypass Blocks - SC 2.4.1)
- **Cơ chế**: Thêm phần tử Skip Link `<Box component="a" href="#main-content">` nằm ngay đầu cây DOM.
- **Hành vi**: Mặc định ẩn ở vị trí `top: -100px`. Khi người dùng nhấn `Tab`, phần tử trượt xuống vị trí `top: 16px, left: 16px`, nền xanh `#00863A`, viền focus trắng 2px. Khi nhấn `Enter`, focus chuyển thẳng vào `<main id="main-content">` (được gắn `tabIndex={-1}`).

### 3.2. Cấu trúc ngữ nghĩa & Vùng điều hướng (Info and Relationships - SC 1.3.1)
- Thành phần sidebar và mobile drawer được đánh dấu bằng thẻ HTML5 ngữ nghĩa `<nav>`.
- Sidebar desktop có ID `#main-sidebar-nav` và `aria-label="Điều hướng chính"` (tiếng Anh: `"Main navigation"`).
- Drawer di động có ID `#mobile-nav-drawer` và `aria-label="Điều hướng trên di động"` (tiếng Anh: `"Mobile navigation"`).
- Icon trang trí trong các mục điều hướng được gắn cờ `aria-hidden="true"` để trình đọc màn hình không đọc thừa ký tự icon.

### 3.3. Trạng thái phần tử & Tên truy cập (Name, Role, Value - SC 4.1.2)
- **Mục đang hoạt động**: Tự động nhận thuộc tính `aria-current="page"` khi đường dẫn hiện tại khớp với mục đó.
- **Nút Hamburger duy nhất ở thanh trên**: Có `aria-expanded` (phản ánh trạng thái mở/đóng) và `aria-controls` trỏ tới `#main-sidebar-nav` (trên desktop) hoặc `#mobile-nav-drawer` (trên mobile). Tên truy cập đổi linh hoạt theo trạng thái ("Thu gọn thanh điều hướng" / "Mở rộng thanh điều hướng" trên desktop; "Mở menu điều hướng" / "Đóng menu điều hướng" trên mobile).
- **Trạng thái thu gọn (72px)**: Mỗi item đều được bọc trong `<Tooltip title={label} placement="right">` hỗ trợ hiển thị cả khi di chuột và khi focus bằng bàn phím (`disableFocusListener={false}`). Ngoài ra, `aria-label={label}` được gắn trực tiếp vào button.

### 3.4. Không thay đổi ngữ cảnh khi nhận Focus (On Focus - SC 3.2.1)
- Thao tác di chuyển tiêu điểm bằng phím `Tab`, hoặc kích hoạt nút/link bằng phím `Enter`/`Space` (`event.detail === 0`) trong vùng nội dung **tuyệt đối không làm sidebar thu gọn**.
- Chỉ các thao tác click/chạm có chủ đích bằng chuột hoặc cảm ứng (`event.detail > 0`) mới kích hoạt tự động thu gọn.

### 3.5. Bẫy Focus & Điều khiển Bàn phím trên Mobile (Keyboard Navigation - SC 2.1.1, 2.1.2)
- Khi mở Drawer trên mobile, tiêu điểm bàn phím tự động chuyển vào bên trong Drawer (focus trap được quản lý bởi MUI Dialog/Drawer).
- Nhấn phím `Escape` hoặc chọn một mục điều hướng sẽ đóng Drawer ngay lập tức.
- Khi Drawer đóng, tiêu điểm bàn phím tự động được hoàn trả về nút hamburger ban đầu thông qua `hamburgerRef.current.focus()`.

### 3.6. Kích thước Vùng tương tác Cảm ứng (Target Size Minimum - SC 2.5.8)
- Nút hamburger trên thanh trên đạt kích thước `40x40px` (chuẩn tiếp cận).
- Trên mobile Drawer, tất cả các mục điều hướng đạt chiều cao tối thiểu `minHeight: 48px` (vượt yêu cầu 24x24px của 2.5.8 và đạt mức tối ưu 44x44px của AAA 2.5.5).
- Nút chuyển đổi ngôn ngữ đạt kích thước `>= 40px`.

### 3.7. Giảm thiểu Chuyển động (Animation from Interactions - SC 2.3.3)
- Tích hợp hook `usePrefersReducedMotion()`.
- Khi người dùng bật cài đặt "Reduce motion" trên hệ điều hành, tất cả các thuộc tính animation/transition chuyển đổi độ rộng sidebar và margin vùng nội dung tự động chuyển thành `"none"`.
- Sự kiện co giãn biểu đồ (`window.dispatchEvent(new Event('resize'))`) được kích hoạt thông qua sự kiện trình duyệt `transitionend` đúng một lần duy nhất, hoặc kích hoạt tức thì khi bật `prefers-reduced-motion`.

### 3.8. Loại bỏ Bẫy cuộn Nội dung (No Keyboard Scroll Traps - SC 2.1.2)
- Danh sách cảnh báo ngân sách ở Dashboard được đặt chiều cao tự động (`height: "auto"`) thay vì cố định `maxHeight: 220px`.
- Toàn bộ các danh mục tiệm cận/vượt hạn mức hiển thị đầy đủ, không bị cắt cụt mục ở đáy ("Ăn uống"), đồng thời loại bỏ vùng cuộn lồng nhau (nested scrollbar) gây khó khăn cho việc điều hướng bằng phím Tab hoặc mũi tên.

### 3.9. Thứ bậc Tiêu đề Liền mạch (Heading Hierarchy - SC 1.3.1 - A11Y-014)
- Loại bỏ hoàn toàn hiện tượng nhảy cóc tiêu đề từ `h1` sang `h5` hoặc `h6` tại `Budgets.tsx` và `Reports.tsx`.
- Thẻ HTML5 được phân cấp nghiêm ngặt:
  - `component="h1"`: Tiêu đề trang duy nhất (`"Quản lý ngân sách"`, `"Báo cáo tài chính"`).
  - `component="h2"`: Các khối chức năng chính (`"Danh sách ngân sách danh mục"`, `"Giao dịch trong kỳ"`, các thẻ chỉ số KPI tổng).
  - Header in ấn (`.print-only`) chuyển sang `component="div"`, không đưa thẻ `<h5>`/`<h6>` vào cây phân cấp tài liệu.
- **Kiểm chứng Computed Style**: Do MUI áp dụng kiểu dáng qua các class `.MuiTypography-[variant]` chứ không gắn vào thẻ HTML tag selector, việc khai báo `component="h2"` với `variant="h6"` giữ nguyên 100% computed style:
  - `font-size`: `1.25rem` (20px)
  - `font-weight`: `600`
  - `line-height`: `1.6`
  - `margin`: `mb={1.5}` (12px)

### 3.10. Nhãn Tiếp cận Thao tác Hàng loạt (Label in Name - SC 2.5.3 - A11Y-015)
- Tính năng chọn và xóa hàng loạt giao dịch tại `LatestTransactions.tsx` hiển thị thanh thao tác với nhãn rõ ràng có số lượng:
  - `1 mục`: `"Xoá 1 giao dịch"` (tiếng Anh: `"Delete 1 transaction"`).
  - `N mục`: `"Xoá {count} giao dịch"` (tiếng Anh: `"Delete {count} transactions"`).
- Thuộc tính `aria-label` trên nút xóa hàng loạt khớp chính xác từng từ với văn bản hiển thị (`aria-label={bulkDeleteLabel}` chứa `bulkDeleteLabel`), đáp ứng hoàn toàn tiêu chuẩn WCAG 2.5.3 (Label in Name).
- Bổ sung hộp thoại xác nhận xóa hàng loạt với văn bản cảnh báo có tham số số lượng và nút xác nhận có nhãn truy cập đồng bộ.

### 3.11. ApexCharts Hỗ trợ Tôn trọng Cài đặt Giảm chuyển động (Animation from Interactions - SC 2.3.3 - A11Y-016)
- Tích hợp hook dùng chung `usePrefersReducedMotion()` vào tất cả các cấu hình ApexCharts trong toàn bộ dự án:
  1. `ProfileChart.tsx` (Biểu đồ phân bổ chi tiêu - Donut/Pie)
  2. `CurrentMonthChart.tsx` (Biểu đồ chi tiêu theo ngày - Bar)
  3. `CashFlowForecast.tsx` (Biểu đồ dự báo dòng tiền 30/60/90 ngày - Area)
  4. `Reports.tsx` (`monthlyTrendsChart` - Bar và `categoryBreakdownChart` - Pie)
- Khi người dùng bật tùy chọn "Reduce motion" trong hệ điều hành:
  - `chart.animations.enabled = false` (tắt toàn bộ hiệu ứng vẽ biểu đồ ban đầu và hiệu ứng co giãn).
  - `chart.animations.dynamicAnimation.enabled = false`.
  - Giúp người dùng mắc chứng rối loạn tiền đình (vestibular disorder) hoặc nhạy cảm với chuyển động không bị chóng mặt hay phân tâm.

---

## 4. Kết quả Thực thi Unit Test Tự động
Bộ test Node.js tích hợp sẵn (`node --test scripts/contrast.test.mjs`):
- `✔ Contrast Math - Standard boundary calculations`
- `✔ Color Token: text.secondary (#9e9e9e) meets WCAG 2.2 AA (>= 4.5:1)`
- `✔ Color Token: error.main / Expense red (#ff8285) meets WCAG 2.2 AA (>= 4.5:1)`
- `✔ UI Component: OutlinedInput border (#5e5e5e) meets WCAG 2.2 Non-text contrast (>= 3.0:1)`
- `✔ Graphical Object: LinearProgress track (rgba(255,255,255,0.36)) meets WCAG 2.2 (>= 3.0:1)`
- `✔ Focus Indicator: :focus-visible outline (#00863A) meets WCAG 2.2 AA non-text contrast (>= 3.0:1)`
- `✔ Reduced Motion (WCAG 2.3.3): matchMedia event listener lifecycle & fallback logic`
- `✔ Heading Typography (WCAG 1.3.1): Semantic component prop preserves identical computed style`
- `✔ Sidebar Contrast: Unselected item text (#9e9e9e) on Sidebar (#0d0e12) meets WCAG 2.2 AA (>= 4.5:1)`
- `✔ Sidebar Contrast: Selected item text (#48cc90) on Active bg over Sidebar meets WCAG 2.2 AA (>= 4.5:1)`
- `✔ Sidebar Contrast: Active indicator (#48cc90) on Sidebar meets WCAG 2.2 Non-text (>= 3.0:1)`
- `✔ Sidebar Contrast: Collapse button icon (#9e9e9e) and hover state (#ffffff) meet WCAG 2.2 AA`
- `✔ Navigation Logic: aria-current matching correctly handles exact root and sub-routes`
- `✔ Sidebar Contrast: Hamburger button icon (#e0e0e0) and focus outline meet WCAG 2.2 Non-text (>= 3.0:1)`
- `✔ Navigation State: Default state is OPEN without localStorage read/write`
- `✔ Navigation Logic: Content click-to-collapse rules`
- `✔ Route Isolation: AuthRoot and unauthenticated routes do not include AppDrawer`
- `✔ A11Y-014: Heading hierarchy strictly structured without h1->h5 jump`
- `✔ A11Y-015: Bulk delete button satisfies WCAG 2.5.3 and includes item count in name and visible label`
- `✔ A11Y-016: ApexCharts configurations respect prefers-reduced-motion`

**Tổng: 20 / 20 tests passed (100%)**.

