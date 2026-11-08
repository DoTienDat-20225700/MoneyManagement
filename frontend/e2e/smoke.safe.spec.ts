import { test, expect } from './fixtures';

test.describe('Smoke Test - Tài khoản An toàn (Safe Account)', () => {
  test('Đăng nhập thành công và xác nhận Dashboard', async ({ safePage }) => {
    // safePage đã được tự động đăng nhập và ở trang '/'
    await expect(safePage).toHaveURL('/');

    // Xác nhận tiêu đề trang Dashboard "Tổng quan" hiển thị
    const heading = safePage.getByRole('heading', { level: 1, name: 'Tổng quan' });
    await expect(heading).toBeVisible();

    // Xác nhận widget Số dư ví hiển thị
    await expect(safePage.getByText('Số dư ví')).toBeVisible();

    // Xác nhận nút Thêm giao dịch hiển thị
    await expect(safePage.getByRole('button', { name: 'Thêm giao dịch' })).toBeVisible();
  });
});
