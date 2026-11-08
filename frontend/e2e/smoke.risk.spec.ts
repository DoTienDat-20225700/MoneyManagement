import { test, expect } from './fixtures';

test.describe('Smoke Test - Tài khoản Rủi ro (Risk Account)', () => {
  test('Đăng nhập thành công và xác nhận Dashboard', async ({ riskPage }) => {
    // riskPage đã được tự động đăng nhập và ở trang '/'
    await expect(riskPage).toHaveURL('/');

    // Xác nhận tiêu đề trang Dashboard "Tổng quan" hiển thị
    const heading = riskPage.getByRole('heading', { level: 1, name: 'Tổng quan' });
    await expect(heading).toBeVisible();

    // Xác nhận widget Số dư ví hiển thị
    await expect(riskPage.getByText('Số dư ví')).toBeVisible();

    // Xác nhận nút Thêm giao dịch hiển thị
    await expect(riskPage.getByRole('button', { name: 'Thêm giao dịch' })).toBeVisible();
  });
});
