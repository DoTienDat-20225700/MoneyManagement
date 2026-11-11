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
python3 -m venv .venv
source .venv/bin/activate
cp .env.example .env
# Điền SECRET_KEY; chạy dev HTTP thì đặt DEBUG=true và AUTH_COOKIE_SECURE=false trong .env.
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

`docker-compose.test.yml` chỉ khởi động PostgreSQL cho kiểm thử; không có service Django cần đặt DEBUG.

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

Kiểm tra TypeScript cho toàn bộ E2E và cấu hình Playwright:

```bash
cd frontend
npm run typecheck:e2e
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

## Chạy demo (có seed dữ liệu)

Tại thư mục gốc repository:

```bash
docker compose up --build
```

Mở `http://localhost:5173`; backend tại `http://localhost:8008`.
`docker-compose.yml` dành cho demo/dev: backend đặt rõ `DEBUG=True`,
`AUTH_COOKIE_SECURE=False`, `SEED_DEMO=true`, `SEED_DEMO_FORCE=false`.
Compose có sẵn thông tin PostgreSQL và SECRET_KEY dự phòng chỉ dành cho demo;
có thể truyền SECRET_KEY riêng bằng biến môi trường hoặc tệp `.env` ở thư mục gốc.
Không dùng cấu hình Compose này cho production.
Scheduler và frontend chờ healthcheck backend đạt, tức migration và seed đã hoàn tất.

Entrypoint luôn chạy migration trước, nhưng chỉ gọi `seed_demo` khi biến môi trường
`SEED_DEMO` bằng chính xác `true`. Chỉ thêm `--force` khi đồng thời
`SEED_DEMO_FORCE=true`; bật force riêng không làm chạy seed. Các tài khoản demo đã
có sẽ không tự bị reset. Không đặt hai biến này thì mặc định không seed.

Nếu chạy trực tiếp bằng Python, sao chép `backend/.env.example` thành `backend/.env`,
điền SECRET_KEY mới, đặt `DEBUG=true`, `AUTH_COOKIE_SECURE=false` cho HTTP local,
chạy migration và chủ động tạo dữ liệu demo:

```bash
cd backend
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Hai tài khoản và mật khẩu demo nằm trong phần E2E phía trên. `GEMINI_API_KEY` là tùy
chọn, cần nếu muốn dùng nhánh đọc hóa đơn qua Gemini. Các khóa API thực chỉ đặt ở
môi trường chạy; không đưa vào repository hoặc image.

## Chạy production (không seed)

Tạo cấu hình riêng từ `backend/.env.example`, thay toàn bộ giá trị placeholder.
Các biến cần đặt cho production:

| Biến | Giá trị/yêu cầu |
|---|---|
| `SECRET_KEY` | Khóa bí mật ngẫu nhiên riêng; bắt buộc để Django khởi động |
| `DEBUG` | `false`; khi không đặt cũng mặc định false |
| `ALLOWED_HOSTS` | Các hostname thật, phân cách bằng dấu phẩy |
| `DB_ENGINE` | `postgres` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Thông tin PostgreSQL thật; hostname phải truy cập được từ container |
| `AUTH_COOKIE_SECURE` | `true` khi phục vụ bằng HTTPS; mặc định là `not DEBUG` |
| `AUTH_COOKIE_SAMESITE` | `Lax` cho triển khai cùng site; cấu hình theo kiến trúc frontend/backend thực tế |
| `SEED_DEMO`, `SEED_DEMO_FORCE` | `false` hoặc không đặt |
| `EXTRA_CORS_ORIGINS` | Đặt origin frontend HTTPS nếu frontend chạy khác origin |
| `GEMINI_API_KEY` | Tùy chọn, cần cho nhánh xử lý hóa đơn qua Gemini |
| `VITE_API_URL` | Đặt lúc build frontend, trỏ đến API production; dùng `/api` khi có reverse proxy cùng origin |

Ví dụ build và chạy backend tại thư mục gốc sau khi đã điền cấu hình, chuẩn bị
PostgreSQL và HTTPS/reverse proxy:

```bash
docker build -t moneymanagement-backend ./backend
docker run --env-file backend/.env -p 8008:8008 moneymanagement-backend
```

`backend/.env.example` không chứa bí mật thật. `.dockerignore` loại các tệp `.env`,
SQLite, cache, `evaluation_results` và `node_modules`; Dockerfile chỉ sao chép
`manage.py`, entrypoint và ba package runtime `hubAPI`, `hubModels`, `hubSettings`.
Image không nhúng cấu hình môi trường; truyền biến khi chạy container.

Parser DEBUG và AUTH_COOKIE_SECURE nhận `true/false/1/0/yes/no`, không phân biệt
hoa thường và bỏ khoảng trắng đầu/cuối. Giá trị khác, kể cả `release` hoặc chuỗi
rỗng, làm khởi động thất bại với thông báo rõ tên biến; không tự chuyển thành false.

**Render:** `render.yaml` đặt `DEBUG=False`, cookie secure và hai biến seed bằng
false. Deploy không tự tạo tài khoản/dữ liệu demo. Nếu muốn chạy demo trên Render,
cần quyết định riêng; seed trong chế độ DEBUG=false cần chủ động bật cả
`SEED_DEMO=true` và `SEED_DEMO_FORCE=true` để vượt chặn của lệnh seed.
Thay đổi này không triển khai hay bật demo trên Render.

## 🧑‍💻 Thông Tin Tác Giả (Author)

- **Họ và tên**: Đỗ Tiến Đạt
- **Mã số sinh viên (MSSV)**: 20225700
- **Trường**: Đại học Bách Khoa Hà Nội (HUST)
- **GitHub**: [@DoTienDat-20225700](https://github.com/DoTienDat-20225700)
- **Email**: [dat.dt225700@sis.hust.edu.vn](mailto:dat.dt225700@sis.hust.edu.vn)

---

## 📄 License

Dự án được phát triển phục vụ mục đích học tập và nghiên cứu cá nhân.
