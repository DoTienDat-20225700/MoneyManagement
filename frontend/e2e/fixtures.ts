import { test as base, expect, Page } from '@playwright/test';
import { RISK_USER, SAFE_USER } from './constants';

type WorkerFixtures = {};
type TestFixtures = {
  riskPage: Page;
  safePage: Page;
};

/**
 * Fixtures tùy biến cho MoneyManagement E2E.
 * Vì React app lưu access token trong bộ nhớ state (AuthContext) và refresh token
 * qua cookie giữa 2 origin khác nhau (localhost:5174 vs 127.0.0.1:8001), việc phục hồi
 * phiên qua storageState giữa các process context độc lập gặp hạn chế.
 * Fixtures `riskPage` và `safePage` tự động thực hiện đăng nhập nhanh trước mỗi test,
 * đảm bảo trạng thái xác thực 100% tin cậy và độc lập cho từng kịch bản.
 */
export const test = base.extend<TestFixtures, WorkerFixtures>({
  riskPage: async ({ page }, use) => {
    // Điều hướng đến trang đăng nhập
    await page.goto('/auth/sign-in');

    // Điền thông tin tài khoản Rủi ro
    await page.locator('input[type="text"]').fill(RISK_USER.email);
    await page.locator('input[type="password"]').fill(RISK_USER.password);
    await page.getByRole('button', { name: 'Đăng nhập' }).click();

    // Chờ điều hướng về trang chủ và hoàn tất render
    await expect(page).toHaveURL('/');
    await expect(page.getByRole('heading', { level: 1, name: 'Tổng quan' })).toBeVisible({ timeout: 10000 });

    // Cung cấp page đã xác thực cho test
    await use(page);
  },

  safePage: async ({ page }, use) => {
    // Điều hướng đến trang đăng nhập
    await page.goto('/auth/sign-in');

    // Điền thông tin tài khoản An toàn
    await page.locator('input[type="text"]').fill(SAFE_USER.email);
    await page.locator('input[type="password"]').fill(SAFE_USER.password);
    await page.getByRole('button', { name: 'Đăng nhập' }).click();

    // Chờ điều hướng về trang chủ và hoàn tất render
    await expect(page).toHaveURL('/');
    await expect(page.getByRole('heading', { level: 1, name: 'Tổng quan' })).toBeVisible({ timeout: 10000 });

    // Cung cấp page đã xác thực cho test
    await use(page);
  },
});

/**
 * Helper điều hướng an toàn trong ứng dụng MoneyManagement.
 * Tự động mở rộng sidebar nếu đang ở trạng thái thu gọn.
 */
export async function navigateTo(page: Page, path: string, linkName: string) {
  const expandBtn = page.getByLabel('Mở rộng thanh điều hướng').or(page.getByLabel('Expand navigation bar'));
  if (await expandBtn.isVisible()) {
    await expandBtn.click();
    await page.waitForTimeout(200);
  }
  const link = page.getByRole('link', { name: linkName });
  await expect(link).toBeVisible({ timeout: 5000 });
  await link.click();
  await page.waitForURL(`**${path}`);
}

export { expect };
