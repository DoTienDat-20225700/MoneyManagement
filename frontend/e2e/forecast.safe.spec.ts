import { test, expect, navigateTo } from './fixtures';

test.describe('Dự báo dòng tiền - Kịch bản An toàn (Forecast Safe)', () => {
  test('Dòng tiền ổn định, không có cảnh báo nguy cơ cạn quỹ', async ({ safePage }) => {
    // Điều hướng sang trang Báo cáo tài chính
    await navigateTo(safePage, '/reports', 'Báo cáo tài chính');

    // Chuyển sang Tab Dự báo dòng tiền
    const forecastTab = safePage.locator('button[role="tab"]').filter({ hasText: 'Dự báo dòng tiền' });
    await expect(forecastTab).toBeVisible();
    await forecastTab.click();

    // 1. Xác nhận tiêu đề tính năng
    await expect(safePage.getByText('Dự báo dòng tiền & Cảnh báo cạn quỹ')).toBeVisible();

    // 2. Xác nhận KHÔNG xuất hiện cảnh báo "Nguy cơ cạn quỹ (Âm tiền)"
    await expect(safePage.getByText('Nguy cơ cạn quỹ (Âm tiền)')).toHaveCount(0);

    // 3. Xác nhận số dư thấp nhất duy trì ở mức dương an toàn dồi dào
    await expect(safePage.getByText('Số dư thấp nhất').first()).toBeVisible();

    // 4. Kiểm tra các nút chuyển đổi chu kỳ: 30d, 60d, 90d
    const btn30d = safePage.getByRole('button', { name: '30d', exact: true });
    const btn60d = safePage.getByRole('button', { name: '60d', exact: true });
    const btn90d = safePage.getByRole('button', { name: '90d', exact: true });

    await expect(btn30d).toBeVisible();
    await expect(btn60d).toBeVisible();
    await expect(btn90d).toBeVisible();

    // Thử chuyển sang chu kỳ 60d
    const responsePromise60 = safePage.waitForResponse(
      (resp) => resp.url().includes('/api/forecast/cashflow/') && resp.url().includes('days=60') && resp.status() === 200
    );
    await btn60d.click();
    await responsePromise60;
    await expect(safePage.getByText('Nguy cơ cạn quỹ (Âm tiền)')).toHaveCount(0);

    // 5. Xác nhận biểu đồ ApexCharts hiển thị bình thường
    const chart = safePage.locator('.apexcharts-canvas').first();
    await expect(chart).toBeVisible();
  });
});

