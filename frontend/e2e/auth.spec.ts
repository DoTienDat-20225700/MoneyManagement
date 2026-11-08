import { test, expect } from '@playwright/test';
import { RISK_USER, SAFE_USER } from './constants';

test.describe('Xác thực & Quản lý phiên (Authentication Flow)', () => {
  test('Đăng nhập thành công với tài khoản Rủi ro (demo@moneymanagement.local)', async ({ page }) => {
    await page.goto('/auth/sign-in');

    // Điền thông tin đăng nhập
    await page.locator('input[type="text"]').fill(RISK_USER.email);
    await page.locator('input[type="password"]').fill(RISK_USER.password);
    await page.getByRole('button', { name: 'Đăng nhập' }).click();

    // Chờ chuyển hướng về Dashboard
    await expect(page).toHaveURL('/');
    await expect(page.getByRole('heading', { level: 1, name: 'Tổng quan' })).toBeVisible();
  });

  test('Đăng nhập thành công với tài khoản An toàn (demo.safe@moneymanagement.local)', async ({ page }) => {
    await page.goto('/auth/sign-in');

    // Điền thông tin đăng nhập
    await page.locator('input[type="text"]').fill(SAFE_USER.email);
    await page.locator('input[type="password"]').fill(SAFE_USER.password);
    await page.getByRole('button', { name: 'Đăng nhập' }).click();

    // Chờ chuyển hướng về Dashboard
    await expect(page).toHaveURL('/');
    await expect(page.getByRole('heading', { level: 1, name: 'Tổng quan' })).toBeVisible();
  });

  test('Đăng nhập thất bại khi nhập sai mật khẩu', async ({ page }) => {
    await page.goto('/auth/sign-in');

    // Nhập sai mật khẩu
    await page.locator('input[type="text"]').fill(RISK_USER.email);
    await page.locator('input[type="password"]').fill('SaiMatKhau123!');
    await page.getByRole('button', { name: 'Đăng nhập' }).click();

    // Vẫn ở lại trang đăng nhập và hiển thị thông báo lỗi (Snackbar)
    await expect(page).toHaveURL('/auth/sign-in');
    const errorAlert = page.locator('.SnackbarItem-wrappedRoot, .notistack-Snackbar, [role="alert"]').first();
    await expect(errorAlert).toBeVisible();
  });

  test('Kiểm tra xác thực dữ liệu đầu vào (Validation) của Form đăng nhập', async ({ page }) => {
    await page.goto('/auth/sign-in');

    // Bỏ trống cả 2 trường và bấm Đăng nhập
    await page.getByRole('button', { name: 'Đăng nhập' }).click();

    // Vẫn ở trang sign-in
    await expect(page).toHaveURL('/auth/sign-in');

    // Nhập email không hợp lệ
    await page.locator('input[type="text"]').fill('email-khong-hop-le');
    await page.locator('input[type="password"]').fill('123');
    await page.getByRole('button', { name: 'Đăng nhập' }).click();
    await expect(page).toHaveURL('/auth/sign-in');
  });

  test('Đăng xuất thành công và quay về trang đăng nhập', async ({ page }) => {
    // Đăng nhập trước
    await page.goto('/auth/sign-in');
    await page.locator('input[type="text"]').fill(SAFE_USER.email);
    await page.locator('input[type="password"]').fill(SAFE_USER.password);
    await page.getByRole('button', { name: 'Đăng nhập' }).click();
    await expect(page).toHaveURL('/');

    // Mở menu người dùng và click Đăng xuất
    await page.getByRole('button', { name: 'Cài đặt tài khoản' }).click();
    await page.getByRole('menuitem', { name: 'Đăng xuất' }).click();

    // Xác nhận đã chuyển hướng về trang đăng nhập
    await expect(page).toHaveURL('/auth/sign-in');
    await expect(page.getByRole('heading', { name: 'Chào mừng trở lại' })).toBeVisible();
  });

  test('Tự động chuyển hướng về /auth/sign-in khi chưa đăng nhập mà truy cập trang bảo vệ', async ({ page }) => {
    // Truy cập trực tiếp trang cần xác thực khi chưa đăng nhập
    await page.goto('/transactions');
    await expect(page).toHaveURL('/auth/sign-in');

    await page.goto('/budgets');
    await expect(page).toHaveURL('/auth/sign-in');

    await page.goto('/debts');
    await expect(page).toHaveURL('/auth/sign-in');
  });
});

