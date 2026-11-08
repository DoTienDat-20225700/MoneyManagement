import { test, expect, navigateTo } from './fixtures';

test.describe('Dự báo dòng tiền - Kịch bản Rủi ro (Forecast Risk)', () => {
  test('Hiển thị cảnh báo nguy cơ cạn quỹ và biểu đồ dự báo cho tài khoản rủi ro', async ({ riskPage }) => {
    // Điều hướng sang trang Báo cáo tài chính
    await navigateTo(riskPage, '/reports', 'Báo cáo tài chính');

    // Chuyển sang Tab Dự báo dòng tiền
    const forecastTab = riskPage.locator('button[role="tab"]').filter({ hasText: 'Dự báo dòng tiền' });
    await expect(forecastTab).toBeVisible();
    await forecastTab.click();

    // 1. Xác nhận tiêu đề tính năng
    await expect(riskPage.getByText('Dự báo dòng tiền & Cảnh báo cạn quỹ')).toBeVisible();

    // 2. Kiểm tra các nút chuyển đổi chu kỳ dự báo: 30d, 60d, 90d
    const btn30d = riskPage.getByRole('button', { name: '30d', exact: true });
    const btn60d = riskPage.getByRole('button', { name: '60d', exact: true });
    const btn90d = riskPage.getByRole('button', { name: '90d', exact: true });

    await expect(btn30d).toBeVisible();
    await expect(btn60d).toBeVisible();
    await expect(btn90d).toBeVisible();

    // 3. Chuyển sang chu kỳ 60d (hoặc 90d) nơi dòng tiền thâm hụt xuống âm và kích hoạt CRITICAL
    const responsePromise60 = riskPage.waitForResponse(
      (resp) => resp.url().includes('/api/forecast/cashflow/') && resp.url().includes('days=60') && resp.status() === 200
    );
    await btn60d.click();
    await responsePromise60;

    // Xác nhận có cảnh báo nguy cơ cạn quỹ (Âm tiền)
    const riskWarning = riskPage.getByText('Nguy cơ cạn quỹ (Âm tiền)');
    await expect(riskWarning).toBeVisible();

    // Thử chuyển tiếp sang 90d
    const responsePromise90 = riskPage.waitForResponse(
      (resp) => resp.url().includes('/api/forecast/cashflow/') && resp.url().includes('days=90') && resp.status() === 200
    );
    await btn90d.click();
    await responsePromise90;
    await expect(riskWarning).toBeVisible();

    // 4. Xác nhận biểu đồ ApexCharts render thành công không lỗi
    const chart = riskPage.locator('.apexcharts-canvas').first();
    await expect(chart).toBeVisible();
  });
});

