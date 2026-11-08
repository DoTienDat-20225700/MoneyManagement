import { test, expect, navigateTo } from './fixtures';

test.describe('Ngân sách - Kịch bản An toàn (Budgets Safe)', () => {
  test('Tất cả ngân sách nằm trong hạn mức an toàn, không có cảnh báo hay nút tái cân bằng', async ({ safePage }) => {
    // Điều hướng sang trang Ngân sách
    await navigateTo(safePage, '/budgets', 'Ngân sách');

    // Xác nhận tiêu đề trang
    await expect(safePage.getByRole('heading', { level: 1, name: 'Quản lý ngân sách' })).toBeVisible();

    // 1. Xác nhận KHÔNG có banner cảnh báo nào xuất hiện
    const alertBanner = safePage.locator('.MuiAlert-message, [role="alert"]');
    await expect(alertBanner).toHaveCount(0);

    // 2. Xác nhận chip đếm trạng thái: Vượt hạn mức (0) và Cảnh báo (0)
    await expect(safePage.locator('button').filter({ hasText: 'Vượt hạn mức (0)' })).toBeVisible();
    await expect(safePage.locator('button').filter({ hasText: 'Cảnh báo (≥80%) (0)' })).toBeVisible();

    // 3. Xác nhận KHÔNG xuất hiện bất kỳ nút "Tái cân bằng" nào trên các thẻ ngân sách
    const rebalanceBtn = safePage.getByRole('button', { name: 'Tái cân bằng' });
    await expect(rebalanceBtn).toHaveCount(0);

    // 4. Kiểm tra các danh mục chính đều ở mức an toàn
    const foodCard = safePage.locator('.MuiGrid-item').filter({ hasText: 'Ăn uống' }).first();
    await expect(foodCard).toBeVisible();
    // Ăn uống chi tiêu ~26.9%, không vượt 80%
    await expect(foodCard.getByText('Cảnh báo (≥80%)')).toHaveCount(0);
  });
});

