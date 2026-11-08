import { test, expect, navigateTo } from './fixtures';

test.describe('Kế hoạch tiết kiệm - Kịch bản An toàn (Saving Plans Safe)', () => {
  test('Tạo kế hoạch tiết kiệm, nạp tiền đóng góp, kiểm tra tiến độ và tự dọn dẹp', async ({
    safePage,
  }) => {
    // 1. Điều hướng tới trang Kế hoạch tiết kiệm
    await navigateTo(safePage, '/saving-plans', 'Kế hoạch tiết kiệm');
    await expect(
      safePage.getByRole('heading', { name: 'Kế hoạch tiết kiệm', exact: true })
    ).toBeVisible();

    // 2. Mở modal tạo kế hoạch tiết kiệm mới
    const planTitle = `Quỹ du lịch Đà Lạt E2E_${Date.now()}`;
    await safePage.getByRole('button', { name: /Thêm kế hoạch tiết kiệm/i }).first().click();

    const planDialog = safePage.getByRole('dialog');
    await expect(planDialog).toBeVisible();

    // Điền thông tin kế hoạch
    await planDialog.getByLabel(/Tên/i).fill(planTitle);
    await planDialog.getByLabel(/Mục tiêu tiết kiệm/i).fill('10000000');
    await planDialog.getByLabel(/Mô tả/i).fill('Mục tiêu tiết kiệm thử nghiệm E2E');
    await planDialog.getByRole('button', { name: /Thêm/i }).click();

    // 3. Xác nhận thẻ kế hoạch xuất hiện trên giao diện
    const planCard = safePage.locator('.MuiGrid-item', { hasText: planTitle });
    await expect(planCard).toBeVisible();
    await expect(planCard.getByText('10.000.000đ').first()).toBeVisible();
    await expect(planCard.getByText('0.0%')).toBeVisible();

    // 4. Nạp tiền đóng góp vào mục tiêu vừa tạo
    await planCard.getByRole('button', { name: /Thêm khoản đóng góp/i }).click();
    const contribDialog = safePage.getByRole('dialog');
    await expect(contribDialog).toBeVisible();

    await contribDialog.getByLabel(/Số tiền đóng góp/i).fill('2500000');
    await contribDialog.getByLabel(/Ghi chú đóng góp/i).fill('Nạp thử nghiệm lần 1');
    await contribDialog.getByRole('button', { name: /Thêm/i }).click();

    // 5. Kiểm tra tiến độ được cập nhật lên 25.0%
    await expect(planCard.getByText('25.0%')).toBeVisible();
    await expect(planCard.getByText('2.500.000đ')).toBeVisible();

    // 6. Tự dọn dẹp: Xoá kế hoạch tiết kiệm thử nghiệm
    await planCard.getByRole('button', { name: new RegExp(`Xoá: ${planTitle}`, 'i') }).click();
    const deleteDialog = safePage.getByRole('dialog');
    await expect(deleteDialog).toBeVisible();
    await deleteDialog.getByRole('button', { name: /Xoá kế hoạch/i }).click();

    // Xác nhận kế hoạch đã được xoá hoàn toàn khỏi danh sách
    await expect(safePage.locator('.MuiGrid-item', { hasText: planTitle })).not.toBeVisible();
  });

  test('Kiểm tra Form Validation khi tạo kế hoạch tiết kiệm không hợp lệ', async ({
    safePage,
  }) => {
    await navigateTo(safePage, '/saving-plans', 'Kế hoạch tiết kiệm');
    await safePage.getByRole('button', { name: /Thêm kế hoạch tiết kiệm/i }).first().click();

    const planDialog = safePage.getByRole('dialog');
    await expect(planDialog).toBeVisible();

    // Thử gửi form khi để trống tên
    await planDialog.getByRole('button', { name: /Thêm/i }).click();
    await expect(planDialog.getByText(/Tiêu đề phải có ít nhất 1 ký tự/i)).toBeVisible();

    // Nhập tên nhưng để trống hoặc nhập số tiền = 0
    await planDialog.getByLabel(/Tên/i).fill('Mục tiêu kiểm tra lỗi');
    await planDialog.getByLabel(/Mục tiêu tiết kiệm/i).fill('0');
    await planDialog.getByRole('button', { name: /Thêm/i }).click();
    await expect(planDialog.getByText(/Vui lòng nhập số tiền hợp lệ/i)).toBeVisible();

    // Đóng modal bằng nút đóng
    await planDialog.getByLabel('Đóng').click();
    await expect(planDialog).not.toBeVisible();
  });
});
