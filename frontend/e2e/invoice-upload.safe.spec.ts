import path from 'path';
import { test, expect } from './fixtures';

test.describe('Nạp hoá đơn tự động - Kịch bản An toàn (Invoice Upload Safe)', () => {
  test('Tải lên hoá đơn mẫu từ sample_invoices và trích xuất thông tin tự động', async ({
    safePage,
  }) => {
    // 1. Mở modal "Nhập hoá đơn" từ trang chủ Dashboard (safePage đã đăng nhập và ở '/')
    const openInvoiceBtn = safePage.getByRole('button', { name: /Nhập hoá đơn/i });
    await expect(openInvoiceBtn).toBeVisible();
    await openInvoiceBtn.click();

    // 2. Kiểm tra modal hiển thị
    const dialog = safePage.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(/Nhập hoá đơn tự động/i)).toBeVisible();

    // 3. Tải lên tệp PDF hoá đơn mẫu thực tế
    const sampleInvoicePath = path.resolve(
      process.cwd(),
      '../sample_invoices/hoa_don_vietcombank.pdf'
    );
    const fileChooserInput = dialog.locator('input[type="file"]');
    await fileChooserInput.setInputFiles(sampleInvoicePath);

    // 4. Xác nhận kết quả phân tích / trích xuất thông tin tự động từ hoá đơn
    await expect(
      dialog.getByText(/Đã đọc được thông tin trong ảnh/i)
    ).toBeVisible();
    await expect(dialog.getByText('Thanh toan tien dien thang 10')).toBeVisible();
    await expect(dialog.getByText('500.000 đ')).toBeVisible();
    await expect(dialog.getByText('11/10/2026')).toBeVisible();

    // 5. Đóng modal
    await dialog.getByLabel('Đóng').click();
    await expect(dialog).not.toBeVisible();
  });

  test('Mock API trích xuất hoá đơn bằng page.route khi cần kiểm thử cô lập', async ({
    safePage,
  }) => {
    // Mock endpoint phân tích hoá đơn preview
    await safePage.route('**/api/import/preview/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message: 'Đã phân tích thông tin hoá đơn thành công (Mocked)',
          results: [
            {
              file_name: 'fake_invoice.pdf',
              title: 'Cà phê Highland Coffee E2E',
              value: 75000,
              formatted_value: '75.000 đ',
              date: '2026-11-08',
              formatted_date: '08/11/2026',
              institution: 'Vietcombank',
              is_valid: true,
            },
          ],
        }),
      });
    });

    // Mở modal nhập hoá đơn
    await safePage.getByRole('button', { name: /Nhập hoá đơn/i }).click();
    const dialog = safePage.getByRole('dialog');
    await expect(dialog).toBeVisible();

    const sampleInvoicePath = path.resolve(
      process.cwd(),
      '../sample_invoices/hoa_don_vietcombank.pdf'
    );
    const fileChooserInput = dialog.locator('input[type="file"]');
    await fileChooserInput.setInputFiles(sampleInvoicePath);

    // Kiểm tra dữ liệu mock hiển thị chính xác
    await expect(
      dialog.getByText(/Đã đọc được thông tin trong ảnh/i)
    ).toBeVisible();
    await expect(dialog.getByText('Cà phê Highland Coffee E2E')).toBeVisible();
    await expect(dialog.getByText('75.000 đ')).toBeVisible();
    await expect(dialog.getByText('08/11/2026')).toBeVisible();

    await dialog.getByLabel('Đóng').click();
  });

  test('Kiểm tra Form Validation khi chưa chọn tệp hoá đơn', async ({
    safePage,
  }) => {
    await safePage.getByRole('button', { name: /Nhập hoá đơn/i }).click();
    const dialog = safePage.getByRole('dialog');
    await expect(dialog).toBeVisible();

    // Nhấn nút nhập mà chưa chọn tệp
    await dialog.getByRole('button', { name: /Nhập hoá đơn/i }).click();

    // Kiểm tra thông báo lỗi validation hiển thị
    await expect(
      dialog.getByText(/Vui lòng chọn tệp PDF hoặc ảnh chụp biên lai/i)
    ).toBeVisible();

    await dialog.getByLabel('Đóng').click();
  });
});

