import { test, expect, navigateTo } from './fixtures';

test.describe('Vay nợ & Trả góp - Kịch bản An toàn (Debts Safe)', () => {
  test('Không có nợ quá hạn và kiểm tra hợp đồng nợ an toàn', async ({ safePage }) => {
    // Điều hướng sang trang Vay nợ & Trả góp
    await navigateTo(safePage, '/debts', 'Vay nợ & Trả góp');

    // Xác nhận tiêu đề trang
    await expect(safePage.getByRole('heading', { level: 1, name: 'Quản lý Vay nợ, Cho vay & Trả góp' })).toBeVisible();

    // 1. Kiểm tra thống kê: Khoản đã quá hạn = 0
    const overdueStat = safePage.locator('.MuiGrid-item').filter({ hasText: 'Khoản đã quá hạn' });
    await expect(overdueStat).toBeVisible();
    await expect(overdueStat).toContainText('0');
    await expect(safePage.locator('[role="alert"]')).toHaveCount(0);

    // 2. Tab Cho vay: Kiểm tra hợp đồng cho Đức (Bạn thân) mượn 5.000.000đ
    await expect(safePage.getByText('Đức (Bạn thân)')).toBeVisible();
    await expect(safePage.getByText('5.000.000đ').first()).toBeVisible();

    // 3. Tab Mua trả góp: Kiểm tra hợp đồng Apple Watch
    const tabTraGop = safePage.locator('button[role="tab"]').filter({ hasText: 'Mua trả góp' });
    await tabTraGop.click();
    await expect(safePage.getByText('Apple Store (Apple Watch)')).toBeVisible();
  });

  test('Ghi nhận một lần trả nợ và một lần trả góp, kiểm tra số dư còn lại giảm đúng và tự dọn dẹp', async ({ safePage }) => {
    await navigateTo(safePage, '/debts', 'Vay nợ & Trả góp');

    // --- 1. Cho vay: Ghi nhận thanh toán 1.000.000đ cho Đức (Bạn thân) ---
    const tabChoVay = safePage.locator('button[role="tab"]').filter({ hasText: 'Cho vay' });
    await tabChoVay.click();

    const ducCard = safePage.locator('.MuiGrid-item').filter({ hasText: 'Đức (Bạn thân)' }).first();
    await expect(ducCard).toBeVisible();
    await expect(ducCard).toContainText('5.000.000đ');

    // Bấm nút "Thanh toán"
    await ducCard.getByRole('button', { name: 'Thanh toán' }).click();
    const payDialog = safePage.locator('div[role="dialog"]');
    await expect(payDialog).toBeVisible();

    // Điền số tiền 1.000.000đ
    const amountInput = payDialog.getByLabel('Số tiền thanh toán');
    await amountInput.clear();
    await amountInput.fill('1000000');

    // Bấm nút "Lưu"
    await payDialog.getByRole('button', { name: 'Lưu' }).click();
    await expect(payDialog).toBeHidden();

    // Kiểm tra số dư còn lại giảm xuống 4.000.000đ, đã thu tăng lên 1.000.000đ
    await expect(ducCard).toContainText('4.000.000đ');
    await expect(ducCard).toContainText('1.000.000đ');

    // --- 2. Mua trả góp: Ghi nhận thanh toán 1.500.000đ cho Apple Store ---
    const tabTraGop = safePage.locator('button[role="tab"]').filter({ hasText: 'Mua trả góp' });
    await tabTraGop.click();

    const watchCard = safePage.locator('.MuiGrid-item').filter({ hasText: 'Apple Store (Apple Watch)' }).first();
    await expect(watchCard).toBeVisible();
    await expect(watchCard).toContainText('4.500.000đ');

    // Bấm nút "Thanh toán"
    await watchCard.getByRole('button', { name: 'Thanh toán' }).click();
    await expect(payDialog).toBeVisible();

    const watchAmountInput = payDialog.getByLabel('Số tiền thanh toán');
    await watchAmountInput.clear();
    await watchAmountInput.fill('1500000');

    await payDialog.getByRole('button', { name: 'Lưu' }).click();
    await expect(payDialog).toBeHidden();

    // Kiểm tra số dư còn lại giảm xuống 3.000.000đ, đã trả tăng lên 3.000.000đ
    await expect(watchCard).toContainText('3.000.000đ');

    // --- 3. Dọn dẹp dữ liệu: Xoá các payment vừa ghi nhận để phục hồi số dư ban đầu ---
    // Xoá payment ở Apple Store
    await watchCard.getByRole('button', { name: 'Chi tiết' }).click();
    const drawer = safePage.locator('.MuiDrawer-root:not(#mobile-nav-drawer)');
    await expect(drawer).toBeVisible();

    // Tìm nút xoá lần thanh toán 1.500.000đ trong lịch sử
    const deleteWatchPaymentBtn = drawer.locator('button[aria-label*="Xoá: 1.500.000"]').first();
    await expect(deleteWatchPaymentBtn).toBeVisible();
    await deleteWatchPaymentBtn.click();

    // Xác nhận trong dialog xoá thanh toán
    const confirmDeleteDialog = safePage.locator('div[role="dialog"]');
    await expect(confirmDeleteDialog).toBeVisible();
    await confirmDeleteDialog.getByRole('button', { name: 'Xoá thanh toán' }).click();
    await expect(confirmDeleteDialog).toBeHidden();

    // Đóng drawer bằng nút đóng
    await drawer.locator('button[aria-label="Đóng"]').click();
    await expect(drawer).toBeHidden();

    // Xác nhận số dư còn lại của Apple Watch đã phục hồi về 4.500.000đ
    await expect(watchCard).toContainText('4.500.000đ');

    // Xoá payment ở Đức (Bạn thân)
    await tabChoVay.click();
    await ducCard.getByRole('button', { name: 'Chi tiết' }).click();
    await expect(drawer).toBeVisible();

    const deleteDucPaymentBtn = drawer.locator('button[aria-label*="Xoá: 1.000.000"]').first();
    await expect(deleteDucPaymentBtn).toBeVisible();
    await deleteDucPaymentBtn.click();

    await expect(confirmDeleteDialog).toBeVisible();
    await confirmDeleteDialog.getByRole('button', { name: 'Xoá thanh toán' }).click();
    await expect(confirmDeleteDialog).toBeHidden();

    await drawer.locator('button[aria-label="Đóng"]').click();
    await expect(drawer).toBeHidden();

    // Xác nhận số dư còn lại của Đức (Bạn thân) phục hồi về 5.000.000đ
    await expect(ducCard).toContainText('5.000.000đ');
  });
});

