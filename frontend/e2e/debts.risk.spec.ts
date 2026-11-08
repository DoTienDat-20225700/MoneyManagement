import { test, expect, navigateTo } from './fixtures';

test.describe('Vay nợ & Trả góp - Kịch bản Rủi ro (Debts Risk)', () => {
  test('Hiển thị đầy đủ 3 loại hợp đồng và các khoản vay nợ thực tế', async ({ riskPage }) => {
    // Điều hướng sang trang Vay nợ & Trả góp
    await navigateTo(riskPage, '/debts', 'Vay nợ & Trả góp');

    // Xác nhận tiêu đề trang
    await expect(riskPage.getByRole('heading', { level: 1, name: 'Quản lý Vay nợ, Cho vay & Trả góp' })).toBeVisible();

    // 1. Kiểm tra 3 tab hợp đồng nợ
    const tabChoVay = riskPage.locator('button[role="tab"]').filter({ hasText: 'Cho vay' });
    const tabDiVay = riskPage.locator('button[role="tab"]').filter({ hasText: 'Đi vay' });
    const tabTraGop = riskPage.locator('button[role="tab"]').filter({ hasText: 'Mua trả góp' });

    await expect(tabChoVay).toBeVisible();
    await expect(tabDiVay).toBeVisible();
    await expect(tabTraGop).toBeVisible();

    // 2. Tab Cho vay (Mặc định được chọn)
    await expect(tabChoVay).toHaveAttribute('aria-selected', 'true');
    // Xác nhận có khoản nợ của Hà (1.500.000đ) và Nam (5.000.000đ)
    await expect(riskPage.getByText('Hà (Đồng nghiệp cũ)')).toBeVisible();
    await expect(riskPage.getByText('1.500.000đ').first()).toBeVisible();
    await expect(riskPage.getByText('Nam (Bạn đại học)')).toBeVisible();

    // 3. Chuyển sang Tab Đi vay
    await tabDiVay.click();
    await expect(tabDiVay).toHaveAttribute('aria-selected', 'true');
    // Xác nhận có khoản của Chị Linh (Đã tất toán) và Anh Hùng (2.000.000đ)
    await expect(riskPage.getByText('Chị Linh').first()).toBeVisible();
    await expect(riskPage.getByText('Đã tất toán').first()).toBeVisible();
    await expect(riskPage.getByText('Anh Hùng (Anh họ)').first()).toBeVisible();

    // 4. Chuyển sang Tab Mua trả góp
    await tabTraGop.click();
    await expect(tabTraGop).toHaveAttribute('aria-selected', 'true');
    // Xác nhận có hợp đồng trả góp iPhone 15 tại FPT Shop và Laptop ASUS tại Thế Giới Di Động
    await expect(riskPage.getByText('FPT Shop (iPhone 15)')).toBeVisible();
    await expect(riskPage.getByText('Thế Giới Di Động (Laptop ASUS)')).toBeVisible();
    await expect(riskPage.getByText('33.3%').first()).toBeVisible();
  });
});

