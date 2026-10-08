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
python manage.py migrate
python manage.py runserver
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
