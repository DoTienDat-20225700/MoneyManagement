# MoneyManagement - Ứng Dụng Quản Lý Chi Tiêu Cá Nhân (FinancialHub)

![FinancialHub Dashboard](https://github.com/isabellaaquino/financialhub/assets/76221367/7b7dc6e9-4279-4fff-9e19-04b4394252e9)

## 📌 Tổng Quan (Overview)

**MoneyManagement (FinancialHub)** là ứng dụng web quản lý tài chính cá nhân toàn diện được xây dựng bằng **Django** (Backend) và **React.js** (Frontend). Hệ thống cung cấp giải pháp trực quan, thân thiện giúp người dùng theo dõi các khoản thu chi, quản lý dòng tiền, lập kế hoạch tiết kiệm và phân tích xu hướng tài chính thông qua biểu đồ phân tích.

---

## ✨ Tính Năng Nổi Bật (Key Features)

### 1. Quản lý Giao dịch (Transaction Management) 💸

- Thêm mới, chỉnh sửa và quản lý các giao dịch thu nhập (Earnings) và chi tiêu (Expenses).
- Ghi nhận chi tiết: ngày giao dịch, số tiền, mô tả và phân loại danh mục.
- Tùy chỉnh các nhãn (Labels) cá nhân hóa để lọc và tìm kiếm giao dịch nhanh chóng.
- Hỗ trợ nhập hóa đơn (Invoice import).

### 2. Thống Kê & Phân Tích Tài Chính (Financial Analytics) 📈

- Biểu đồ tương tác trực quan hóa thu nhập và chi tiêu theo tuần/tháng/năm.
- Phân tích cơ cấu chi tiêu theo từng danh mục dưới dạng biểu đồ tròn (Pie chart) và biểu đồ cột.
- Theo dõi xu hướng tài chính và đưa ra đánh giá thói quen chi tiêu.

### 3. Kế Hoạch Tiết Kiệm (Saving Plans) 🐖

- Thiết lập các mục tiêu tiết kiệm cá nhân hóa với số tiền và thời hạn cụ thể.
- Theo dõi tiến độ hoàn thành mục tiêu tiết kiệm trực quan.

---

## 🛠️ Công Nghệ Sử Dụng (Tech Stack)

- **Backend**: Python 3, Django, Django REST Framework
- **Frontend**: React.js, HTML5, CSS3, JavaScript
- **Database**: SQLite (phát triển) / PostgreSQL
- **Tools**: Git, GitHub CLI, npm, pip

---

## ⚙️ Hướng Dẫn Cài Đặt & Chạy Ứng Dụng (Installation)

### 1. Clone repository

```bash
git clone https://github.com/DoTienDat-20225700/MoneyManagement.git
cd MoneyManagement
```

### 2. Cài đặt Backend (Django)

```bash
cd backend
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

Backend sẽ khởi chạy tại: `http://127.0.0.1:8000`

### 3. Cài đặt Frontend (React)

Mở một terminal mới:

```bash
cd frontend
npm install
npm run dev
```

Frontend sẽ khởi chạy tại: `http://localhost:5173`

### 4. Chạy Kiểm Thử Đồng Thời (Concurrency Tests) với PostgreSQL

Mặc định test suite chạy trên SQLite (`python manage.py test`). Để chạy kiểm thử đồng thời trên PostgreSQL:
```bash
docker compose -f docker-compose.test.yml up -d
TEST_DB=postgres python manage.py test hubModels.test_concurrency_postgres
```

### 5. Chạy Kiểm Thử End-to-End (E2E Tests với Playwright) 🎭

Dự án cung cấp bộ kiểm thử End-to-End toàn diện bao phủ các kịch bản RỦI RO (Stressed) và AN TOÀN (Safe) của ứng dụng.

#### Cài đặt trình duyệt Playwright:
```bash
cd frontend
npx playwright install chromium
```

#### Chạy toàn bộ test suite E2E:
```bash
cd frontend
npm run test:e2e
```

#### Chạy E2E với giao diện trực quan (Playwright UI Mode):
```bash
cd frontend
npm run test:e2e:ui
```

#### Thông tin môi trường E2E:
- **Hạ tầng cổng độc lập**: Quá trình chạy test E2E hoàn toàn tự động khởi động và cô lập trên cổng riêng, không gây xung đột với môi trường dev thông thường:
  - **Backend E2E**: `http://127.0.0.1:8001` (Sử dụng cấu hình `backend/hubSettings/settings_e2e.py` và cơ sở dữ liệu riêng `backend/db_e2e.sqlite3`). Tự động `migrate` và `seed_demo --reset --yes` trước khi chạy.
  - **Frontend E2E**: `http://localhost:5174` (Khởi chạy Vite với `VITE_API_URL=http://127.0.0.1:8001/api`).
- **Tài khoản Demo E2E (Mật khẩu chung: `Demo@12345`)**:
  - `demo@moneymanagement.local`: **Kịch bản Rủi ro** (Ngân sách Mua sắm vượt hạn mức 125%, có nợ quá hạn, dự báo dòng tiền 30 ngày ở mức `CRITICAL` và chạm đáy âm).
  - `demo.safe@moneymanagement.local`: **Kịch bản An toàn** (Chi tiêu dưới 60% hạn mức, hợp đồng vay nợ đúng hạn, dự báo dòng tiền luôn ở mức `SAFE`).
- **Cơ chế phiên đăng nhập**: Sử dụng Playwright Fixtures (`riskPage` và `safePage`) tự động hóa quá trình đăng nhập và cô lập phiên theo từng kịch bản kiểm thử, đảm bảo tính bền vững và khả năng tái lập độc lập.


---

## 🧑‍💻 Thông Tin Tác Giả (Author)

- **Họ và tên**: Đỗ Tiến Đạt
- **Mã số sinh viên (MSSV)**: 20225700
- **Trường**: Đại học Bách Khoa Hà Nội (HUST)
- **GitHub**: [@DoTienDat-20225700](https://github.com/DoTienDat-20225700)
- **Email**: [dat.dt225700@sis.hust.edu.vn](mailto:dat.dt225700@sis.hust.edu.vn)

---

## 📄 License

Dự án được phát triển phục vụ mục đích học tập và nghiên cứu cá nhân.
