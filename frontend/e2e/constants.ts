import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Thông tin tài khoản demo dùng cho kiểm thử E2E.
 * Mật khẩu và email có thể ghi đè thông qua biến môi trường.
 */
export const DEMO_PASSWORD = process.env.E2E_PASSWORD || 'Demo@12345';

export const RISK_USER = {
  email: process.env.E2E_RISK_EMAIL || 'demo@moneymanagement.local',
  password: DEMO_PASSWORD,
  name: 'Minh Anh Nguyễn',
  role: 'stressed',
};

export const SAFE_USER = {
  email: process.env.E2E_SAFE_EMAIL || 'demo.safe@moneymanagement.local',
  password: DEMO_PASSWORD,
  name: 'Quốc Bảo Trần',
  role: 'safe',
};

// Đường dẫn lưu trữ trạng thái phiên đăng nhập (storageState)
export const AUTH_DIR = path.join(__dirname, '.auth');
export const RISK_STORAGE_STATE = path.join(AUTH_DIR, 'risk.json');
export const SAFE_STORAGE_STATE = path.join(AUTH_DIR, 'safe.json');

// Cấu hình cổng cho môi trường E2E
export const E2E_FRONTEND_PORT = 5174;
export const E2E_BACKEND_PORT = 8001;
export const E2E_BASE_URL = `http://localhost:${E2E_FRONTEND_PORT}`;
export const E2E_API_URL = `http://127.0.0.1:${E2E_BACKEND_PORT}/api`;

