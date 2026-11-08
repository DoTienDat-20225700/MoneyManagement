import { test, expect, navigateTo } from './fixtures';

test.describe('Báo cáo thống kê - Kịch bản An toàn (Reports Safe)', () => {
  test('Hiển thị tab Báo cáo lịch sử, biểu đồ xu hướng và số liệu tổng quan', async ({
    safePage,
  }) => {
    // 1. Điều hướng tới trang Báo cáo
    await navigateTo(safePage, '/reports', 'Báo cáo tài chính');
    await expect(safePage.getByRole('heading', { name: /Báo cáo/i })).toBeVisible();

    // 2. Kiểm tra tab "Báo cáo lịch sử" đang được chọn mặc định
    const historyTab = safePage.getByRole('tab', { name: 'Báo cáo lịch sử' });
    await expect(historyTab).toBeVisible();
    await expect(historyTab).toHaveAttribute('aria-selected', 'true');

    // 3. Kiểm tra các thẻ số liệu tài chính tổng quan (KPI)
    await expect(safePage.getByText(/Thu nhập/i).first()).toBeVisible();
    await expect(safePage.getByText(/Tổng chi tiêu/i)).toBeVisible();
    await expect(safePage.getByText(/Dòng tiền ròng/i)).toBeVisible();

    // 4. Kiểm tra các biểu đồ ApexCharts đã render thành công
    const charts = safePage.locator('.apexcharts-canvas');
    await expect(charts.first()).toBeVisible();
    expect(await charts.count()).toBeGreaterThanOrEqual(1);

    // 5. Kiểm tra danh sách giao dịch chi tiết trong kỳ báo cáo
    await expect(safePage.getByRole('heading', { name: /Danh sách giao dịch trong kỳ/i })).toBeVisible();
  });

  test('Tải xuống báo cáo định dạng Excel (.xlsx)', async ({
    safePage,
  }) => {
    await navigateTo(safePage, '/reports', 'Báo cáo tài chính');

    const exportBtn = safePage.getByRole('button', { name: /Xuất Excel/i });
    await expect(exportBtn).toBeVisible();

    // Bắt sự kiện tải file của trình duyệt
    const downloadPromise = safePage.waitForEvent('download');
    await exportBtn.click();
    const download = await downloadPromise;

    // Xác nhận tệp tải về có đuôi .xlsx
    expect(download.suggestedFilename()).toMatch(/\.xlsx$/i);
    expect(download.suggestedFilename()).toContain('bao_cao_tai_chinh');
  });

  test('Kích hoạt tính năng In báo cáo / Xuất PDF', async ({
    safePage,
  }) => {
    await navigateTo(safePage, '/reports', 'Báo cáo tài chính');

    // Cài đặt theo dõi lệnh window.print
    await safePage.evaluate(() => {
      (window as any).__printTriggered = false;
      window.print = () => {
        (window as any).__printTriggered = true;
      };
    });

    const printBtn = safePage.getByRole('button', { name: /In báo cáo/i });
    await expect(printBtn).toBeVisible();
    await printBtn.click();

    // Xác nhận hàm print() của trình duyệt đã được gọi
    const wasPrinted = await safePage.evaluate(() => (window as any).__printTriggered);
    expect(wasPrinted).toBe(true);
  });
});
