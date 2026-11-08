import { test, expect, navigateTo } from './fixtures';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const backendDir = path.resolve(__dirname, '../../backend');

test.describe('Ngân sách - Kịch bản Rủi ro (Budgets Risk)', () => {
  test('Hiển thị cảnh báo vượt ngân sách cho Mua sắm và tiệm cận cho Ăn uống', async ({ riskPage }) => {
    // Điều hướng sang trang Ngân sách
    await navigateTo(riskPage, '/budgets', 'Ngân sách');

    // Xác nhận tiêu đề trang
    await expect(riskPage.getByRole('heading', { level: 1, name: 'Quản lý ngân sách' })).toBeVisible();

    // 1. Kiểm tra thông báo cảnh báo tổng thể (Alert banner)
    const alertBanner = riskPage.locator('.MuiAlert-root').first();
    await expect(alertBanner).toBeVisible();
    await expect(alertBanner).toContainText('Mua sắm');
    await expect(alertBanner).toContainText('Ăn uống');

    // 2. Kiểm tra thẻ danh mục Mua sắm (Vượt hạn mức: 1.250.000đ / 1.000.000đ - 125.0%)
    const shoppingCard = riskPage.locator('.MuiGrid-item').filter({ hasText: 'Mua sắm' }).first();
    await expect(shoppingCard).toBeVisible();
    await expect(shoppingCard).toContainText('1.250.000đ');
    await expect(shoppingCard).toContainText('1.000.000đ');
    await expect(shoppingCard).toContainText('125.0%');
    await expect(shoppingCard).toContainText('Vượt 250.000đ');
    await expect(shoppingCard.getByRole('button', { name: 'Tái cân bằng' })).toBeVisible();

    // 3. Kiểm tra thẻ danh mục Ăn uống (Cảnh báo tiệm cận ≥80%)
    const foodCard = riskPage.locator('.MuiGrid-item').filter({ hasText: 'Ăn uống' }).first();
    await expect(foodCard).toBeVisible();
    await expect(foodCard).toContainText('Ăn uống');
    await expect(foodCard).toContainText('91.7%');
    await expect(foodCard).toContainText('2.750.000đ');
    await expect(foodCard).toContainText('3.000.000đ');

    // 4. Kiểm tra bộ lọc chip trạng thái và các chip đếm
    await expect(riskPage.locator('button').filter({ hasText: 'Vượt hạn mức (1)' })).toBeVisible();
    await expect(riskPage.locator('button').filter({ hasText: 'Cảnh báo (≥80%) (1)' })).toBeVisible();
    const overLimitFilter = riskPage.locator('button').filter({ hasText: 'Vượt hạn mức' }).first();
    await overLimitFilter.click();
    // Khi lọc theo Vượt hạn mức, danh mục Mua sắm vẫn hiển thị
    await expect(shoppingCard).toBeVisible();

    const warningFilter = riskPage.locator('button').filter({ hasText: 'Cảnh báo' }).first();
    await warningFilter.click();
    // Khi lọc theo Cảnh báo, danh mục Ăn uống hiển thị
    await expect(foodCard).toBeVisible();

    // Reset lại lọc Tất cả
    const allFilter = riskPage.locator('button').filter({ hasText: 'Tất cả' }).first();
    await allFilter.click();

    // 5. Kiểm tra nút "Tái cân bằng" xuất hiện và mở modal gợi ý
    const rebalanceBtn = riskPage.getByRole('button', { name: 'Tái cân bằng' }).first();
    await expect(rebalanceBtn).toBeVisible();
    await rebalanceBtn.click();

    // Xác nhận Dialog Gợi ý tái cân bằng ngân sách mở ra
    const dialog = riskPage.locator('div[role="dialog"]');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText('Gợi ý tái cân bằng ngân sách')).toBeVisible();
    await expect(dialog.getByText('Mua sắm')).toBeVisible();

    // Đóng dialog bằng nút "Bỏ qua"
    const skipBtn = dialog.getByRole('button', { name: 'Bỏ qua' });
    if (await skipBtn.isVisible()) {
      await skipBtn.click();
      await expect(dialog).toBeHidden();
    }
  });

  test('Tái cân bằng ngân sách Mua sắm từ nguồn Giải trí, xác nhận số liệu cập nhật và tự khôi phục', async ({ riskPage }) => {
    // 1. Điều hướng đến trang Ngân sách và lấy dữ liệu ngân sách hiện tại qua response
    const budgetsResponsePromise = riskPage.waitForResponse(
      (resp) => resp.url().includes('/api/budgets/') && !resp.url().includes('/summary') && resp.status() === 200
    );
    await navigateTo(riskPage, '/budgets', 'Ngân sách');
    const budgetsResponse = await budgetsResponsePromise;
    const budgets = await budgetsResponse.json();

    const shoppingBudget = budgets.find((b: any) => b.label?.name === 'Mua sắm');
    const entertainmentBudget = budgets.find((b: any) => b.label?.name === 'Giải trí');

    expect(shoppingBudget).toBeTruthy();
    expect(entertainmentBudget).toBeTruthy();

    const currentMonth = shoppingBudget.month;
    const currentYear = shoppingBudget.year;

    // 2. Mock endpoint gợi ý tái cân bằng để test ổn định mọi ngày trong tháng (bất kể ngày <= 15)
    await riskPage.route('**/api/budgets/rebalance-suggestions/*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            budget_id: entertainmentBudget.id,
            label_id: entertainmentBudget.label.id,
            label_name: entertainmentBudget.label.name,
            label_color: entertainmentBudget.label.color || '#36A2EB',
            amount: String(entertainmentBudget.amount),
            spent: String(entertainmentBudget.spent),
            available_rebalance: '1000000.00',
            spent_percentage: 33.33,
            is_non_essential: true,
          },
        ]),
      });
    });

    // 3. Mở dialog Tái cân bằng trên thẻ Mua sắm
    const shoppingCard = riskPage.locator('.MuiGrid-item').filter({ hasText: 'Mua sắm' }).first();
    const entertainmentCard = riskPage.locator('.MuiGrid-item').filter({ hasText: 'Giải trí' }).first();

    const rebalanceBtn = shoppingCard.getByRole('button', { name: 'Tái cân bằng' });
    await expect(rebalanceBtn).toBeVisible();
    await rebalanceBtn.click();

    const dialog = riskPage.locator('div[role="dialog"]');
    await expect(dialog).toBeVisible();

    // Xác nhận đã có gợi ý Giải trí và điền số tiền 250.000đ
    await expect(dialog.getByText('Giải trí')).toBeVisible();

    // Bấm nút "Xác nhận tái cân bằng"
    const confirmBtn = dialog.getByRole('button', { name: 'Xác nhận tái cân bằng' });
    await expect(confirmBtn).toBeVisible();
    await confirmBtn.click();
    await expect(dialog).toBeHidden();

    // 4. Kiểm tra số liệu ngân sách đã được cập nhật sau khi tái cân bằng
    // - Hạn mức Mua sắm tăng từ 1.000.000đ lên 1.250.000đ (đã chi 1.250.000đ -> đạt 100.0%, không còn vượt)
    await expect(shoppingCard).toContainText('1.250.000đ');
    await expect(shoppingCard).toContainText('100.0%');
    await expect(shoppingCard.getByRole('button', { name: 'Tái cân bằng' })).toBeHidden();

    // - Hạn mức Giải trí giảm từ 1.500.000đ xuống 1.250.000đ
    await expect(entertainmentCard).toContainText('1.250.000đ');

    // 5. Tự khôi phục dữ liệu: Hoàn nguyên hạn mức ban đầu bằng Python script theo settings_e2e
    await riskPage.unroute('**/api/budgets/rebalance-suggestions/*');

    const restoreOutput = execSync(
      `python3 -c "import os, django; os.environ['DJANGO_SETTINGS_MODULE']='hubSettings.settings_e2e'; django.setup(); from hubModels.models import CategoryBudget, HubUser; from datetime import date; today=date.today(); user=HubUser.objects.get(email='demo@moneymanagement.local'); wallet=user.get_wallet(); CategoryBudget.objects.filter(wallet=wallet, label__name='Mua sắm', month=today.month, year=today.year).update(amount=1000000); CategoryBudget.objects.filter(wallet=wallet, label__name='Giải trí', month=today.month, year=today.year).update(amount=1500000); sb=CategoryBudget.objects.get(wallet=wallet, label__name='Mua sắm', month=today.month, year=today.year); eb=CategoryBudget.objects.get(wallet=wallet, label__name='Giải trí', month=today.month, year=today.year); print(f'{sb.amount},{eb.amount}')"`,
      { cwd: backendDir }
    ).toString().trim();

    // Xác nhận trực tiếp dữ liệu cơ sở dữ liệu đã phục hồi hoàn toàn về trạng thái ban đầu
    expect(restoreOutput).toBe('1000000.00,1500000.00');
  });
});

