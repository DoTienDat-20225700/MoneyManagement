import { test as setup, expect } from '@playwright/test';
import fs from 'fs';
import {
  AUTH_DIR,
  RISK_STORAGE_STATE,
  SAFE_STORAGE_STATE,
  RISK_USER,
  SAFE_USER,
} from './constants';

setup('Thiết lập phiên đăng nhập cho tài khoản Demo (Risk & Safe)', async ({ browser }) => {
  // Tạo thư mục .auth nếu chưa tồn tại
  if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
  }

  // 1. Đăng nhập tài khoản Rủi ro (RISK_USER)
  const riskContext = await browser.newContext();
  const riskPage = await riskContext.newPage();
  await riskPage.goto('/auth/sign-in');

  // Điền form đăng nhập
  await riskPage.locator('input[type="text"]').fill(RISK_USER.email);
  await riskPage.locator('input[type="password"]').fill(RISK_USER.password);
  await riskPage.getByRole('button', { name: 'Đăng nhập' }).click();

  // Xác nhận đã chuyển hướng về trang chủ thành công
  await expect(riskPage).toHaveURL('/');
  await expect(riskPage.getByRole('heading', { level: 1, name: 'Tổng quan' })).toBeVisible({ timeout: 10000 });

  // Lưu storageState cho tài khoản rủi ro
  await riskPage.context().storageState({ path: RISK_STORAGE_STATE });
  await riskContext.close();

  // 2. Đăng nhập tài khoản An toàn (SAFE_USER)
  const safeContext = await browser.newContext();
  const safePage = await safeContext.newPage();
  await safePage.goto('/auth/sign-in');

  // Điền form đăng nhập
  await safePage.locator('input[type="text"]').fill(SAFE_USER.email);
  await safePage.locator('input[type="password"]').fill(SAFE_USER.password);
  await safePage.getByRole('button', { name: 'Đăng nhập' }).click();

  // Xác nhận đã chuyển hướng về trang chủ thành công
  await expect(safePage).toHaveURL('/');
  await expect(safePage.getByRole('heading', { level: 1, name: 'Tổng quan' })).toBeVisible({ timeout: 10000 });

  // Lưu storageState cho tài khoản an toàn
  await safePage.context().storageState({ path: SAFE_STORAGE_STATE });
  await safeContext.close();
});

