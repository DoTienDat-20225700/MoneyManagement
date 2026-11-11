# Kiểm chứng triển khai ngày 2026-11-11

Thực hiện trên workspace hiện tại, bao gồm các thay đổi chưa commit; không phải bản GitHub cũ.
Giữ Render không seed và dùng Docker Compose cục bộ để kiểm chứng demo.

## Docker Compose thực tế

- `docker compose build backend`: thành công từ base image mới, cài dependency từ requirements.
- Build frontend và khởi động PostgreSQL/backend/frontend/scheduler: thành công.
- Cổng 5173 đang có tiến trình Node của người dùng, giữ nguyên tiến trình đó; dùng override tạm `/private/tmp/MoneyManagement-compose-smoke.override.yml` để publish frontend ở 5179.
- Truy cập demo: `http://localhost:5179`; backend: `http://localhost:8008`.
- Không xóa volume, reset tài khoản hoặc dừng container PostgreSQL kiểm thử có sẵn.

Lệnh khởi động đã dùng:

```bash
docker compose -f docker-compose.yml -f /private/tmp/MoneyManagement-compose-smoke.override.yml up -d --build
```

Lần khởi động sạch phát hiện scheduler chạy trước migration:

```text
psycopg2.errors.UndefinedTable: relation "hubModels_transactionrecurrency" does not exist
```

Đã viết test cấu hình xác nhận thất bại rồi thêm healthcheck backend và điều kiện `service_healthy`
cho scheduler/frontend. Tạo lại các container ứng dụng, giữ nguyên DB/volume, xác nhận log:

```text
Container moneymanagement_backend Healthy
Processing recurring transactions up to 2026-11-11...
Successfully generated 0 transaction(s). Deactivated 0 expired schedule(s).
```

Hai bài Playwright chạy với API và PostgreSQL thật, không mock:

1. Đăng nhập tài khoản risk qua UI; mở trang ngân sách và thấy danh mục Mua sắm;
   API trả giao dịch/ngân sách seed; dự báo 30 ngày là CRITICAL. Cookie HttpOnly được xoay;
   token refresh cũ bị từ chối; logout trả 204 và xóa cookie; tải lại trang bảo vệ quay về đăng nhập.
2. Đăng nhập tài khoản safe; dự báo 30 ngày là SAFE.

Kiểm tra trực tiếp filesystem/template loader trong container xác nhận:
`hubSettings/env.py`, `seed_demo`, `process_recurring_transactions`, template `admin/login.html`
và tệp static admin tồn tại. Không có `.env`, SQLite hay thư mục `evaluation_results` trong `/app`.
Việc tệp static admin có mặt không đồng nghĩa Gunicorn phục vụ static admin; kiểm tra CSS HTTP
phía dưới dùng runserver theo hướng dẫn dev. Frontend Docker được kiểm tra qua Nginx/UI thật.

## Cài mới theo README

Tạo bản sao backend trong `/private/tmp/MoneyManagement-clean-td17l1r1` và virtualenv Python mới,
cài đầy đủ requirements, không dùng `.env`, DB hay package Python đã cài của workspace.
Tạo `.env` từ example với SECRET_KEY sinh ngẫu nhiên chỉ trong thư mục tạm,
`DEBUG=true`, `AUTH_COOKIE_SECURE=false`, theo hướng dẫn dev HTTP.

Đã chạy migration và runserver tại cổng 8012; kiểm tra:

- API trả 200; trang admin và CSS admin trả 200.
- Host ngoài ALLOWED_HOSTS bị từ chối với 400.
- Đăng ký trả 201; đăng nhập và đọc ví mới 0.00 thành công.
- Refresh xoay cookie, JSON chỉ có access_token; logout trả 204 và không refresh được nữa.

Runserver tạm đã được tắt sau kiểm tra. Đây là môi trường Python/dependency/DB mới trên cùng máy,
không phải kiểm chứng trên một hệ điều hành mới cài.

## Render và TypeScript E2E

- Phát hiện `generateCryptoKey` không đúng khóa Blueprint; test thất bại trước khi sửa thành
  `generateValue: true` theo https://render.com/docs/blueprint-spec.
- `DEBUG=False`, `SEED_DEMO=false`, `SEED_DEMO_FORCE=false`; không deploy hoặc bật seed trên Render.
- Cài `@types/node` major 24 theo Node 24 của máy kiểm thử; thêm tsconfig E2E với Node/Vite types
  và lệnh `npm run typecheck:e2e`. Không thay đổi cấu hình TypeScript của ứng dụng.

## Trạng thái các prompt trước

- Prompt 3 đã có trong workspace: chuẩn hóa CSV theo ngày lịch, thống kê dòng bị loại,
  ngưỡng 90 ngày lịch, initial-balance; kiểm thử ở `backend/hubModels/test_forecast_backtest.py`.
- Prompt 5 đã có trong workspace: đăng ký 201, logout, rotation và blacklist;
  hợp đồng API tại `backend/auth_api.md`, test tại `backend/hubModels/test_auth_cookie.py`
  và `frontend/e2e/auth-contract.spec.ts`.
- Chưa commit/push nên các thay đổi này chưa xuất hiện trên bản GitHub đã được đối chiếu.

## Kiểm tra cuối cùng

| Lệnh | Kết quả |
|---|---|
| `cd backend && python manage.py test` | 233 test, không thất bại; bỏ qua 8 test PostgreSQL concurrency |
| `cd backend && python manage.py makemigrations --check --dry-run` | Không có migration mới |
| `cd frontend && npm run build && npm run lint` | Đạt cả hai |
| `cd frontend && npm run typecheck:e2e` | Đạt |
| Playwright trên Docker thật | 2/2 đạt |

Tệp sửa trong lần kiểm chứng này: `docker-compose.yml` (readiness), `render.yaml`
(khóa sinh secret), `frontend/package.json`, `frontend/package-lock.json`,
`frontend/e2e/tsconfig.json`, `backend/hubModels/test_deployment_config.py`,
`README.md` và báo cáo này. Các sửa đổi từ prompt trước được giữ nguyên, chưa commit/push.
